"""
Email account service layer.
Business logic for managing email accounts and OAuth tokens.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials

from app.db.models import EmailAccount
from app.email_ingest.encryption import TokenEncryption
import logging

logger = logging.getLogger(__name__)


class EmailAccountService:
    """Service for managing email accounts."""

    @staticmethod
    def create_email_account(
        db: Session,
        user_id: str,
        email_address: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ) -> EmailAccount:
        """
        Create email account with encrypted OAuth tokens.

        Args:
            db: Database session
            user_id: User ID
            email_address: Email address
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration time

        Returns:
            Created EmailAccount instance
        """
        # Encrypt tokens
        encrypted_access, encrypted_dek_access, iv_access = TokenEncryption.encrypt_token(access_token)
        encrypted_refresh, encrypted_dek_refresh, iv_refresh = TokenEncryption.encrypt_token(refresh_token)

        # Create email account record
        email_account = EmailAccount(
            user_id=user_id,
            provider="gmail",
            email_address=email_address,
            oauth_access_token=encrypted_access,
            oauth_refresh_token=encrypted_refresh,
            oauth_token_expires_at=expires_at,
            encryption_key=encrypted_dek_access,  # Store DEK for access token
            encryption_iv=iv_access,
            sync_enabled=True
        )

        db.add(email_account)
        db.commit()
        db.refresh(email_account)

        logger.info(f"Created email account for user {user_id}: {email_address}")
        return email_account

    @staticmethod
    def get_decrypted_credentials(email_account: EmailAccount) -> Credentials:
        """
        Get decrypted Google OAuth credentials from email account.

        Args:
            email_account: EmailAccount instance

        Returns:
            Google Credentials object with decrypted tokens
        """
        # Decrypt access token
        access_token = TokenEncryption.decrypt_token(
            email_account.oauth_access_token,
            email_account.encryption_key,
            email_account.encryption_iv
        )

        # Decrypt refresh token
        refresh_token = TokenEncryption.decrypt_token(
            email_account.oauth_refresh_token,
            email_account.encryption_key,
            email_account.encryption_iv
        )

        # Create Credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,  # Not needed for API calls
            client_secret=None
        )

        return credentials

    @staticmethod
    def disconnect_email_account(db: Session, account_id: str) -> None:
        """
        Disconnect email account (delete from database).

        Args:
            db: Database session
            account_id: Email account ID
        """
        email_account = db.query(EmailAccount).filter_by(id=account_id).first()
        if email_account:
            db.delete(email_account)
            db.commit()
            logger.info(f"Deleted email account {account_id}")
