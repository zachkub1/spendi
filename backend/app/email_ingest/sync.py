"""
Email sync service - orchestrates email discovery, fetching, and parsing.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import EmailAccount, RawEmail, ParsedTransaction, AuditLogAction
from app.email_ingest.service import EmailAccountService
from app.email_ingest.gmail_client import GmailClient
from app.email_ingest.parsers.registry import ParserRegistry
from app.auth.service import AuthService
import logging

logger = logging.getLogger(__name__)


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
            credentials = EmailAccountService.get_decrypted_credentials(email_account)
            gmail_client = GmailClient(credentials)

            # Stage 1: Discovery - list messages from allowed senders
            last_sync = email_account.last_sync_at or datetime(2020, 1, 1)
            sender_filter = ParserRegistry.get_allowed_senders()

            messages = gmail_client.list_messages(
                sender_filter=sender_filter,
                after_date=last_sync.strftime("%Y/%m/%d"),
                max_results=100
            )

            discovered_count = 0
            parsed_count = 0
            failed_count = 0

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
                received_at = datetime.strptime(message['date'], "%a, %d %b %Y %H:%M:%S %z") if message['date'] else datetime.utcnow()

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
                    parsed_data = parser.parse(subject, body)

                    # Create ParsedTransaction
                    parsed_txn = ParsedTransaction(
                        raw_email_id=raw_email.id,
                        email_account_id=email_account.id,
                        merchant_name=parsed_data.merchant_name,
                        amount=parsed_data.amount,
                        currency="USD",
                        transaction_date=parsed_data.transaction_date,
                        card_last_four=parsed_data.card_last_four,
                        transaction_type=parsed_data.transaction_type,
                        confidence_score=parsed_data.confidence_score,
                        parser_version=parser.get_version()
                    )
                    db.add(parsed_txn)

                    raw_email.parsing_status = "success"
                    raw_email.parser_used = parser.provider
                    parsed_count += 1

                except Exception as e:
                    logger.error(f"Parsing error for {msg_metadata['id']}: {e}")
                    raw_email.parsing_status = "failed"
                    raw_email.error_message = str(e)
                    failed_count += 1

            # Update email account
            email_account.last_sync_at = datetime.utcnow()
            email_account.sync_status = "success"
            db.commit()

            # Create audit log
            AuthService.create_audit_log(
                db=db,
                user_id=str(email_account.user_id),
                action=AuditLogAction.EMAIL_ACCOUNT_SYNC_COMPLETED,
                resource_id=email_account.id,
                details={
                    "discovered": discovered_count,
                    "parsed": parsed_count,
                    "failed": failed_count
                }
            )

            logger.info(f"Sync completed: {discovered_count} discovered, {parsed_count} parsed, {failed_count} failed")

            return {
                "discovered": discovered_count,
                "parsed": parsed_count,
                "failed": failed_count
            }

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            email_account.sync_status = "error"
            db.commit()

            AuthService.create_audit_log(
                db=db,
                user_id=str(email_account.user_id),
                action=AuditLogAction.EMAIL_ACCOUNT_SYNC_FAILED,
                resource_id=email_account.id,
                details={"error": str(e)}
            )

            raise
