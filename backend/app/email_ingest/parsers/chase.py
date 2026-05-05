"""
Chase credit card transaction email parser.

Handles the current Chase alert format:
  Subject : You made a $x.xx transaction with MERCHANT NAME
  Body    : table with Account / Date / Merchant / Amount rows
"""
import re
from datetime import datetime, timezone
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult


class ChaseParser(EmailParser):
    """Parser for Chase credit card transaction notifications."""

    provider = "chase"

    SENDER_PATTERN = r"@chase\.com$|@alerts\.chase\.com$"

    # Matches both current ("You made a $x.xx transaction")
    # and legacy ("Your $x.xx transaction") subject formats.
    SUBJECT_PATTERN = r"You made a \$[\d,]+\.\d{2} transaction|Your \$[\d,]+\.\d{2} transaction"

    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"

    # Body table rows:  "Merchant\t<name>" or "Merchant: <name>"
    MERCHANT_PATTERN = r"Merchant[:\t ]+(.+?)(?:\r?\n|$)"

    # "Date\tApr 9, 2026 at 6:54 PM ET"
    DATE_PATTERN = r"Date[:\t ]+(\w{3}\s+\d{1,2},\s+\d{4})"

    # "Chase Freedom Rise Visa (...3449)" → captures "3449"
    CARD_PATTERN = r"\(\.\.\.(\d{4})\)|ending in (\d{4})"

    def can_parse(self, sender: str, subject: str) -> bool:
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject, re.IGNORECASE)
        )

    def parse(self, subject: str, body: str) -> ParseResult:
        try:
            # Amount from subject
            amount_match = re.search(self.AMOUNT_PATTERN, subject)
            if not amount_match:
                return ParseResult(status="non_transaction", reason="no_amount_in_subject")
            amount = Decimal(amount_match.group(1).replace(',', ''))

            # Merchant from body table
            merchant_match = re.search(self.MERCHANT_PATTERN, body)
            if not merchant_match:
                # Fallback: merchant sometimes appended to subject after "with"
                subject_merchant = re.search(r"transaction with (.+)$", subject, re.IGNORECASE)
                if subject_merchant:
                    merchant = subject_merchant.group(1).strip()
                else:
                    return ParseResult(status="parse_error", reason="no_merchant_found")
            else:
                merchant = merchant_match.group(1).strip()

            # Date from body ("Apr 9, 2026 at ...")
            date_match = re.search(self.DATE_PATTERN, body)
            if date_match:
                try:
                    transaction_date = datetime.strptime(date_match.group(1).strip(), "%b %d, %Y")
                    transaction_date = transaction_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    transaction_date = datetime.now(timezone.utc)
            else:
                transaction_date = datetime.now(timezone.utc)

            # Card last 4 — "(...3449)" or legacy "ending in 3449"
            card_match = re.search(self.CARD_PATTERN, body)
            if card_match:
                card_last_four = card_match.group(1) or card_match.group(2)
            else:
                card_last_four = None

            return ParseResult(
                status="transaction",
                data=ParsedTransactionData(
                    merchant_name=merchant,
                    amount=amount,
                    transaction_date=transaction_date,
                    card_last_four=card_last_four,
                    transaction_type="purchase",
                    confidence_score=95.0,
                )
            )

        except Exception as e:
            return ParseResult(status="parse_error", reason=f"unexpected_error: {str(e)}")
