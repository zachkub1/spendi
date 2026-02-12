"""
Zelle transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData


class ZelleParser(EmailParser):
    """Parser for Zelle payment notifications."""

    provider = "zelle"

    SENDER_PATTERN = r"@zellepay\.com$|@notify\.zelle\.com$"
    SUBJECT_PATTERN = r"sent you|You sent"
    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"
    PERSON_SENT_PATTERN = r"([^\s]+) sent you"
    PERSON_RECEIVED_PATTERN = r"You sent \$[\d,]+\.\d{2} to ([^\s]+)"

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is from Zelle."""
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject, re.IGNORECASE)
        )

    def parse(self, subject: str, body: str) -> ParsedTransactionData:
        """Extract transaction data from Zelle email."""
        amount_match = re.search(self.AMOUNT_PATTERN, subject)
        if not amount_match:
            raise ValueError("Could not extract amount")
        amount = Decimal(amount_match.group(1).replace(',', ''))

        # Determine if received or sent
        if "sent you" in subject.lower():
            merchant_match = re.search(self.PERSON_SENT_PATTERN, subject)
            transaction_type = "transfer"
        else:
            merchant_match = re.search(self.PERSON_RECEIVED_PATTERN, subject)
            transaction_type = "payment"

        if not merchant_match:
            raise ValueError("Could not extract person name")
        merchant = merchant_match.group(1).strip()

        transaction_date = datetime.utcnow()

        return ParsedTransactionData(
            merchant_name=merchant,
            amount=amount,
            transaction_date=transaction_date,
            card_last_four=None,
            transaction_type=transaction_type,
            confidence_score=90.0
        )
