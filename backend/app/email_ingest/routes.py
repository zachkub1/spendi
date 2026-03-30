"""
Email account management routes.
API endpoints for connecting/disconnecting Gmail accounts.
"""
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
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=credentials.expiry.timestamp() - datetime.now(timezone.utc).timestamp())

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

    except HTTPException:
        raise
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
    """List user's connected email accounts (excludes demo accounts)."""
    accounts = (
        db.query(EmailAccount)
        .filter(
            EmailAccount.user_id == current_user.id,
            EmailAccount.provider != "demo"
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
    logger.info(f"[SYNC_API] User {current_user.id} requesting sync for account {account_id}")

    # Verify ownership
    email_account = db.query(EmailAccount).filter_by(
        id=account_id,
        user_id=current_user.id
    ).first()

    if not email_account:
        logger.warning(f"[SYNC_API] Account {account_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found"
        )

    logger.info(f"[SYNC_API] Account found: {email_account.email_address}, sync_status={email_account.sync_status}")

    if email_account.sync_status == "in_progress":
        logger.warning(f"[SYNC_API] Sync already in progress for {account_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync already in progress"
        )

    # Verify OAuth tokens exist
    if not email_account.oauth_access_token or not email_account.oauth_refresh_token:
        logger.error(f"[SYNC_API] Missing OAuth tokens for account {account_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email account is missing OAuth tokens. Please reconnect your Gmail account."
        )

    # Enqueue Celery task
    try:
        logger.info(f"[SYNC_API] Importing Celery task...")
        from jobs.tasks import sync_email_account_task

        logger.info(f"[SYNC_API] Enqueuing sync task for {account_id}...")
        task = sync_email_account_task.delay(str(email_account.id))

        logger.info(f"[SYNC_API] Task enqueued successfully: task_id={task.id}")

        return {
            "message": "Sync started",
            "task_id": task.id,
            "account_id": str(email_account.id),
            "email_address": email_account.email_address
        }
    except ImportError as e:
        logger.error(f"[SYNC_API] Failed to import Celery task: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background job system not available. Please check Celery worker is running."
        )
    except Exception as e:
        logger.error(f"[SYNC_API] Failed to enqueue sync task: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync: {str(e)}"
        )


@router.get("/transactions")
async def list_parsed_transactions(
    account_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    include_demo: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List parsed transactions for user with optional category from normalized record."""
    from app.db.models import ParsedTransaction
    from sqlalchemy.orm import joinedload

    query = (
        db.query(ParsedTransaction)
        .options(joinedload(ParsedTransaction.normalized_transaction))
        .join(EmailAccount)
        .filter(EmailAccount.user_id == current_user.id)
    )

    if not include_demo:
        query = query.filter(EmailAccount.provider != "demo")

    if account_id:
        query = query.filter(ParsedTransaction.email_account_id == account_id)

    total = query.count()
    transactions = (
        query
        .order_by(ParsedTransaction.transaction_date.desc())
        .offset(offset)
        .limit(limit)
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
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/demo-sync")
async def demo_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inject demo email data to test the parsing pipeline without real Gmail access.

    - Finds or creates a demo EmailAccount for the user.
    - Runs each mock email through the real parser registry.
    - Stores ParsedTransactions (and NormalizedTransactions if payment instruments exist).
    - Idempotent: re-running skips already-processed emails.
    """
    from app.email_ingest.demo_data import DEMO_EMAILS
    from app.email_ingest.parsers.registry import ParserRegistry
    from app.db.models import (
        RawEmail, ParsedTransaction, NormalizedTransaction,
        PaymentInstrument, PaymentInstrumentType, PaymentInstrumentStatus,
    )
    from app.transactions.matching_service import PaymentInstrumentMatchingService

    # ── 1. Find or create the demo EmailAccount ───────────────────────────────
    demo_account = db.query(EmailAccount).filter(
        EmailAccount.user_id == current_user.id,
        EmailAccount.provider == "demo"
    ).first()

    if not demo_account:
        demo_account = EmailAccount(
            user_id=current_user.id,
            provider="demo",
            email_address="demo@ledgerly.demo",
            sync_enabled=False,
            sync_status="success",
        )
        db.add(demo_account)
        db.flush()

    # ── 2. Auto-create demo payment instruments (idempotent) ─────────────────
    # These match the card numbers embedded in the demo email bodies so that
    # PaymentInstrumentMatchingService can link ParsedTransactions → NormalizedTransactions.
    _DEMO_INSTRUMENTS = [
        dict(type=PaymentInstrumentType.CREDIT_CARD, issuer="Chase",
             display_name="Demo Chase Card", network="Visa",
             last_four_digits="4242", account_identifier=None),
        dict(type=PaymentInstrumentType.CREDIT_CARD, issuer="American Express",
             display_name="Demo Amex Card", network="Amex",
             last_four_digits="9876", account_identifier=None),
        dict(type=PaymentInstrumentType.CREDIT_CARD, issuer="Discover",
             display_name="Demo Discover Card", network="Discover",
             last_four_digits="5555", account_identifier=None),
        dict(type=PaymentInstrumentType.P2P_ACCOUNT, issuer="Venmo/Zelle",
             display_name="Demo P2P Account", network=None,
             last_four_digits=None, account_identifier="demo_p2p"),
    ]
    for inst_data in _DEMO_INSTRUMENTS:
        exists = db.query(PaymentInstrument).filter(
            PaymentInstrument.user_id == current_user.id,
            (PaymentInstrument.last_four_digits == inst_data["last_four_digits"])
            if inst_data["last_four_digits"]
            else (PaymentInstrument.account_identifier == inst_data["account_identifier"]),
        ).first()
        if not exists:
            db.add(PaymentInstrument(
                user_id=current_user.id,
                status=PaymentInstrumentStatus.ACTIVE,
                **inst_data,
            ))
    db.flush()

    parsed_count = 0
    non_transaction_count = 0
    already_exists_count = 0

    # ── 3. Process each demo email ────────────────────────────────────────────
    for email in DEMO_EMAILS:
        existing = db.query(RawEmail).filter_by(message_id=email["message_id"]).first()

        if existing and existing.parsing_status in ("success", "non_transaction"):
            already_exists_count += 1
            continue

        if existing:
            # Reset a previously-failed demo email for retry
            raw_email = existing
            raw_email.parsing_status = "pending"
            raw_email.error_message = None
            raw_email.parser_used = None
            db.flush()
        else:
            raw_email = RawEmail(
                email_account_id=demo_account.id,
                message_id=email["message_id"],
                subject=email["subject"],
                sender=email["from"],
                received_at=email["received_at"],
                parsing_status="pending",
            )
            db.add(raw_email)
            db.flush()

        # Non-parseable emails (marketing, statements) — mark directly
        if not email.get("parseable", True):
            raw_email.parsing_status = "non_transaction"
            raw_email.error_message = "non_transactional_email"
            non_transaction_count += 1
            continue

        # Run through real parser
        parser = ParserRegistry.get_parser(email["from"], email["subject"])
        if not parser:
            raw_email.parsing_status = "failed"
            raw_email.error_message = "no_parser_matched"
            logger.warning(f"[DEMO] No parser matched for {email['message_id']}")
            continue

        parse_result = parser.parse(email["subject"], email["body"])
        raw_email.parser_used = parser.provider

        if parse_result.status == "transaction":
            parsed_txn = ParsedTransaction(
                raw_email_id=raw_email.id,
                email_account_id=demo_account.id,
                merchant_name=parse_result.data.merchant_name,
                amount=parse_result.data.amount,
                currency="USD",
                transaction_date=parse_result.data.transaction_date,
                card_last_four=parse_result.data.card_last_four,
                transaction_type=parse_result.data.transaction_type,
                confidence_score=parse_result.data.confidence_score,
                parser_version=parser.get_version(),
            )
            db.add(parsed_txn)
            db.flush()

            raw_email.parsing_status = "success"
            parsed_count += 1
            logger.debug(
                f"[DEMO] Parsed: {parse_result.data.merchant_name} "
                f"${parse_result.data.amount} via {parser.provider}"
            )

            # Attempt normalization (non-fatal — requires payment instruments)
            try:
                normalized = PaymentInstrumentMatchingService.match_and_normalize(
                    db=db,
                    parsed_transaction=parsed_txn,
                    user_id=str(current_user.id),
                )
                if normalized:
                    logger.debug(
                        f"[DEMO] Normalized: {normalized.merchant_normalized} ({normalized.category})"
                    )
            except Exception as norm_err:
                logger.warning(f"[DEMO] Normalization skipped for {parsed_txn.merchant_name}: {norm_err}")

        elif parse_result.status == "non_transaction":
            raw_email.parsing_status = "non_transaction"
            raw_email.error_message = parse_result.reason
            non_transaction_count += 1
        else:
            raw_email.parsing_status = "failed"
            raw_email.error_message = parse_result.reason

    # ── 4. Retroactively normalize any ParsedTransactions that were created
    #       before payment instruments existed (e.g. on a previous demo-sync run).
    unmatched = (
        db.query(ParsedTransaction)
        .outerjoin(NormalizedTransaction, NormalizedTransaction.parsed_transaction_id == ParsedTransaction.id)
        .filter(
            ParsedTransaction.email_account_id == demo_account.id,
            NormalizedTransaction.id.is_(None),
        )
        .all()
    )
    retro_count = 0
    for pt in unmatched:
        try:
            norm = PaymentInstrumentMatchingService.match_and_normalize(
                db=db,
                parsed_transaction=pt,
                user_id=str(current_user.id),
            )
            if norm:
                retro_count += 1
        except Exception as retro_err:
            logger.warning(f"[DEMO] Retro-normalization failed for {pt.merchant_name}: {retro_err}")

    if retro_count:
        logger.info(f"[DEMO] Retroactively normalized {retro_count} previously-unmatched transactions")

    demo_account.last_sync_at = datetime.now(timezone.utc)
    demo_account.sync_status = "success"
    db.commit()

    logger.info(
        f"[DEMO] Sync complete for user {current_user.id}: "
        f"{parsed_count} parsed, {non_transaction_count} non-transaction, "
        f"{already_exists_count} already existed"
    )

    return {
        "message": "Demo sync complete",
        "parsed": parsed_count,
        "non_transaction": non_transaction_count,
        "already_exists": already_exists_count,
    }
