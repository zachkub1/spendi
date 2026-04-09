"""
Email sync service - orchestrates email discovery, fetching, and parsing.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from typing import Optional
from app.db.models import EmailAccount, RawEmail, ParsedTransaction, AuditLogAction
from app.email_ingest.service import EmailAccountService
from app.email_ingest.gmail_client import GmailClient
from app.email_ingest.parsers.registry import ParserRegistry
from app.auth.service import AuthService
from app.transactions.matching_service import PaymentInstrumentMatchingService
import logging

logger = logging.getLogger(__name__)


def parse_email_date(date_header: str, internal_date_ms: Optional[int] = None) -> datetime:
    """
    Defensively parse email Date header with fallback to Gmail internalDate.

    Gmail Date headers are often non-RFC-compliant:
    - "Tue, 11 Feb 2026 19:43:12 (UTC)" - parenthetical timezone
    - "Wed, 12 Feb 2026 10:00:00" - missing timezone
    - "12 Feb 2026 10:00:00 GMT" - missing day-of-week

    Args:
        date_header: Raw Date header from email
        internal_date_ms: Gmail's internalDate (milliseconds since epoch)

    Returns:
        Parsed datetime (timezone-aware if possible)
    """
    if not date_header and not internal_date_ms:
        logger.warning("[PARSE] No date header or internalDate, using current time")
        return datetime.now(timezone.utc)

    # Try email.utils.parsedate_to_datetime (handles most RFC-2822 variants)
    if date_header:
        try:
            # Strip common non-standard suffixes before parsing
            cleaned = date_header.strip()
            # Remove parenthetical timezone annotations like " (UTC)", " (EST)"
            if '(' in cleaned:
                cleaned = cleaned[:cleaned.index('(')].strip()

            parsed = parsedate_to_datetime(cleaned)
            logger.debug(f"[PARSE] Successfully parsed Date header: {date_header} -> {parsed}")
            return parsed
        except Exception as e:
            logger.warning(f"[PARSE] Failed to parse Date header '{date_header}': {e}, falling back to internalDate")

    # Fallback to Gmail's internalDate (always present and reliable)
    if internal_date_ms:
        try:
            # internalDate is milliseconds since epoch
            timestamp_seconds = int(internal_date_ms) / 1000
            parsed = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
            logger.debug(f"[PARSE] Using Gmail internalDate: {internal_date_ms}ms -> {parsed}")
            return parsed
        except Exception as e:
            logger.error(f"[PARSE] Failed to parse internalDate {internal_date_ms}: {e}")

    # Final fallback
    logger.warning("[PARSE] All date parsing failed, using current time")
    return datetime.now(timezone.utc)


class EmailSyncService:
    """Service for syncing emails from Gmail."""

    @staticmethod
    def sync_email_account(db: Session, email_account: EmailAccount) -> dict:
        """
        Full sync pipeline for an email account.

        Args:
            db: Database session
            email_account: EmailAccount to sync

        Returns:
            Summary dict: {discovered: int, parsed: int, failed: int}
        """
        try:
            # Update sync status
            email_account.sync_status = "in_progress"
            db.commit()

            # Get decrypted credentials
            logger.info(f"[SYNC] Decrypting credentials for account {email_account.id}")
            try:
                credentials = EmailAccountService.get_decrypted_credentials(email_account)
                logger.info(f"[SYNC] ✅ Credentials decrypted successfully")
                logger.info(f"[SYNC] Token expiry: {credentials.expiry}")
                logger.info(f"[SYNC] Token valid: {credentials.valid}")
                logger.info(f"[SYNC] Token expired: {credentials.expired}")
            except Exception as decrypt_error:
                logger.error(f"[SYNC] ❌ Credential decryption failed: {type(decrypt_error).__name__}: {decrypt_error}")
                raise

            gmail_client = GmailClient(credentials)

            # Stage 1: Discovery - list messages from allowed senders
            last_sync = email_account.last_sync_at or datetime(2020, 1, 1)

            # Extend window back to cover any previously-failed emails that need retry
            oldest_failed = (
                db.query(RawEmail)
                .filter(
                    RawEmail.email_account_id == email_account.id,
                    RawEmail.parsing_status == "failed"
                )
                .order_by(RawEmail.received_at.asc())
                .first()
            )
            if oldest_failed and oldest_failed.received_at:
                # Normalize both to naive UTC for comparison
                failed_dt = oldest_failed.received_at
                if getattr(failed_dt, 'tzinfo', None):
                    failed_dt = failed_dt.replace(tzinfo=None)
                last_sync_naive = last_sync.replace(tzinfo=None) if getattr(last_sync, 'tzinfo', None) else last_sync
                if failed_dt < last_sync_naive:
                    retry_count = (
                        db.query(RawEmail)
                        .filter(
                            RawEmail.email_account_id == email_account.id,
                            RawEmail.parsing_status == "failed"
                        )
                        .count()
                    )
                    logger.info(f"[SYNC] {retry_count} failed email(s) detected — extending sync window from {last_sync_naive.date()} back to {failed_dt.date()}")
                    last_sync = failed_dt

            sender_filter = ParserRegistry.get_allowed_senders()

            logger.info(f"[SYNC] Querying Gmail API for messages since {last_sync}")
            logger.info(f"[SYNC] Sender filter: {sender_filter}")

            try:
                messages = gmail_client.list_messages(
                    sender_filter=sender_filter,
                    after_date=last_sync.strftime("%Y/%m/%d"),
                    max_results=100
                )
                logger.info(f"[SYNC] ✅ Gmail API returned {len(messages)} messages")
            except Exception as gmail_error:
                logger.error(f"[SYNC] ❌ Gmail API error: {type(gmail_error).__name__}: {gmail_error}")
                if hasattr(gmail_error, 'resp'):
                    logger.error(f"[SYNC] Response status: {gmail_error.resp.status}")
                    logger.error(f"[SYNC] Response body: {gmail_error.resp.get('error', 'N/A')}")
                raise

            discovered_count = 0
            parsed_count = 0
            failed_count = 0
            non_transaction_count = 0
            normalized_count = 0

            # Stage 2 & 3: Fetch and Parse
            for msg_metadata in messages:
                # Idempotency: skip already-successful emails; retry failed/pending ones
                existing = db.query(RawEmail).filter_by(
                    message_id=msg_metadata['id']
                ).first()
                if existing and existing.parsing_status in ("success", "non_transaction"):
                    # Always skip confirmed successes.
                    # For non_transaction: skip unless a parser now claims it can parse it,
                    # which means new patterns were added after the email was processed.
                    if existing.parsing_status == "success":
                        logger.debug(
                            f"[SYNC] Skipping {msg_metadata['id']!r} — "
                            f"already success (subject={existing.subject!r})"
                        )
                        continue
                    # non_transaction: peek at whether a parser now matches the subject
                    # (uses stored subject — no extra API call needed)
                    candidate_parser = ParserRegistry.get_parser(
                        existing.sender.lower() if existing.sender else "",
                        existing.subject or "",
                    )
                    # parseaddr is already imported at module level
                    _, clean_sender = parseaddr(existing.sender or "")
                    if not candidate_parser and clean_sender:
                        candidate_parser = ParserRegistry.get_parser(
                            clean_sender.lower(), existing.subject or ""
                        )
                    if not candidate_parser:
                        logger.debug(
                            f"[SYNC] Skipping {msg_metadata['id']!r} — "
                            f"non_transaction, no parser match "
                            f"(subject={existing.subject!r})"
                        )
                        continue
                    # A parser now matches — allow retry by falling through
                    logger.info(
                        f"[SYNC] Re-queuing {msg_metadata['id']!r} — "
                        f"previously non_transaction but parser now matches "
                        f"(subject={existing.subject!r})"
                    )
                if existing:
                    logger.info(f"[SYNC] Retrying email {msg_metadata['id']} (status={existing.parsing_status!r}, reason={existing.error_message!r})")

                # Fetch full message
                try:
                    message = gmail_client.get_message(msg_metadata['id'])
                except Exception as e:
                    logger.error(f"Failed to fetch message {msg_metadata['id']}: {e}")
                    if existing:
                        existing.error_message = f"refetch_failed: {str(e)}"
                    continue

                subject = message['subject']
                sender_raw = message['from']
                # Extract clean email address from display-name formatted From header.
                # Gmail From headers look like "Chase Alerts <no.reply.alerts@chase.com>"
                # which breaks $-anchored sender patterns if passed as-is.
                _, sender = parseaddr(sender_raw)
                sender = sender.lower()
                body = message['body']
                received_at = parse_email_date(message.get('date', ''), message.get('internalDate'))

                if existing:
                    # Reset failed record for retry in-place (preserves id + foreign keys)
                    raw_email = existing
                    raw_email.subject = subject
                    raw_email.sender = sender_raw
                    raw_email.received_at = received_at
                    raw_email.parsing_status = "pending"
                    raw_email.error_message = None
                    raw_email.parser_used = None
                    db.flush()
                else:
                    # Create RawEmail record — store original From header for audit trail
                    raw_email = RawEmail(
                        email_account_id=email_account.id,
                        message_id=msg_metadata['id'],
                        subject=subject,
                        sender=sender_raw,
                        received_at=received_at,
                        parsing_status="pending"
                    )
                    db.add(raw_email)
                    db.flush()
                discovered_count += 1

                # Find appropriate parser using extracted email address
                parser = ParserRegistry.get_parser(sender, subject)
                if not parser:
                    # No parser = unrecognized email from a financial domain (marketing,
                    # account alerts, etc.). Mark as non_transaction so the idempotency
                    # check skips it on future syncs (unless a new parser is added that
                    # now matches it — the re-queue logic handles that case).
                    # Using "failed" here would extend the sync window back indefinitely.
                    raw_email.parsing_status = "non_transaction"
                    raw_email.error_message = "no_parser_found"
                    non_transaction_count += 1
                    logger.debug(
                        f"[SYNC] No parser matched — sender_email={sender!r}, subject={subject!r}"
                    )
                    continue

                # Parse transaction
                logger.info(f"[SYNC] Using parser={parser.provider!r} for subject={subject!r}")
                try:
                    parse_result = parser.parse(subject, body)
                    raw_email.parser_used = parser.provider

                    if parse_result.status == "transaction":
                        # Successfully parsed transaction - create record
                        parsed_txn = ParsedTransaction(
                            raw_email_id=raw_email.id,
                            email_account_id=email_account.id,
                            merchant_name=parse_result.data.merchant_name,
                            amount=parse_result.data.amount,
                            currency="USD",
                            transaction_date=parse_result.data.transaction_date,
                            card_last_four=parse_result.data.card_last_four,
                            transaction_type=parse_result.data.transaction_type,
                            confidence_score=parse_result.data.confidence_score,
                            parser_version=parser.get_version(),
                            p2p_transaction_id=parse_result.data.p2p_transaction_id,
                            p2p_source=parse_result.data.p2p_source,
                        )
                        db.add(parsed_txn)
                        db.flush()  # Flush to get parsed_txn.id for matching

                        raw_email.parsing_status = "success"
                        parsed_count += 1
                        logger.info(
                            f"[SYNC] ✅ Parsed ({parser.provider}): "
                            f"{parse_result.data.merchant_name} ${parse_result.data.amount} "
                            f"type={parse_result.data.transaction_type} p2p={parse_result.data.p2p_source}"
                        )

                        # Phase 2: Match to payment instrument and normalize
                        try:
                            normalized_txn = PaymentInstrumentMatchingService.match_and_normalize(
                                db=db,
                                parsed_transaction=parsed_txn,
                                user_id=str(email_account.user_id)
                            )
                            if normalized_txn:
                                normalized_count += 1
                                logger.info(
                                    f"[SYNC] ✅ Normalized: {normalized_txn.merchant_normalized} "
                                    f"${normalized_txn.amount} category={normalized_txn.category} "
                                    f"instrument={normalized_txn.payment_instrument_id}"
                                )
                            else:
                                logger.warning(
                                    f"[SYNC] ⚠️  No payment instrument match for: "
                                    f"{parsed_txn.merchant_name} (type={parsed_txn.transaction_type} "
                                    f"last4={parsed_txn.card_last_four} p2p={parsed_txn.p2p_source})"
                                )
                        except Exception as norm_error:
                            # Normalization failure should not crash the sync
                            logger.error(f"[SYNC] ❌ Normalization failed for {parsed_txn.merchant_name}: {norm_error}", exc_info=True)

                    elif parse_result.status == "non_transaction":
                        # Email is from financial provider but contains no transaction (marketing, alerts, etc.)
                        raw_email.parsing_status = "non_transaction"
                        raw_email.error_message = parse_result.reason
                        non_transaction_count += 1
                        logger.info(f"[SYNC] ℹ️  Non-transaction ({parser.provider}): {parse_result.reason} subject={subject!r}")

                    elif parse_result.status == "parse_error":
                        # Email should contain transaction but parsing failed
                        raw_email.parsing_status = "failed"
                        raw_email.error_message = parse_result.reason
                        failed_count += 1
                        logger.warning(
                            f"[SYNC] ⚠️  Parse error: reason={parse_result.reason!r} "
                            f"parser={parser.provider!r} subject={subject!r}"
                        )
                        logger.warning(f"[SYNC] Parse-error body preview: {body[:500]!r}")

                except Exception as e:
                    # Unexpected exception during parsing (shouldn't happen with new contract)
                    logger.error(f"❌ Unexpected parsing exception for {msg_metadata['id']}: {e}")
                    raw_email.parsing_status = "failed"
                    raw_email.error_message = f"unexpected_exception: {str(e)}"
                    failed_count += 1

            # Update email account
            email_account.last_sync_at = datetime.now(timezone.utc)
            email_account.sync_status = "success"
            db.commit()

            logger.info(f"✅ Sync completed: {discovered_count} discovered, {parsed_count} parsed, {normalized_count} normalized, {non_transaction_count} non-transaction, {failed_count} failed")

            # Create audit log (non-blocking - must not crash sync)
            try:
                AuthService.create_audit_log(
                    db=db,
                    user_id=str(email_account.user_id),
                    action=AuditLogAction.EMAIL_ACCOUNT_SYNC_COMPLETED,
                    resource_type="EmailAccount",
                    resource_id=str(email_account.id),
                    details={
                        "discovered": discovered_count,
                        "parsed": parsed_count,
                        "normalized": normalized_count,
                        "non_transaction": non_transaction_count,
                        "failed": failed_count
                    }
                )
                logger.info("[AUDIT] Sync completion logged successfully")
            except Exception as audit_error:
                # Audit logging failure should NOT crash the sync job
                logger.error(f"[AUDIT] ⚠️  Failed to create audit log (non-fatal): {audit_error}")
                logger.error(f"[AUDIT] Sync still succeeded - this is a logging issue only")

            return {
                "discovered": discovered_count,
                "parsed": parsed_count,
                "normalized": normalized_count,
                "non_transaction": non_transaction_count,
                "failed": failed_count
            }

        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            email_account.sync_status = "error"
            db.commit()

            # Create audit log for failure (non-blocking)
            try:
                AuthService.create_audit_log(
                    db=db,
                    user_id=str(email_account.user_id),
                    action=AuditLogAction.EMAIL_ACCOUNT_SYNC_FAILED,
                    resource_type="EmailAccount",
                    resource_id=str(email_account.id),
                    details={"error": str(e)}
                )
            except Exception as audit_error:
                logger.error(f"[AUDIT] Failed to log sync failure (non-fatal): {audit_error}")

            raise
