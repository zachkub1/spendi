from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class User(Base):
    """
    User model - represents authenticated users.
    Users authenticate via Google OAuth (no password storage).
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    oauth_provider = Column(String(50), nullable=False, default="google")  # "google" for MVP
    oauth_subject_id = Column(String(255), unique=True, nullable=False, index=True)  # Google's 'sub' claim
    display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    email_accounts = relationship("EmailAccount", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class EmailAccount(Base):
    """
    EmailAccount model - represents connected email accounts (Gmail).
    OAuth tokens for Gmail API are stored encrypted.
    """
    __tablename__ = "email_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False, default="gmail")  # "gmail" for MVP
    email_address = Column(String(255), nullable=False)

    # Encrypted OAuth tokens (envelope encryption)
    oauth_access_token = Column(Text, nullable=True)  # Encrypted
    oauth_refresh_token = Column(Text, nullable=True)  # Encrypted
    oauth_token_expires_at = Column(DateTime, nullable=True)

    # Encryption metadata
    encryption_key = Column(Text, nullable=True)  # Encrypted DEK
    encryption_iv = Column(Text, nullable=True)  # Initialization vector

    # Sync configuration
    sync_enabled = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(50), nullable=True)  # "success", "error", "in_progress"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="email_accounts")
    raw_emails = relationship("RawEmail", back_populates="email_account")

    def __repr__(self):
        return f"<EmailAccount {self.email_address}>"


class AuditLogAction(str, enum.Enum):
    """Enumeration of audit log action types."""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_DELETE = "user.delete"
    EMAIL_ACCOUNT_CONNECTED = "email_account.connected"
    EMAIL_ACCOUNT_REVOKED = "email_account.revoked"
    EMAIL_ACCOUNT_SYNC_STARTED = "email_account.sync_started"
    EMAIL_ACCOUNT_SYNC_COMPLETED = "email_account.sync_completed"
    EMAIL_ACCOUNT_SYNC_FAILED = "email_account.sync_failed"


class AuditLog(Base):
    """
    AuditLog model - immutable log of security-sensitive events.
    Tracks all authentication and authorization events for compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(SQLEnum(AuditLogAction), nullable=False)
    resource_type = Column(String(100), nullable=True)  # e.g., "EmailAccount", "User"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, nullable=True, default=dict)  # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"

class RawEmail(Base):
    """
    RawEmail - stores minimal metadata for discovered emails.
    Full body not persisted (privacy-first).
    """
    __tablename__ = "raw_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id"), nullable=False)
    message_id = Column(String(255), unique=True, nullable=False)
    subject = Column(String(500), nullable=False)
    sender = Column(String(255), nullable=False)
    received_at = Column(DateTime, nullable=False)
    parsing_status = Column(String(50), nullable=False, default="pending")
    parser_used = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    email_account = relationship("EmailAccount", back_populates="raw_emails")
    parsed_transaction = relationship("ParsedTransaction", uselist=False, back_populates="raw_email")

    def __repr__(self):
        return f"<RawEmail {self.message_id}>"


class ParsedTransaction(Base):
    """
    ParsedTransaction - extracted transaction data from email.
    """
    __tablename__ = "parsed_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_email_id = Column(UUID(as_uuid=True), ForeignKey("raw_emails.id"), nullable=False)
    email_account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id"), nullable=False)

    # Transaction fields
    merchant_name = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    card_last_four = Column(String(4), nullable=True)
    transaction_type = Column(String(50), nullable=False)

    # Parsing metadata
    confidence_score = Column(Numeric(5, 2), nullable=False)
    parser_version = Column(String(50), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    raw_email = relationship("RawEmail", back_populates="parsed_transaction")
    email_account = relationship("EmailAccount")

    def __repr__(self):
        return f"<ParsedTransaction {self.merchant_name} ${self.amount}>"
