"""
Authentication routes for Google OAuth and JWT-based sessions.
"""
import logging
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
from app.db.models import User, AuditLogAction

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
