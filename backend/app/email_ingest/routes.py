"""
Email account management routes.
API endpoints for connecting/disconnecting Gmail accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import get_db
from app.db.models import User, EmailAccount
from app.auth.dependencies import get_current_user
from app.email_ingest.service import EmailAccountService
from app.email_ingest.gmail_client import GmailClient
from app.config import settings
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email Accounts"])


@router.get("/auth/debug")
async def debug_oauth_config():
    """Debug endpoint to verify OAuth configuration."""
    client_config, redirect_uri = _get_gmail_oauth_config()
    return {
        "client_id": client_config["web"]["client_id"],
        "redirect_uri": redirect_uri,
        "redirect_uri_bytes": list(redirect_uri.encode('utf-8')),
        "frontend_url": settings.FRONTEND_URL,
        "scopes": settings.GOOGLE_OAUTH_SCOPES,
        "token_uri": client_config["web"]["token_uri"],
        "instructions": [
            "Verify in Google Cloud Console that:",
            f"1. Client ID matches: {client_config['web']['client_id']}",
            f"2. Authorized redirect URIs includes EXACTLY: {redirect_uri}",
            "3. No trailing slash unless you add one to both sides",
            "4. This SAME client ID has Gmail API enabled"
        ]
    }


@router.get("/auth/login")
async def gmail_auth_login():
    """
    Initiate Gmail OAuth flow (separate from user login).
    Returns authorization URL with gmail scope.
    """
    try:
        # Use single source of truth for OAuth config
        client_config, redirect_uri = _get_gmail_oauth_config()

        logger.info("=" * 80)
        logger.info("GMAIL AUTH INITIATION")
        logger.info(f"client_id: {client_config['web']['client_id']}")
        logger.info(f"redirect_uri: {redirect_uri}")
        logger.info(f"scopes: {settings.GOOGLE_OAUTH_SCOPES}")

        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )

        logger.info(f"Generated state: {state}")
        logger.info("=" * 80)

        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"Failed to create Gmail auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Gmail authorization"
        )


class ConnectGmailRequest(BaseModel):
    """Request model for connecting Gmail account."""
    code: str


# In-memory cache to prevent authorization code reuse
# In production, use Redis with expiration
_used_auth_codes: set = set()


def _get_gmail_oauth_config() -> tuple[dict, str]:
    """
    Single source of truth for Gmail OAuth configuration.
    Returns (client_config, redirect_uri) to ensure consistency.
    """
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


class EmailAccountResponse(BaseModel):
    """Response model for email account."""
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
    db: Session = Depends(get_db)
):
    """
    Connect Gmail account using OAuth code.
    Exchanges code for tokens, encrypts them, and stores in database.
    """
    try:
        # DEFENSE: Prevent authorization code reuse
        if request.code in _used_auth_codes:
            logger.error(f"Authorization code reuse detected for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code has already been used"
            )

        # Use SAME single source of truth for OAuth config
        client_config, redirect_uri = _get_gmail_oauth_config()

        logger.info("=" * 80)
        logger.info("GMAIL TOKEN EXCHANGE")
        logger.info(f"user_id: {current_user.id}")
        logger.info(f"client_id: {client_config['web']['client_id']}")
        logger.info(f"redirect_uri: {redirect_uri}")
        logger.info(f"redirect_uri (repr): {repr(redirect_uri)}")
        logger.info(f"redirect_uri (bytes): {redirect_uri.encode('utf-8')}")
        logger.info(f"code (first 20): {request.code[:20]}...")
        logger.info(f"code length: {len(request.code)}")
        logger.info(f"code previously used: False")

        # Create OAuth flow - MUST use same config as auth initiation
        flow = Flow.from_client_config(
            client_config,
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=redirect_uri
        )

        # Exchange code for tokens
        logger.info("Calling Google token endpoint...")
        logger.info(f"Token request: client_id={client_config['web']['client_id']}, redirect_uri={redirect_uri}, grant_type=authorization_code")

        try:
            flow.fetch_token(code=request.code)
            # Mark code as used ONLY after successful exchange
            _used_auth_codes.add(request.code)
        except Exception as token_error:
            logger.error("=" * 80)
            logger.error("TOKEN EXCHANGE FAILED")
            logger.error(f"Error type: {type(token_error).__name__}")
            logger.error(f"Error message: {str(token_error)}")

            # Try to extract more details from the error
            if hasattr(token_error, 'response'):
                logger.error(f"Response status: {token_error.response.status_code if hasattr(token_error.response, 'status_code') else 'N/A'}")
                logger.error(f"Response body: {token_error.response.text if hasattr(token_error.response, 'text') else 'N/A'}")
            if hasattr(token_error, 'args'):
                logger.error(f"Error args: {token_error.args}")

            logger.error(f"Client ID used: {settings.GOOGLE_CLIENT_ID}")
            logger.error(f"Redirect URI used: {redirect_uri}")
            logger.error("=" * 80)
            raise

        logger.info("Token exchange successful!")
        logger.info("=" * 80)
        credentials = flow.credentials

        # Get user's email address from Gmail API
        gmail_client = GmailClient(credentials)
        profile = gmail_client.service.users().getProfile(userId='me').execute()
        email_address = profile['emailAddress']

        # Check if account already exists
        existing = db.query(EmailAccount).filter_by(
            user_id=current_user.id,
            email_address=email_address
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email account already connected"
            )

        # Calculate token expiration
        expires_at = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - datetime.utcnow().timestamp())

        # Create email account with encrypted tokens
        email_account = EmailAccountService.create_email_account(
            db=db,
            user_id=str(current_user.id),
            email_address=email_address,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at
        )

        return {
            "message": "Gmail account connected successfully",
            "account": {
                "id": str(email_account.id),
                "email_address": email_account.email_address,
                "provider": email_account.provider,
                "sync_enabled": email_account.sync_enabled,
                "last_sync_at": email_account.last_sync_at.isoformat() if email_account.last_sync_at else None,
                "sync_status": email_account.sync_status,
                "created_at": email_account.created_at.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to connect Gmail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Gmail account: {str(e)}"
        )


@router.get("/accounts")
async def list_email_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's connected email accounts."""
    accounts = db.query(EmailAccount).filter_by(user_id=current_user.id).all()

    return {
        "accounts": [
            {
                "id": str(acc.id),
                "email_address": acc.email_address,
                "provider": acc.provider,
                "sync_enabled": acc.sync_enabled,
                "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
                "sync_status": acc.sync_status,
                "created_at": acc.created_at.isoformat()
            }
            for acc in accounts
        ]
    }


