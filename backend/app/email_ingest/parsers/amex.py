"""
American Express transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult


class AmexParser(EmailParser):
    """Parser for American Express transaction notifications."""

    provider = "amex"

    SENDER_PATTERN = r"@(?:[\w-]+\.)?americanexpress\.com$|@aexp\.com$"
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

    def parse(self, subject: str, body: str) -> ParseResult:
        """Extract transaction data from Amex email."""
        try:
            # Extract amount from subject
            amount_match = re.search(self.AMOUNT_PATTERN, subject)
            if not amount_match:
                return ParseResult(
                    status="non_transaction",
                    reason="no_amount_in_subject"
                )
            amount = Decimal(amount_match.group(1).replace(',', ''))

            # Extract merchant from body
            merchant_match = re.search(self.MERCHANT_PATTERN, body)
            if not merchant_match:
                return ParseResult(
                    status="parse_error",
                    reason="amount_found_but_no_merchant"
                )
            merchant = merchant_match.group(1).strip()

            # Extract date
            date_match = re.search(self.DATE_PATTERN, body)
            if not date_match:
                return ParseResult(
                    status="parse_error",
                    reason="amount_found_but_no_date"
                )
            transaction_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")

            # Extract card last 4 digits (optional)
            card_match = re.search(self.CARD_PATTERN, body)
            card_last_four = card_match.group(1) if card_match else None

            transaction_data = ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=card_last_four,
                transaction_type="purchase",
                confidence_score=95.0
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
