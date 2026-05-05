"""
Authentication service module.
Handles Google OAuth flow, JWT token creation/validation, and user management.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from redis import from_url as redis_from_url
from redis import RedisError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User, AuditLog, AuditLogAction

logger = logging.getLogger(__name__)

_STATE_TTL_SECONDS = 600  # 10 minutes
_STATE_KEY_PREFIX = "oauth_state:"

# Redis-backed state store works across multiple uvicorn workers.
# Falls back to in-process dict when Redis is unavailable (dev/test).
try:
    _redis = redis_from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _redis.ping()
    _USE_REDIS = True
    logger.info("[AUTH] OAuth state store: Redis")
except Exception:
    _USE_REDIS = False
    _redis = None
    _OAUTH_STATES: dict[str, datetime] = {}
    logger.warning("[AUTH] OAuth state store: in-process (Redis unavailable)")


class AuthService:
    """Service for authentication and authorization operations."""

    # ------------------------------------------------------------------
    # OAuth State (CSRF protection)
    # ------------------------------------------------------------------

    @staticmethod
    def store_oauth_state(state: str) -> None:
        """Persist a freshly generated OAuth state token so the callback can verify it."""
        if _USE_REDIS and _redis is not None:
            try:
                _redis.setex(f"{_STATE_KEY_PREFIX}{state}", _STATE_TTL_SECONDS, "1")
                return
            except RedisError:
                logger.warning("[AUTH] Redis unavailable, falling back to in-process store")
        _prune_expired_states()
        _OAUTH_STATES[state] = datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL_SECONDS)

    @staticmethod
    def validate_oauth_state(state: str) -> bool:
        """
        Validate and consume an OAuth state token (one-time use).
        Returns True if valid.
        """
        if _USE_REDIS and _redis is not None:
            try:
                deleted = _redis.delete(f"{_STATE_KEY_PREFIX}{state}")
                return deleted == 1
            except RedisError:
                logger.warning("[AUTH] Redis unavailable, falling back to in-process store")
        _prune_expired_states()
        expiry = _OAUTH_STATES.pop(state, None)
        if expiry is None:
            return False
        return datetime.now(timezone.utc) <= expiry

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """Create a JWT access token for the given user."""
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_hex(16),  # unique token ID (enables future revocation)
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_access_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT access token. Returns payload or None."""
        try:
            return jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # ------------------------------------------------------------------
    # Google ID Token
    # ------------------------------------------------------------------

    @staticmethod
    def verify_google_token(token: str) -> Optional[dict]:
        """Verify a Google ID token and return user info dict, or None."""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
            if idinfo.get("iss") not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                return None
            return {
                "sub": idinfo["sub"],
                "email": idinfo.get("email"),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
            }
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    @staticmethod
    def get_or_create_user(
        db: Session,
        oauth_subject_id: str,
        email: str,
        display_name: Optional[str] = None,
    ) -> User:
        """Get an existing user or create a new one from OAuth data."""
        user = (
            db.query(User)
            .filter(User.oauth_subject_id == oauth_subject_id)
            .filter(User.deleted_at.is_(None))
            .first()
        )

        if user:
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            return user

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

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

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
        """Create an audit log entry for security-sensitive events."""
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


def _prune_expired_states() -> None:
    """Remove expired state tokens to prevent unbounded memory growth."""
    now = datetime.now(timezone.utc)
    expired = [k for k, exp in list(_OAUTH_STATES.items()) if now > exp]
    for k in expired:
        del _OAUTH_STATES[k]
