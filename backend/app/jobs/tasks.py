"""
Celery tasks for background processing.
"""
from celery import Task
import logging

from app.jobs.worker import celery_app

logger = logging.getLogger(__name__)


# Transient errors that are worth retrying (network blips, rate limits, token refresh races).
# Permanent failures (bad data, missing records) should not consume retries.
_NON_RETRYABLE_PATTERNS = [
    "not found",
    "invalid",
    "unauthorized",
    "unconverted data remains",  # malformed email date headers
    "parse error",
    "no parser found",
]


@celery_app.task(bind=True, name='app.jobs.tasks.sync_email_account_task', max_retries=3)
def sync_email_account_task(self: Task, account_id: str):
    """
    Sync a single email account (manually triggered or scheduled).
    Retries up to 3 times on transient failures with exponential backoff.

    Args:
        account_id: UUID of EmailAccount to sync

    Returns:
        Summary dict with sync results
    """
    from app.db.session import SessionLocal
    from app.db.models import EmailAccount, AuditLogAction
    from app.email_ingest.sync import EmailSyncService
    from app.auth.service import AuthService

    logger.info(f"[CELERY] Starting email sync task for account {account_id}")

    db = SessionLocal()
    email_account = None

    try:
        email_account = db.query(EmailAccount).filter_by(id=account_id).first()
        if not email_account:
            logger.error(f"[CELERY] Email account {account_id} not found")
            return {"status": "error", "message": "Account not found"}

        logger.info(f"[CELERY] Syncing {email_account.email_address}...")

        result = EmailSyncService.sync_email_account(db, email_account)

        # Audit log — non-fatal (sync must not fail because of logging)
        try:
            AuthService.create_audit_log(
                db=db,
                user_id=str(email_account.user_id),
                action=AuditLogAction.EMAIL_ACCOUNT_SYNC_COMPLETED,
                resource_type="EmailAccount",
                resource_id=account_id,
                details=result,
            )
        except Exception as audit_error:
            logger.warning(f"[CELERY] Audit logging failed (non-fatal): {audit_error}")

        logger.info(f"[CELERY] ✅ Sync completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"[CELERY] ❌ Sync failed: {type(exc).__name__}: {exc}", exc_info=True)

        if email_account:
            email_account.sync_status = "error"
            db.commit()

        # Audit log failure — non-fatal
        if email_account:
            try:
                AuthService.create_audit_log(
                    db=db,
                    user_id=str(email_account.user_id),
                    action=AuditLogAction.EMAIL_ACCOUNT_SYNC_FAILED,
                    resource_type="EmailAccount",
                    resource_id=account_id,
                    details={"error": str(exc)},
                )
            except Exception as audit_error:
                logger.warning(f"[CELERY] Audit logging failed (non-fatal): {audit_error}")

        # Permanent failures — don't waste retries
        error_msg = str(exc).lower()
        if any(pattern in error_msg for pattern in _NON_RETRYABLE_PATTERNS):
            logger.error(f"[CELERY] Non-retryable error, skipping retries: {exc}")
            return {"status": "error", "message": str(exc)}

        # Transient failures — retry with exponential backoff (60s, 120s, 240s)
        logger.info(
            f"[CELERY] Transient error detected, scheduling retry "
            f"(attempt {self.request.retries + 1}/{self.max_retries})"
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(name='app.jobs.tasks.sync_all_email_accounts')
def sync_all_email_accounts():
    """
    Sync all active email accounts (runs hourly).
    """
    from app.db.session import SessionLocal
    from app.db.models import EmailAccount

    logger.info("[CELERY] Starting scheduled sync for all email accounts")

    db = SessionLocal()
    try:
        # Get all active accounts with sync enabled
        accounts = db.query(EmailAccount).filter_by(sync_enabled=True).all()

        logger.info(f"[CELERY] Found {len(accounts)} accounts to sync")

        # Trigger sync for each account
        for account in accounts:
            logger.info(f"[CELERY] Enqueuing sync for {account.email_address}")
            sync_email_account_task.delay(str(account.id))

        return {
            "status": "success",
            "message": f"Enqueued {len(accounts)} sync tasks"
        }

    except Exception as e:
        logger.error(f"[CELERY] ❌ Failed to schedule syncs: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery_app.task(name='app.jobs.tasks.process_transaction')
def process_transaction(transaction_id: str):
    """
    Process a single transaction (normalize, categorize, match).
    Not yet implemented — normalization is handled synchronously in the sync pipeline.
    """
    raise NotImplementedError(
        f"process_transaction is not yet implemented (transaction_id={transaction_id}). "
        "Transaction normalization currently runs synchronously inside sync_email_account."
    )
