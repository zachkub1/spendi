"""
Base class for email parsers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


@dataclass
class ParsedTransactionData:
    """Data class for parsed transaction information."""
    merchant_name: str
    amount: Decimal
    transaction_date: datetime
    card_last_four: Optional[str]
    transaction_type: str  # purchase, refund, payment, transfer
    confidence_score: float  # 0-100


@dataclass
class ParseResult:
    """
    Result of parsing an email.

    status can be:
    - "transaction": Successfully extracted transaction data
    - "non_transaction": Email is valid but contains no transaction (marketing, alerts, etc.)
    - "parse_error": Email should contain transaction but parsing failed
    """
    status: str  # "transaction", "non_transaction", "parse_error"
    data: Optional[ParsedTransactionData] = None
    reason: Optional[str] = None  # Explanation for non_transaction or parse_error


class EmailParser(ABC):
    """Abstract base class for email parsers."""

    provider: str  # e.g., "chase", "amex", "venmo", "zelle"

    @abstractmethod
    def can_parse(self, sender: str, subject: str) -> bool:
        """
        Determine if this parser can handle the email.

        Args:
            sender: Email sender address
            subject: Email subject line

        Returns:
            True if this parser can parse the email
        """
        pass

    @abstractmethod
    def parse(self, subject: str, body: str) -> ParseResult:
        """
        Extract transaction data from email.

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            ParseResult with status and optional transaction data

        Never raises exceptions - returns ParseResult with status="parse_error" instead
        """
        pass

    @classmethod
    def get_version(cls) -> str:
        """Return parser version for tracking."""
        return "1.0.0"
