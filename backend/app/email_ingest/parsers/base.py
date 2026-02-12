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
    def parse(self, subject: str, body: str) -> ParsedTransactionData:
        """
        Extract transaction data from email.

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            ParsedTransactionData with extracted information

        Raises:
            ValueError: If parsing fails
        """
        pass

    @classmethod
    def get_version(cls) -> str:
        """Return parser version for tracking."""
        return "1.0.0"
