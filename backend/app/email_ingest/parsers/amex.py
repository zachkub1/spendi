"""
American Express transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData


class AmexParser(EmailParser):
    """Parser for American Express transaction notifications."""

    provider = "amex"

    SENDER_PATTERN = r"@americanexpress\.com$|@aexp\.com$"
    SUBJECT_PATTERN = r"Charge of \$[\d,]+\.\d{2}"
    AMOUNT_PATTERN = r"Charge of \$(\d{1,3}(?:,\d{3})*\.\d{2})"
    MERCHANT_PATTERN = r"at (.+?) has been approved"
    DATE_PATTERN = r"on (\d{2}/\d{2}/\d{4})"
    CARD_PATTERN = r"ending in (\d{4})"

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is from Amex and matches transaction pattern."""
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject)
        )

    def parse(self, subject: str, body: str) -> ParsedTransactionData:
        """Extract transaction data from Amex email."""
        amount_match = re.search(self.AMOUNT_PATTERN, subject)
        if not amount_match:
            raise ValueError("Could not extract amount")
        amount = Decimal(amount_match.group(1).replace(',', ''))

        merchant_match = re.search(self.MERCHANT_PATTERN, body)
        if not merchant_match:
            raise ValueError("Could not extract merchant")
        merchant = merchant_match.group(1).strip()

        date_match = re.search(self.DATE_PATTERN, body)
        if not date_match:
            raise ValueError("Could not extract date")
        transaction_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")

        card_match = re.search(self.CARD_PATTERN, body)
        card_last_four = card_match.group(1) if card_match else None

        return ParsedTransactionData(
            merchant_name=merchant,
            amount=amount,
            transaction_date=transaction_date,
            card_last_four=card_last_four,
            transaction_type="purchase",
            confidence_score=95.0
        )
