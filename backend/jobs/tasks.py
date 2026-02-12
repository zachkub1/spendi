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
        logger.info(f"Sync completed for {email_account_id}: {result}")
        return result

    except Exception as exc:
        logger.error(f"Sync task failed for {email_account_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
