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
        # Encrypt both tokens using SHARED DEK/IV (envelope encryption)
        # This ensures we only need to store one DEK/IV pair
        encrypted_access, encrypted_dek, iv = TokenEncryption.encrypt_token(access_token)

        # Reuse the SAME DEK and IV for refresh token encryption
        # This is secure because we're using envelope encryption - each token
        # gets a unique ciphertext even with the same DEK/IV combo
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64

        # Decrypt DEK to encrypt refresh token with it
        master_key = TokenEncryption._get_master_key()
        iv_bytes = base64.b64decode(iv)
        encrypted_dek_bytes = base64.b64decode(encrypted_dek)

        aesgcm_key = AESGCM(master_key)
        dek = aesgcm_key.decrypt(iv_bytes, encrypted_dek_bytes, None)

        # Encrypt refresh token with the SAME DEK but NEW IV
        refresh_iv = os.urandom(12)
        aesgcm_data = AESGCM(dek)
        encrypted_refresh_bytes = aesgcm_data.encrypt(refresh_iv, refresh_token.encode(), None)
        encrypted_refresh = base64.b64encode(encrypted_refresh_bytes).decode()

        # Store refresh token's IV separately (we'll need a new DB column for this)
        # For now, we'll use a JSON structure in oauth_refresh_token to store both
        import json
        refresh_token_data = {
            'ciphertext': encrypted_refresh,
            'iv': base64.b64encode(refresh_iv).decode()
        }
        encrypted_refresh_with_iv = json.dumps(refresh_token_data)

        # Create email account record
        email_account = EmailAccount(
            user_id=user_id,
            provider="gmail",
            email_address=email_address,
            oauth_access_token=encrypted_access,
            oauth_refresh_token=encrypted_refresh_with_iv,  # JSON with ciphertext + iv
            oauth_token_expires_at=expires_at,
            encryption_key=encrypted_dek,  # Shared DEK for both tokens
            encryption_iv=iv,  # IV for access token
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

        # Decrypt refresh token (stored as JSON with separate IV)
        import json
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        try:
            # Try new format (JSON with ciphertext + iv)
            refresh_data = json.loads(email_account.oauth_refresh_token)
            encrypted_refresh = refresh_data['ciphertext']
            refresh_iv = refresh_data['iv']

            # Decrypt using shared DEK but refresh token's own IV
            encrypted_refresh_bytes = base64.b64decode(encrypted_refresh)
            refresh_iv_bytes = base64.b64decode(refresh_iv)
            encrypted_dek_bytes = base64.b64decode(email_account.encryption_key)
            iv_bytes = base64.b64decode(email_account.encryption_iv)

            # Decrypt DEK
            master_key = TokenEncryption._get_master_key()
            aesgcm_key = AESGCM(master_key)
            dek = aesgcm_key.decrypt(iv_bytes, encrypted_dek_bytes, None)

            # Decrypt refresh token
            aesgcm_data = AESGCM(dek)
            refresh_token_bytes = aesgcm_data.decrypt(refresh_iv_bytes, encrypted_refresh_bytes, None)
            refresh_token = refresh_token_bytes.decode()

        except (json.JSONDecodeError, KeyError):
            # Fallback: old format (direct encrypted string, same IV as access - BROKEN)
            logger.warning(f"Email account {email_account.id} uses old broken encryption format")
            raise ValueError("Refresh token encrypted with incompatible format. Please reconnect Gmail account.")

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
