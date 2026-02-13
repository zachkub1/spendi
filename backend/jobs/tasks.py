"""
Celery tasks for background jobs.
"""
from jobs.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import EmailAccount
from app.email_ingest.sync import EmailSyncService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def sync_email_account_task(self, email_account_id: str):
    """
    Background task to sync an email account.
    Retries up to 3 times on failure with exponential backoff.

    Args:
        email_account_id: UUID of EmailAccount to sync

    Returns:
        Dict with sync summary
    """
    db = SessionLocal()
    try:
        email_account = db.query(EmailAccount).filter_by(id=email_account_id).first()
        if not email_account:
            logger.error(f"EmailAccount {email_account_id} not found")
            return {"error": "Email account not found"}

        result = EmailSyncService.sync_email_account(db, email_account)
        logger.info(f"✅ Sync completed for {email_account_id}: {result}")
        return result

    except Exception as exc:
        logger.error(f"❌ Sync task failed for {email_account_id}: {exc}")

        # Check if this is a retryable error (Gmail API, network, etc)
        # Audit log failures are already caught and don't reach here
        error_msg = str(exc).lower()

        # Don't retry on non-retryable errors (permanent failures)
        non_retryable_patterns = [
            "not found",
            "invalid",
            "unauthorized",
            "unconverted data remains",  # Date parsing errors (malformed email headers)
            "parse error",               # Email parsing failures
            "no parser found"            # Unsupported email format
        ]

        if any(pattern in error_msg for pattern in non_retryable_patterns):
            logger.error(f"Non-retryable error, not retrying: {exc}")
            return {"error": str(exc)}

        # Retry on transient errors (network, rate limit, Gmail API throttling, etc)
        logger.info(f"Retryable error detected, will retry (attempt {self.request.retries + 1}/3)")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
