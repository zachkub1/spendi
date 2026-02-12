"""
Envelope encryption for OAuth tokens.
Uses AES-256-GCM with generated DEK, encrypted by master KEK from environment.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens using envelope encryption."""

    @staticmethod
    def _get_master_key() -> bytes:
        """Get master encryption key from settings and convert from hex."""
        if not settings.ENCRYPTION_MASTER_KEY:
            raise ValueError("ENCRYPTION_MASTER_KEY not configured")
        return bytes.fromhex(settings.ENCRYPTION_MASTER_KEY)

    @staticmethod
    def encrypt_token(plaintext: str) -> tuple[str, str, str]:
        """
        Encrypt a token using envelope encryption.

        Args:
            plaintext: The token to encrypt

        Returns:
            Tuple of (encrypted_token, encrypted_dek, iv) all base64-encoded
        """
        # Generate a random 256-bit DEK (Data Encryption Key)
        dek = AESGCM.generate_key(bit_length=256)

        # Generate random IV (96 bits recommended for GCM)
        iv = os.urandom(12)

        # Encrypt the plaintext token with the DEK
        aesgcm_data = AESGCM(dek)
        encrypted_token = aesgcm_data.encrypt(iv, plaintext.encode(), None)

        # Encrypt the DEK with the master key (KEK)
        master_key = TokenEncryption._get_master_key()
        aesgcm_key = AESGCM(master_key)
        encrypted_dek = aesgcm_key.encrypt(iv, dek, None)

        # Return all as base64-encoded strings for storage
        return (
            base64.b64encode(encrypted_token).decode(),
            base64.b64encode(encrypted_dek).decode(),
            base64.b64encode(iv).decode(),
        )

    @staticmethod
    def decrypt_token(encrypted_token: str, encrypted_dek: str, iv: str) -> str:
        """
        Decrypt a token using envelope encryption.

        Args:
            encrypted_token: Base64-encoded encrypted token
            encrypted_dek: Base64-encoded encrypted DEK
            iv: Base64-encoded initialization vector

        Returns:
            Decrypted plaintext token
        """
        # Decode from base64
        encrypted_token_bytes = base64.b64decode(encrypted_token)
        encrypted_dek_bytes = base64.b64decode(encrypted_dek)
        iv_bytes = base64.b64decode(iv)

        # Decrypt the DEK with the master key
        master_key = TokenEncryption._get_master_key()
        aesgcm_key = AESGCM(master_key)
        dek = aesgcm_key.decrypt(iv_bytes, encrypted_dek_bytes, None)

        # Decrypt the token with the DEK
        aesgcm_data = AESGCM(dek)
        plaintext_bytes = aesgcm_data.decrypt(iv_bytes, encrypted_token_bytes, None)

        return plaintext_bytes.decode()
