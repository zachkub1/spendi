"""
Authentication service module.
Handles Google OAuth flow, JWT token creation/validation, and user management.
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User, AuditLog, AuditLogAction


class AuthService:
    """Service for authentication and authorization operations."""

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """
        Create a JWT access token for the given user.

        Args:
            user_id: UUID of the user
            email: User's email address

        Returns:
            Encoded JWT token string
        """
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_access_token(token: str) -> Optional[dict]:
        """
        Verify and decode a JWT access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def verify_google_token(token: str) -> Optional[dict]:
        """
        Verify a Google ID token and extract user information.

        Args:
            token: Google ID token string

        Returns:
            User info dict if valid, None otherwise
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # Verify the issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                return None

            return {
                "sub": idinfo["sub"],  # Google's unique user ID
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
            }
        except ValueError:
            return None

    @staticmethod
    def get_or_create_user(
        db: Session, oauth_subject_id: str, email: str, display_name: Optional[str] = None
    ) -> User:
        """
        Get an existing user or create a new one from OAuth data.

        Args:
            db: Database session
            oauth_subject_id: Google's unique user ID (sub claim)
            email: User's email address
            display_name: User's display name (optional)

        Returns:
            User instance
        """
        # Try to find existing user by OAuth subject ID
        user = (
            db.query(User)
            .filter(User.oauth_subject_id == oauth_subject_id)
            .filter(User.deleted_at.is_(None))
            .first()
        )

        if user:
            # Update last login time
            user.last_login_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            return user

        # Create new user
        user = User(
            email=email,
            oauth_provider="google",
            oauth_subject_id=oauth_subject_id,
            display_name=display_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_audit_log(
        db: Session,
        user_id: str,
        action: AuditLogAction,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """
        Create an audit log entry for security-sensitive events.

        Args:
            db: Database session
            user_id: UUID of the user
            action: Action type from AuditLogAction enum
            resource_type: Type of resource affected (e.g., "EmailAccount")
            resource_id: UUID of the affected resource
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            details: Additional context (optional)

        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log