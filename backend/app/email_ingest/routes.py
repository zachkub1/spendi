"""
Email account management routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.session import get_db
from app.db.models import User, EmailAccount
from app.auth.dependencies import get_current_user
from app.email_ingest.service import EmailAccountService
from app.email_ingest.gmail_client import GmailClient
from app.config import settings
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email Accounts"])


def _get_gmail_oauth_config() -> tuple[dict, str]:
    """Single source of truth for Gmail OAuth configuration."""
    redirect_uri = f"{settings.FRONTEND_URL}/email/callback"
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return client_config, redirect_uri


@router.get("/auth/login")
async def gmail_auth_login(current_user: User = Depends(get_current_user)):
    """Initiate Gmail OAuth flow (separate from user login). Requires authentication."""
    try:
        client_config, redirect_uri = _get_gmail_oauth_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )

        # Store state for CSRF validation on callback
        from app.auth.service import AuthService
        AuthService.store_oauth_state(state)

        logger.info("[EMAIL_AUTH] Gmail OAuth initiated for user %s", current_user.id)
        return {"authorization_url": authorization_url, "state": state}
    except Exception as e:
        logger.error("[EMAIL_AUTH] Failed to create Gmail auth URL: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Gmail authorization",
        )


class ConnectGmailRequest(BaseModel):
    code: str
    state: Optional[str] = None


class EmailAccountResponse(BaseModel):
    id: str
    email_address: str
    provider: str
    sync_enabled: bool
    last_sync_at: Optional[str]
    sync_status: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/connect")
async def connect_gmail(
    request: ConnectGmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect Gmail account using OAuth code."""
    # Validate state to prevent CSRF
    if not request.state:
        logger.warning("[EMAIL_AUTH] /email/connect called without state by user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state parameter",
        )

    logger.info("[EMAIL_AUTH] Validating state (first 8): %s... for user %s", request.state[:8], current_user.id)
    from app.auth.service import AuthService
    if not AuthService.validate_oauth_state(request.state):
        logger.warning("[EMAIL_AUTH] State not found in Redis — expired or already used. User %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    try:
        client_config, redirect_uri = _get_gmail_oauth_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=redirect_uri,
        )

        try:
            flow.fetch_token(code=request.code)
        except Exception as token_error:
            logger.error(
                "[EMAIL_AUTH] Token exchange failed for user %s: %s",
                current_user.id,
                type(token_error).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code",
            )

        credentials = flow.credentials

        gmail_client = GmailClient(credentials)
        profile = gmail_client.service.users().getProfile(userId="me").execute()
        email_address = profile["emailAddress"]

        existing = db.query(EmailAccount).filter_by(
            user_id=current_user.id,
            email_address=email_address,
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email account already connected",
            )

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(0, credentials.expiry.timestamp() - datetime.now(timezone.utc).timestamp())
            if credentials.expiry else 3600
        )

        email_account = EmailAccountService.create_email_account(
            db=db,
            user_id=str(current_user.id),
            email_address=email_address,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
        )

        logger.info("[EMAIL_AUTH] Gmail connected for user %s: %s", current_user.id, email_address)

        return {
            "message": "Gmail account connected successfully",
            "account": {
                "id": str(email_account.id),
                "email_address": email_account.email_address,
                "provider": email_account.provider,
                "sync_enabled": email_account.sync_enabled,
                "last_sync_at": email_account.last_sync_at.isoformat() if email_account.last_sync_at else None,
                "sync_status": email_account.sync_status,
                "created_at": email_account.created_at.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[EMAIL_AUTH] Failed to connect Gmail for user %s: %s", current_user.id, type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect Gmail account",
        )


@router.get("/accounts")
async def list_email_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's connected email accounts."""
    accounts = (
        db.query(EmailAccount)
        .filter(
            EmailAccount.user_id == current_user.id,
            EmailAccount.provider != "demo",
        )
        .all()
    )
    return {
        "accounts": [
            {
                "id": str(acc.id),
                "email_address": acc.email_address,
                "provider": acc.provider,
                "sync_enabled": acc.sync_enabled,
                "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
                "sync_status": acc.sync_status,
                "created_at": acc.created_at.isoformat(),
            }
            for acc in accounts
        ]
    }


@router.delete("/accounts/{account_id}")
async def disconnect_email_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect email account."""
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id,
    ).first()

    if not email_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found",
        )

    EmailAccountService.disconnect_email_account(db, account_id)
    return {"message": "Email account disconnected successfully"}


@router.post("/sync/{account_id}")
async def trigger_sync(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger email sync for an account (enqueues Celery task)."""
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id,
    ).first()

    if not email_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found",
        )

    if email_account.sync_status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync already in progress",
        )

    if not email_account.oauth_access_token or not email_account.oauth_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email account is missing OAuth tokens. Please reconnect your Gmail account.",
        )

    try:
        from app.jobs.tasks import sync_email_account_task
        task = sync_email_account_task.delay(str(email_account.id))
        logger.info("[SYNC_API] Enqueued sync task %s for account %s (user %s)", task.id, account_id, current_user.id)
        return {
            "message": "Sync started",
            "task_id": task.id,
            "account_id": str(email_account.id),
            "email_address": email_account.email_address,
        }
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background job system not available.",
        )
    except Exception as e:
        logger.error("[SYNC_API] Failed to enqueue sync task: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start sync",
        )


@router.get("/transactions")
async def list_parsed_transactions(
    account_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List parsed transactions for user."""
    from app.db.models import ParsedTransaction
    from sqlalchemy.orm import joinedload

    query = (
        db.query(ParsedTransaction)
        .options(joinedload(ParsedTransaction.normalized_transaction))
        .join(EmailAccount)
        .filter(
            EmailAccount.user_id == current_user.id,
            EmailAccount.provider != "demo",
        )
    )

    if account_id:
        query = query.filter(ParsedTransaction.email_account_id == account_id)

    total = query.count()
    transactions = (
        query.order_by(ParsedTransaction.transaction_date.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )

    return {
        "transactions": [
            {
                "id": str(t.id),
                "merchant_name": t.merchant_name,
                "merchant_normalized": (
                    t.normalized_transaction.merchant_normalized
                    if t.normalized_transaction else None
                ),
                "amount": str(t.amount),
                "transaction_date": t.transaction_date.isoformat(),
                "card_last_four": t.card_last_four,
                "transaction_type": t.transaction_type,
                "confidence_score": float(t.confidence_score),
                "category": (
                    t.normalized_transaction.category
                    if t.normalized_transaction else None
                ),
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