@router.delete("/accounts/{account_id}")
async def disconnect_email_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect email account."""
    # Verify ownership
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id
    ).first()

    if not email_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )

    EmailAccountService.disconnect_email_account(db, account_id)

    return {"message": "Email account disconnected successfully"}


@router.get("/messages")
async def list_messages(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List messages from Gmail (for testing only).
    Returns list of message IDs.
    """
    # Verify ownership
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id
    ).first()

    if not email_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )

    # Get decrypted credentials
    credentials = EmailAccountService.get_decrypted_credentials(email_account)

    # List messages
    gmail_client = GmailClient(credentials)
    messages = gmail_client.list_messages(
        sender_filter=["chase.com", "venmo.com"],
        max_results=10
    )

    return {"messages": messages}


@router.post("/sync/{account_id}")
async def trigger_sync(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger email sync for an account.
    Runs in background task (Celery).
    """
    # Verify ownership
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id
    ).first()

    if not email_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )

    if email_account.sync_status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync already in progress"
        )

    # Enqueue Celery task
    from jobs.tasks import sync_email_account_task
    task = sync_email_account_task.delay(str(email_account.id))

    return {
        "message": "Sync started",
        "task_id": task.id
    }


@router.get("/transactions")
async def list_parsed_transactions(
    account_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List parsed transactions for user."""
    from app.db.models import ParsedTransaction

    query = db.query(ParsedTransaction).join(EmailAccount).filter(
        EmailAccount.user_id == current_user.id
    )

    if account_id:
        query = query.filter(ParsedTransaction.email_account_id == account_id)

    transactions = query.order_by(
        ParsedTransaction.transaction_date.desc()
    ).limit(limit).all()

    return {
        "transactions": [
            {
                "id": str(t.id),
                "merchant_name": t.merchant_name,
                "amount": str(t.amount),
                "transaction_date": t.transaction_date.isoformat(),
                "card_last_four": t.card_last_four,
                "transaction_type": t.transaction_type,
                "confidence_score": float(t.confidence_score),
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    }
