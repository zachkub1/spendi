"""
Discover credit card transaction email parser.
"""
import re
from datetime import datetime
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult


class DiscoverParser(EmailParser):
    """Parser for Discover credit card transaction notifications."""

    provider = "discover"

    # Regex patterns for Discover emails
    SENDER_PATTERN = r"@discover\.com$|@services\.discover\.com$|@discovercard\.com$"

    # Discover uses various subject patterns
    SUBJECT_PATTERNS = [
        r"Transaction Alert",
        r"Purchase Alert",
        r"Your Discover card was used",
        r"\$[\d,]+\.\d{2}",  # Amount in subject
    ]

    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"
    MERCHANT_PATTERN = r"(?:at|merchant:|to)\s+([A-Z][A-Za-z0-9\s\-&',\.]+?)(?:\s+on|\s+for|\s+\$|\.)"
    DATE_PATTERNS = [
        r"on (\d{1,2}/\d{1,2}/\d{4})",
        r"on (\d{1,2}/\d{1,2}/\d{2})",
        r"(\d{1,2}/\d{1,2}/\d{4})",
        r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})",
    ]
    CARD_PATTERN = r"ending in (\d{4})|card (\d{4})|xxxx(\d{4})"

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is from Discover and matches transaction pattern."""
        sender_match = bool(re.search(self.SENDER_PATTERN, sender, re.IGNORECASE))
        if not sender_match:
            return False

        # Check if subject matches any of the known patterns
        for pattern in self.SUBJECT_PATTERNS:
            if re.search(pattern, subject, re.IGNORECASE):
                return True

        return False

    def parse(self, subject: str, body: str) -> ParseResult:
        """Extract transaction data from Discover email."""
        try:
            # Combine subject and body for searching
            text = f"{subject}\n{body}"

            # Extract amount (try subject first, then body)
            amount_match = re.search(self.AMOUNT_PATTERN, subject)
            if not amount_match:
                amount_match = re.search(self.AMOUNT_PATTERN, body)
            if not amount_match:
                return ParseResult(
                    status="non_transaction",
                    reason="no_amount_found"
                )
            amount = Decimal(amount_match.group(1).replace(',', ''))

            # Extract merchant name
            merchant_match = re.search(self.MERCHANT_PATTERN, text, re.IGNORECASE)
            if not merchant_match:
                # Fallback: try to find capitalized words after "at" or before amount
                fallback_pattern = r"(?:at|merchant)\s+([A-Z][A-Za-z0-9\s\-&']+)"
                merchant_match = re.search(fallback_pattern, text)

            if not merchant_match:
                return ParseResult(
                    status="parse_error",
                    reason="amount_found_but_no_merchant"
                )

            merchant = merchant_match.group(1).strip()
            # Clean up common trailing words
            merchant = re.sub(r'\s+(on|for|was|charged)$', '', merchant, flags=re.IGNORECASE)

            # Extract date (try multiple patterns)
            transaction_date = None
            for pattern in self.DATE_PATTERNS:
                date_match = re.search(pattern, text)
                if date_match:
                    date_str = date_match.group(1)
                    # Try to parse the date
                    for fmt in ["%m/%d/%Y", "%m/%d/%y"]:
                        try:
                            transaction_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    if transaction_date:
                        break

            if not transaction_date:
                # Fallback to current date if no date found
                transaction_date = datetime.utcnow()

            # Extract card last 4 digits
            card_match = re.search(self.CARD_PATTERN, text, re.IGNORECASE)
            card_last_four = None
            if card_match:
                # Match could be in any of the 3 groups
                card_last_four = card_match.group(1) or card_match.group(2) or card_match.group(3)

            transaction_data = ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=card_last_four,
                transaction_type="purchase",
                confidence_score=90.0  # Good confidence for Discover
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
