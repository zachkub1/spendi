"""
Authentication routes for Google OAuth and JWT-based sessions.
"""
import logging
import requests as http_requests
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.config import settings
from app.auth.service import AuthService
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.db.models import (
    User, AuditLogAction,
    EmailAccount, RawEmail, ParsedTransaction,
    NormalizedTransaction, PaymentInstrument,
    ReimbursementLink, AuditLog, Feedback,
)
from app.email_ingest.service import EmailAccountService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    oauth_provider: str

    class Config:
        from_attributes = True


@router.get("/login")
async def login():
    """Initiate Google OAuth login flow."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured.",
        )

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=settings.GOOGLE_OAUTH_SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    # Persist state so callback can validate it (CSRF protection)
    AuthService.store_oauth_state(state)

    return {"authorization_url": authorization_url, "state": state}


@router.get("/callback")
async def callback(
    code: str,
    state: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth callback from Google."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured.",
        )

    # Validate state to prevent CSRF
    if not state or not AuthService.validate_oauth_state(state):
        logger.warning("[AUTH] OAuth callback received with missing or invalid state")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/error?message=invalid_state"
        )

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=settings.GOOGLE_OAUTH_SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)

        credentials: Credentials = flow.credentials

        user_info = AuthService.verify_google_token(credentials.id_token)
        if not user_info:
            raise ValueError("Google ID token verification failed")

        user = AuthService.get_or_create_user(
            db=db,
            oauth_subject_id=user_info["sub"],
            email=user_info["email"],
            display_name=user_info.get("name"),
        )

        client_ip = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        AuthService.create_audit_log(
            db=db,
            user_id=str(user.id),
            action=AuditLogAction.USER_LOGIN,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        access_token = AuthService.create_access_token(
            user_id=str(user.id), email=user.email
        )

        # Token in fragment: never sent to server, not in access logs or Referer headers
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback#token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # Never expose internal exception messages to the browser
        logger.error("[AUTH] OAuth callback error: %s", type(e).__name__, exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/error?message=authentication_failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        oauth_provider=current_user.oauth_provider,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout endpoint — audit logged; token invalidation is client-side."""
    AuthService.create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action=AuditLogAction.USER_LOGOUT,
    )
    return {"message": "Logged out successfully"}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete the authenticated user's account and all associated data.

    Deletion order respects FK constraints:
      reimbursement_links → normalized_transactions → parsed_transactions
      → raw_emails → email_accounts → payment_instruments
      → feedback → audit_logs → user

    Google OAuth tokens are revoked best-effort before data is removed.
    """
    user_id = current_user.id
    logger.info("[DELETE_ACCOUNT] Starting deletion for user %s (%s)", user_id, current_user.email)

    # ── 1. Revoke Google OAuth tokens (best-effort, never blocks deletion) ──────
    email_accounts = db.query(EmailAccount).filter(EmailAccount.user_id == user_id).all()
    for account in email_accounts:
        try:
            creds = EmailAccountService.get_decrypted_credentials(account)
            if creds.token:
                http_requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": creds.token},
                    timeout=5,
                )
                logger.info("[DELETE_ACCOUNT] Revoked Gmail token for account %s", account.id)
        except Exception as exc:
            logger.warning("[DELETE_ACCOUNT] Token revocation failed for account %s (non-fatal): %s", account.id, exc)

    # ── 2. Delete in FK dependency order ─────────────────────────────────────────

    # reimbursement_links: FK → normalized_transactions (must go first)
    nt_ids = db.query(NormalizedTransaction.id).filter(NormalizedTransaction.user_id == user_id)
    db.query(ReimbursementLink).filter(
        ReimbursementLink.p2p_transaction_id.in_(nt_ids)
    ).delete(synchronize_session=False)
    db.query(ReimbursementLink).filter(
        ReimbursementLink.target_transaction_id.in_(nt_ids)
    ).delete(synchronize_session=False)

    # normalized_transactions
    db.query(NormalizedTransaction).filter(NormalizedTransaction.user_id == user_id).delete(synchronize_session=False)

    # parsed_transactions: scoped via email accounts
    ea_ids = db.query(EmailAccount.id).filter(EmailAccount.user_id == user_id)
    db.query(ParsedTransaction).filter(ParsedTransaction.email_account_id.in_(ea_ids)).delete(synchronize_session=False)

    # raw_emails
    db.query(RawEmail).filter(RawEmail.email_account_id.in_(ea_ids)).delete(synchronize_session=False)

    # email_accounts, payment_instruments, feedback, audit_logs
    db.query(EmailAccount).filter(EmailAccount.user_id == user_id).delete(synchronize_session=False)
    db.query(PaymentInstrument).filter(PaymentInstrument.user_id == user_id).delete(synchronize_session=False)
    db.query(Feedback).filter(Feedback.user_id == user_id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(synchronize_session=False)

    # user row last
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)

    db.commit()
    logger.info("[DELETE_ACCOUNT] Completed deletion for user %s", user_id)
    return None
