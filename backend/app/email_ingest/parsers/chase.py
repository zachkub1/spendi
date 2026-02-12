"""
Chase credit card transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData


class ChaseParser(EmailParser):
    """Parser for Chase credit card transaction notifications."""

    provider = "chase"

    # Regex patterns for Chase emails
    SENDER_PATTERN = r"@chase\.com$|@alerts\.chase\.com$"
    SUBJECT_PATTERN = r"Your \$[\d,]+\.\d{2} transaction"
    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"
    MERCHANT_PATTERN = r"transaction at (.+?) on"
    DATE_PATTERN = r"on (\d{2}/\d{2}/\d{4})"
    CARD_PATTERN = r"ending in (\d{4})"

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is from Chase and matches transaction pattern."""
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject)
        )

    def parse(self, subject: str, body: str) -> ParsedTransactionData:
        """Extract transaction data from Chase email."""
        # Extract amount from subject
        amount_match = re.search(self.AMOUNT_PATTERN, subject)
        if not amount_match:
            raise ValueError("Could not extract amount from subject")
        amount = Decimal(amount_match.group(1).replace(',', ''))

        # Extract merchant from body
        merchant_match = re.search(self.MERCHANT_PATTERN, body)
        if not merchant_match:
            raise ValueError("Could not extract merchant name")
        merchant = merchant_match.group(1).strip()

        # Extract date
        date_match = re.search(self.DATE_PATTERN, body)
        if not date_match:
            raise ValueError("Could not extract transaction date")
        transaction_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")

        # Extract card last 4 digits (optional)
        card_match = re.search(self.CARD_PATTERN, body)
        card_last_four = card_match.group(1) if card_match else None

        return ParsedTransactionData(
            merchant_name=merchant,
            amount=amount,
            transaction_date=transaction_date,
            card_last_four=card_last_four,
            transaction_type="purchase",
            confidence_score=95.0  # High confidence for Chase
        )
