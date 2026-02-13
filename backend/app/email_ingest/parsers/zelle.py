"""
Zelle transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult


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

    def parse(self, subject: str, body: str) -> ParseResult:
        """Extract transaction data from Zelle email."""
        try:
            # Extract amount from subject
            amount_match = re.search(self.AMOUNT_PATTERN, subject)
            if not amount_match:
                return ParseResult(
                    status="non_transaction",
                    reason="no_amount_in_subject"
                )
            amount = Decimal(amount_match.group(1).replace(',', ''))

            # Determine if received or sent
            if "sent you" in subject.lower():
                merchant_match = re.search(self.PERSON_SENT_PATTERN, subject)
                transaction_type = "transfer"
            else:
                merchant_match = re.search(self.PERSON_RECEIVED_PATTERN, subject)
                transaction_type = "payment"

            if not merchant_match:
                return ParseResult(
                    status="parse_error",
                    reason="amount_found_but_no_person_name"
                )
            merchant = merchant_match.group(1).strip()

            transaction_date = datetime.utcnow()

            transaction_data = ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=None,
                transaction_type=transaction_type,
                confidence_score=90.0
            )

            return ParseResult(
                status="transaction",
                data=transaction_data
            )

        except Exception as e:
            return ParseResult(
                status="parse_error",
                reason=f"unexpected_error: {str(e)}"
            )
