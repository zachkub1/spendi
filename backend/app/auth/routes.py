"""
Authentication routes for Google OAuth and JWT-based sessions.
"""
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

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    """Response model for successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """User information response model."""

    id: str
    email: str
    display_name: Optional[str]
    oauth_provider: str

    class Config:
        from_attributes = True


@router.get("/login")
async def login():
    """
    Initiate Google OAuth login flow.
    Returns the authorization URL to redirect the user to.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Create OAuth flow
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

    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type="offline",  # Request refresh token
        include_granted_scopes="true",
        prompt="consent",  # Force consent screen to ensure refresh token
    )

    return {"authorization_url": authorization_url, "state": state}


@router.get("/callback")
async def callback(
    code: str,
    state: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Handle OAuth callback from Google.
    Exchanges authorization code for tokens and creates user session.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        request: FastAPI request object
        db: Database session

    Returns:
        Redirects to frontend with JWT token
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured.",
        )

    try:
        # Create OAuth flow
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

        # Exchange authorization code for tokens
        flow.fetch_token(code=code)

        # Get credentials
        credentials: Credentials = flow.credentials

        # Verify the ID token and extract user info
        user_info = AuthService.verify_google_token(credentials.id_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )

        # Get or create user
        user = AuthService.get_or_create_user(
            db=db,
            oauth_subject_id=user_info["sub"],
            email=user_info["email"],
            display_name=user_info.get("name"),
        )

        # Create audit log
        client_ip = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        AuthService.create_audit_log(
            db=db,
            user_id=str(user.id),
            action=AuditLogAction.USER_LOGIN,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Create JWT access token
        access_token = AuthService.create_access_token(
            user_id=str(user.id), email=user.email
        )

        # Redirect to frontend with token
        # Frontend should extract the token from URL and store it
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # Log error and redirect to frontend with error
        error_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current user from JWT token

    Returns:
        User information
    """
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
    """
    Logout endpoint.
    Currently JWT is stateless, so logout is handled client-side by deleting the token.
    This endpoint exists for audit logging and future server-side session management.

    Args:
        current_user: Current user from JWT token
        db: Database session

    Returns:
        Success message
    """
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action=AuditLogAction.USER_LOGOUT,
    )

    return {"message": "Logged out successfully"}