"""
Application configuration module.
Loads settings from environment variables with validation.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_NAME: str = "Spendi"
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/spendi"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")  # 24 hours
    )

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", f"{API_BASE_URL}/auth/callback"
    )

    # OAuth Scopes
    GOOGLE_OAUTH_SCOPES: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.readonly",  # Added in Week 2
    ]

    # Encryption Configuration (Week 2)
    ENCRYPTION_MASTER_KEY: str = os.getenv("ENCRYPTION_MASTER_KEY", "")

    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration settings.
        Raises ValueError if critical settings are missing.
        """
        if cls.ENVIRONMENT == "production":
            if cls.JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
                raise ValueError("JWT_SECRET_KEY must be set in production")
            if not cls.GOOGLE_CLIENT_ID:
                raise ValueError("GOOGLE_CLIENT_ID must be set")
            if not cls.GOOGLE_CLIENT_SECRET:
                raise ValueError("GOOGLE_CLIENT_SECRET must be set")
            if not cls.ENCRYPTION_MASTER_KEY or len(cls.ENCRYPTION_MASTER_KEY) != 64:
                raise ValueError(
                    "ENCRYPTION_MASTER_KEY must be set to a 32-byte hex key (64 characters)"
                )


# Global settings instance
settings = Settings()