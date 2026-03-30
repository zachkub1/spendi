"""
Discover credit card transaction and payment email parser.

Handles two email families:
  1. Purchase alerts  — "Transaction Alert", "Purchase Alert", "$X.XX" in subject
  2. Payment notices  — "Your Scheduled Payment", "Payment Confirmation", etc.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal
from .base import EmailParser, ParsedTransactionData, ParseResult

# Full month names for written-date parsing ("March 30, 2026")
_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_RE = "|".join(_MONTH_NAMES)


class DiscoverParser(EmailParser):
    """Parser for Discover credit card transaction and payment notifications."""

    provider = "discover"

    SENDER_PATTERN = r"@discover\.com$|@services\.discover\.com$|@discovercard\.com$"

    # Subject patterns — purchase alerts first, payment notices second.
    SUBJECT_PATTERNS = [
        r"Transaction Alert",
        r"Purchase Alert",
        r"Your Discover card was used",
        r"\$[\d,]+\.\d{2}",            # amount anywhere in subject
        # payment notices
        r"Your Scheduled Payment",
        r"Payment Confirmation",
        r"Payment Posted",
        r"Payment Received",
        r"Payment Processed",
        r"Scheduled Payment",
    ]

    # Patterns that identify a payment (vs purchase) email
    _PAYMENT_SUBJECT_RE = re.compile(
        r"scheduled\s+payment|payment\s+confirmation|payment\s+posted|"
        r"payment\s+received|payment\s+processed",
        re.IGNORECASE,
    )
    _PAYMENT_BODY_RE = re.compile(
        r"payment\s+post\s+date|bank\s+account\s+ending|confirmation\s+#|"
        r"payment\s+info",
        re.IGNORECASE,
    )

    # Amount patterns
    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"
    _LABELED_AMOUNT_RE = re.compile(
        r"(?:amount|payment\s+amount)[:\s]+\$(\d{1,3}(?:,\d{3})*\.\d{2})",
        re.IGNORECASE,
    )

    # Merchant (purchase emails)
    MERCHANT_PATTERN = r"(?:at|merchant:|to)\s+([A-Z][A-Za-z0-9\s\-&',\.]+?)(?:\s+on|\s+for|\s+\$|\.)"

    # Date: "Payment Post Date: March 30, 2026" or "March 30, 2026" standalone
    _PAYMENT_DATE_RE = re.compile(
        rf"(?:payment\s+post\s+date|post\s+date|date)[:\s]+({_MONTH_RE})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        re.IGNORECASE,
    )
    _WRITTEN_DATE_RE = re.compile(
        rf"({_MONTH_RE})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        re.IGNORECASE,
    )
    _NUMERIC_DATE_PATTERNS = [
        re.compile(r"on (\d{1,2}/\d{1,2}/\d{4})"),
        re.compile(r"on (\d{1,2}/\d{1,2}/\d{2})"),
        re.compile(r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})"),
        re.compile(r"(\d{1,2}/\d{1,2}/\d{4})"),
    ]

    # Card / account
    CARD_PATTERN = r"ending in (\d{4})|card (\d{4})|xxxx(\d{4})"
    _BANK_ACCOUNT_RE = re.compile(r"bank\s+account\s+ending\s+in\s+(\d{4})", re.IGNORECASE)

    # ─────────────────────────────────────────────────────────────────────────

    def can_parse(self, sender: str, subject: str) -> bool:
        if not re.search(self.SENDER_PATTERN, sender, re.IGNORECASE):
            return False
        for pattern in self.SUBJECT_PATTERNS:
            if re.search(pattern, subject, re.IGNORECASE):
                return True
        return False

    def parse(self, subject: str, body: str) -> ParseResult:
        try:
            text = f"{subject}\n{body}"
            if self._is_payment_email(subject, body):
                return self._parse_payment(text)
            return self._parse_purchase(text)
        except Exception as e:
            return ParseResult(status="parse_error", reason=f"unexpected_error: {e}")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _is_payment_email(self, subject: str, body: str) -> bool:
        return bool(
            self._PAYMENT_SUBJECT_RE.search(subject)
            or self._PAYMENT_BODY_RE.search(body)
        )

    def _parse_payment(self, text: str) -> ParseResult:
        """Parse a Discover bill-payment notification."""
        # Amount — prefer labeled "Amount: $X.XX", fall back to any $X.XX
        amount_match = self._LABELED_AMOUNT_RE.search(text)
        if not amount_match:
            amount_match = re.search(self.AMOUNT_PATTERN, text)
        if not amount_match:
            return ParseResult(status="non_transaction", reason="no_amount_in_payment_email")

        amount = Decimal(amount_match.group(1).replace(",", ""))

        # Date — prefer labeled "Payment Post Date: …" then any date
        transaction_date = self._extract_labeled_payment_date(text) or self._extract_any_date(text)

        # Bank account last 4 (stored as card_last_four for record-keeping)
        acct_match = self._BANK_ACCOUNT_RE.search(text)
        card_last_four = acct_match.group(1) if acct_match else None

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name="Discover Payment",
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=card_last_four,
                transaction_type="payment",
                confidence_score=85.0,
            ),
        )

    def _parse_purchase(self, text: str) -> ParseResult:
        """Parse a Discover purchase alert."""
        # Amount
        amount_match = re.search(self.AMOUNT_PATTERN, text)
        if not amount_match:
            return ParseResult(status="non_transaction", reason="no_amount_found")
        amount = Decimal(amount_match.group(1).replace(",", ""))

        # Merchant
        merchant_match = re.search(self.MERCHANT_PATTERN, text, re.IGNORECASE)
        if not merchant_match:
            merchant_match = re.search(
                r"(?:at|merchant)\s+([A-Z][A-Za-z0-9\s\-&']+)", text
            )
        if not merchant_match:
            return ParseResult(status="parse_error", reason="amount_found_but_no_merchant")

        merchant = re.sub(
            r"\s+(on|for|was|charged)$", "", merchant_match.group(1).strip(), flags=re.IGNORECASE
        )

        # Date
        transaction_date = self._extract_any_date(text)

        # Card last 4
        card_match = re.search(self.CARD_PATTERN, text, re.IGNORECASE)
        card_last_four = None
        if card_match:
            card_last_four = card_match.group(1) or card_match.group(2) or card_match.group(3)

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=card_last_four,
                transaction_type="purchase",
                confidence_score=90.0,
            ),
        )

    def _extract_labeled_payment_date(self, text: str) -> datetime | None:
        """Parse 'Payment Post Date: March 30, 2026' style label."""
        m = self._PAYMENT_DATE_RE.search(text)
        if m:
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y")
            except ValueError:
                pass
        return None

    def _extract_any_date(self, text: str) -> datetime:
        """Try written date ('March 30, 2026'), then numeric, then fallback."""
        m = self._WRITTEN_DATE_RE.search(text)
        if m:
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y")
            except ValueError:
                pass

        for pattern in self._NUMERIC_DATE_PATTERNS:
            date_match = pattern.search(text)
            if date_match:
                date_str = date_match.group(1)
                for fmt in ["%m/%d/%Y", "%m/%d/%y"]:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue

        return datetime.now(timezone.utc)
