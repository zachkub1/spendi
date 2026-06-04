"""
Republic Bank (Trinidad & Tobago) credit card transaction email parser.

Handles the alert format:
  Sender : internetbanking@republictt.com
  Subject: RepublicAlerts  (or similar)
  Body   : "A debit of USD xx.xx has been applied to your Republic Bank Credit Card
            xxxxxxxx****xxxx by MERCHANT on YYYY-MM-DD HH:MM:SS."
"""
import re
from datetime import datetime, timezone
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult


class RepublicTTParser(EmailParser):
    """Parser for Republic Bank (TT) credit card transaction notifications."""

    provider = "republictt"

    SENDER_PATTERN = r"@republictt\.com$"

    SUBJECT_PATTERN = r"RepublicAlerts|Republic Bank Transaction"

    # "A debit of USD 12.34 has been applied ... by MERCHANT on DATE"
    DEBIT_PATTERN = (
        r"A debit of USD\s+([\d,]+\.\d{2})\s+has been applied to your "
        r"Republic Bank Credit Card\s+(\S+)\s+by\s+(.+?)\s+on\s+"
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
    )

    # Card number pattern: xxxxxxxx****xxxx — last 4 digits after the final ****
    CARD_LAST_FOUR_PATTERN = r"\*{4}(\d{4})"

    def can_parse(self, sender: str, subject: str) -> bool:
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject, re.IGNORECASE)
        )

    def parse(self, subject: str, body: str) -> ParseResult:
        try:
            debit_match = re.search(self.DEBIT_PATTERN, body, re.IGNORECASE | re.DOTALL)
            if not debit_match:
                return ParseResult(status="non_transaction", reason="no_debit_pattern_found")

            amount = Decimal(debit_match.group(1).replace(',', ''))
            card_field = debit_match.group(2)  # e.g. "xxxxxxxx****1234"
            merchant_raw = debit_match.group(3).strip()
            date_str = debit_match.group(4).strip()

            # Strip trailing location noise: "SHEIN.COM LOS ANGELES US" → "SHEIN.COM"
            # Keep everything up to the first city/state-like token (all-caps 2+ word suffix)
            merchant = self._clean_merchant(merchant_raw)

            # Parse ISO-style datetime from body
            try:
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                transaction_date = transaction_date.replace(tzinfo=timezone.utc)
            except ValueError:
                transaction_date = datetime.now(timezone.utc)

            # Extract last 4 from masked card number field
            card_match = re.search(self.CARD_LAST_FOUR_PATTERN, card_field)
            card_last_four = card_match.group(1) if card_match else None

            return ParseResult(
                status="transaction",
                data=ParsedTransactionData(
                    merchant_name=merchant,
                    amount=amount,
                    transaction_date=transaction_date,
                    card_last_four=card_last_four,
                    transaction_type="purchase",
                    direction="outgoing",
                    confidence_score=92.0,
                )
            )

        except Exception as e:
            return ParseResult(status="parse_error", reason=f"unexpected_error: {str(e)}")

    @staticmethod
    def _clean_merchant(raw: str) -> str:
        """
        Remove trailing US city/state tokens from merchant string.

        Republic TT emails append location: "SHEIN.COM LOS ANGELES US"
        We keep only the first token if it looks like a domain/brand name,
        otherwise return the full string trimmed.
        """
        # Split on whitespace; if last token is a 2-letter country code, strip location suffix
        tokens = raw.split()
        if len(tokens) > 1 and re.match(r'^[A-Z]{2}$', tokens[-1]):
            # Drop trailing country code and city tokens — keep merchant name (first token)
            return tokens[0]
        return raw
