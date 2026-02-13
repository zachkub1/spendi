"""
Email sync service - orchestrates email discovery, fetching, and parsing.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from app.db.models import EmailAccount, RawEmail, ParsedTransaction, AuditLogAction
from app.email_ingest.service import EmailAccountService
from app.email_ingest.gmail_client import GmailClient
from app.email_ingest.parsers.registry import ParserRegistry
from app.auth.service import AuthService
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

            # Stage 2 & 3: Fetch and Parse
            for msg_metadata in messages:
                # Check if already processed (idempotency)
                existing = db.query(RawEmail).filter_by(
                    message_id=msg_metadata['id']
                ).first()
                if existing:
                    continue

                # Fetch full message
                try:
                    message = gmail_client.get_message(msg_metadata['id'])
                except Exception as e:
                    logger.error(f"Failed to fetch message {msg_metadata['id']}: {e}")
                    continue

                subject = message['subject']
                sender = message['from']
                body = message['body']
                received_at = parse_email_date(message.get('date', ''), message.get('internalDate'))

                # Create RawEmail record
                raw_email = RawEmail(
                    email_account_id=email_account.id,
                    message_id=msg_metadata['id'],
                    subject=subject,
                    sender=sender,
                    received_at=received_at,
                    parsing_status="pending"
                )
                db.add(raw_email)
                db.flush()
                discovered_count += 1

                # Find appropriate parser
                parser = ParserRegistry.get_parser(sender, subject)
                if not parser:
                    raw_email.parsing_status = "failed"
                    raw_email.error_message = "No parser found for email"
                    failed_count += 1
                    continue

                # Parse transaction
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
                            parser_version=parser.get_version()
                        )
                        db.add(parsed_txn)

                        raw_email.parsing_status = "success"
                        parsed_count += 1
                        logger.debug(f"✅ Parsed transaction from {sender}: {parse_result.data.merchant_name} ${parse_result.data.amount}")

                    elif parse_result.status == "non_transaction":
                        # Email is from financial provider but contains no transaction (marketing, alerts, etc.)
                        raw_email.parsing_status = "non_transaction"
                        raw_email.error_message = parse_result.reason
                        non_transaction_count += 1
                        logger.debug(f"ℹ️  Non-transaction email from {sender}: {parse_result.reason}")

                    elif parse_result.status == "parse_error":
                        # Email should contain transaction but parsing failed
                        raw_email.parsing_status = "failed"
                        raw_email.error_message = parse_result.reason
                        failed_count += 1
                        logger.warning(f"⚠️  Parse error for {msg_metadata['id']}: {parse_result.reason}")

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

            logger.info(f"✅ Sync completed: {discovered_count} discovered, {parsed_count} parsed, {non_transaction_count} non-transaction, {failed_count} failed")

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
