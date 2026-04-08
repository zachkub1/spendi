"""
Zelle transaction email parser.

Handles three email families:
  1. Native Zelle emails — from @zellepay.com / @notify.zelle.com
     Subject contains amount: "John sent you $50.00" / "You sent $50.00 to John"
  2. Chase-routed Zelle notifications — from @chase.com / @alerts.chase.com
     Subject: "You received money with Zelle®" / "You sent money with Zelle®"
     Body: details table (Amount / Sent on / Transaction number / Memo)
  3. TD Bank Zelle deposits — from @tdbank.com
     Body: "We have successfully deposited the $X payment from NAME (confirmation number N)"
"""
import re
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from .base import EmailParser, ParsedTransactionData, ParseResult

logger = logging.getLogger(__name__)

# Full month names for written-date parsing ("March 28, 2026")
_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_RE = "|".join(_MONTH_NAMES)


class ZelleParser(EmailParser):
    """Parser for Zelle payment notifications (native, Chase-routed, and TD Bank)."""

    provider = "zelle"

    # Accept native Zelle senders, Chase (routes Zelle from chase.com), and TD Bank.
    # Prevention rule: use subdomain-tolerant patterns for large senders.
    SENDER_PATTERN = (
        r"@zellepay\.com$|@notify\.zelle\.com$"
        r"|@(?:[\w-]+\.)?chase\.com$"
        r"|@(?:[\w-]+\.)?tdbank\.com$"
    )

    # Subject patterns — checked as a list so multiple formats are supported.
    # Native: amount in subject. Chase: descriptive. TD Bank: Zelle or payment keywords.
    SUBJECT_PATTERNS = [
        r"sent you",                       # native: "John sent you $50.00"
        r"You sent",                       # native: "You sent $50.00 to John"
        r"received money with Zelle",      # Chase/TD Bank incoming
        r"sent money with Zelle",          # Chase outgoing
        r"Zelle",                          # TD Bank (any Zelle-related subject)
        r"deposited.+payment",             # TD Bank fallback
        r"received.+payment",              # TD Bank fallback
    ]

    # Amount — optional cents (some emails omit .00)
    _AMOUNT_RE = re.compile(r"\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")
    # Chase body table: "Amount\t$50.00" or "Amount  $50"
    _LABELED_AMOUNT_RE = re.compile(
        r"Amount[\s\t]+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
        re.IGNORECASE,
    )
    # TD Bank body: "deposited the $50.00 payment"
    _TD_DEPOSITED_AMOUNT_RE = re.compile(
        r"deposited the \$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+payment",
        re.IGNORECASE,
    )

    # Native Zelle person-name patterns
    _PERSON_SENT_RE = re.compile(r"(.+?)\s+sent you", re.IGNORECASE)
    _PERSON_RECEIVED_RE = re.compile(r"You sent .+? to (.+)", re.IGNORECASE)

    # Chase body: "FirstName sent you money" on its own line
    _CHASE_SENDER_RE = re.compile(r"^(.+?)\s+sent you money", re.IGNORECASE | re.MULTILINE)

    # TD Bank body: "payment from NAME (confirmation number N)"
    _TD_SENDER_RE = re.compile(
        r"payment from (.+?) \(confirmation number",
        re.IGNORECASE,
    )
    _TD_CONFIRMATION_RE = re.compile(
        r"confirmation number\s+(\w+)",
        re.IGNORECASE,
    )
    # Chase body: "Transaction number\t1234567890"
    _CHASE_TRANSACTION_ID_RE = re.compile(
        r"Transaction number[\s\t]+(\w+)",
        re.IGNORECASE,
    )
    _TD_ACCOUNT_RE = re.compile(
        r"\*+(\d{3,4})\)",
        re.IGNORECASE,
    )

    # Date: "Sent on\tMarch 28, 2026 at 12:20:28 AM EDT" or bare "March 28, 2026"
    _LABELED_DATE_RE = re.compile(
        rf"Sent on[\s\t]+({_MONTH_RE})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        re.IGNORECASE,
    )
    _WRITTEN_DATE_RE = re.compile(
        rf"({_MONTH_RE})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        re.IGNORECASE,
    )

    # ── Public interface ───────────────────────────────────────────────────────

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is a Zelle notification (native, Chase-routed, or TD Bank)."""
        if not re.search(self.SENDER_PATTERN, sender, re.IGNORECASE):
            return False
        for pattern in self.SUBJECT_PATTERNS:
            if re.search(pattern, subject, re.IGNORECASE):
                return True
        return False

    def parse(self, subject: str, body: str) -> ParseResult:
        """Extract transaction data from Zelle email."""
        try:
            if self._is_td_bank_zelle(body):
                return self._parse_td_bank_zelle(subject, body)
            if self._is_chase_zelle(subject):
                return self._parse_chase_zelle(subject, body)
            return self._parse_native_zelle(subject, body)
        except Exception as e:
            return ParseResult(status="parse_error", reason=f"unexpected_error: {str(e)}")

    # ── Dispatchers ────────────────────────────────────────────────────────────

    def _is_chase_zelle(self, subject: str) -> bool:
        """True for Chase-routed Zelle emails (descriptive subject, no amount)."""
        return bool(re.search(r"with Zelle", subject, re.IGNORECASE))

    def _is_td_bank_zelle(self, body: str) -> bool:
        """True for TD Bank Zelle deposit notifications (detected via body)."""
        return bool(
            re.search(r"successfully deposited", body, re.IGNORECASE)
            or re.search(r"Send Money with Zelle", body, re.IGNORECASE)
        )

    # ── Parsers ────────────────────────────────────────────────────────────────

    def _parse_td_bank_zelle(self, subject: str, body: str) -> ParseResult:
        """
        Parse TD Bank Zelle deposit notification.

        Body format:
            We have successfully deposited the $50.00 payment from John Doe
            (confirmation number 1234567890) into your account
            (TD Bank, TD COMPLETE CHECKING, ******1234).
        """
        text = f"{subject}\n{body}"

        # Amount — prefer labeled "deposited the $X", fall back to any $ in full text
        amount_match = self._TD_DEPOSITED_AMOUNT_RE.search(body)
        if not amount_match:
            amount_match = self._AMOUNT_RE.search(text)
        if not amount_match:
            logger.warning("[ZELLE] TD Bank email: no amount found in body")
            return ParseResult(status="parse_error", reason="td_bank_zelle_no_amount_found")
        amount = Decimal(amount_match.group(1).replace(",", ""))

        # Sender name from "payment from NAME (confirmation number"
        sender_match = self._TD_SENDER_RE.search(body)
        merchant_name = sender_match.group(1).strip() if sender_match else "Zelle"

        # Account last digits (stored as card_last_four for audit trail)
        acct_match = self._TD_ACCOUNT_RE.search(body)
        card_last_four = acct_match.group(1) if acct_match else None

        # Date — try written date in body, fall back to current time
        transaction_date = self._extract_written_date(body) or datetime.now(timezone.utc)

        # Confirmation number as transaction ID
        p2p_transaction_id: Optional[str] = None
        conf_match = self._TD_CONFIRMATION_RE.search(body)
        if conf_match:
            p2p_transaction_id = conf_match.group(1)

        logger.info(
            "[ZELLE] TD Bank Zelle parsed: merchant=%r amount=%s account=****%s txid=%s",
            merchant_name, amount, card_last_four or "??", p2p_transaction_id or "n/a",
        )

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant_name,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=card_last_four,
                transaction_type="transfer",  # Incoming deposit = transfer received
                confidence_score=92.0,
                p2p_source="zelle",
                p2p_transaction_id=p2p_transaction_id,
            ),
        )

    def _parse_chase_zelle(self, subject: str, body: str) -> ParseResult:
        """
        Parse Chase-format Zelle notification.

        Body format:
            XXXX sent you money

            Here are the details:
            Amount\t$50.00
            Sent on\tMarch 28, 2026 at 12:20:28 AM EDT
            Transaction number\t1234567890
            Memo\t(optional)
        """
        text = f"{subject}\n{body}"

        # Direction determines transaction_type
        is_received = bool(re.search(r"received money|sent you", subject, re.IGNORECASE))
        transaction_type = "transfer" if is_received else "payment"

        # Amount — prefer labeled row in body, fall back to first $ in full text
        amount_match = self._LABELED_AMOUNT_RE.search(body)
        if not amount_match:
            amount_match = self._AMOUNT_RE.search(text)
        if not amount_match:
            logger.warning("[ZELLE] Chase Zelle email: no amount found in body")
            return ParseResult(status="parse_error", reason="chase_zelle_no_amount_found")
        amount = Decimal(amount_match.group(1).replace(",", ""))

        # Sender name from body: "FirstName sent you money"
        sender_match = self._CHASE_SENDER_RE.search(body)
        merchant_name = sender_match.group(1).strip() if sender_match else "Zelle"

        # Date — prefer labeled "Sent on\t...", fall back to any written date
        transaction_date = (
            self._extract_labeled_date(text)
            or self._extract_written_date(text)
            or datetime.now(timezone.utc)
        )

        # Extract Chase transaction number: "Transaction number\t1234567890"
        p2p_transaction_id: Optional[str] = None
        txid_match = self._CHASE_TRANSACTION_ID_RE.search(body)
        if txid_match:
            p2p_transaction_id = txid_match.group(1)

        logger.info(
            "[ZELLE] Chase Zelle parsed: merchant=%r amount=%s date=%s type=%s txid=%s",
            merchant_name, amount, transaction_date.date(), transaction_type, p2p_transaction_id or "n/a",
        )

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant_name,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=None,
                transaction_type=transaction_type,
                confidence_score=92.0,
                p2p_source="zelle",
                p2p_transaction_id=p2p_transaction_id,
            ),
        )

    def _parse_native_zelle(self, subject: str, body: str) -> ParseResult:
        """
        Parse native Zelle email where the amount appears in the subject.
        Examples:
          "John sent you $50.00"
          "You sent $50.00 to John"
        """
        # Amount must be in subject for native format
        amount_match = self._AMOUNT_RE.search(subject)
        if not amount_match:
            return ParseResult(status="non_transaction", reason="no_amount_in_subject")
        amount = Decimal(amount_match.group(1).replace(",", ""))

        if re.search(r"sent you", subject, re.IGNORECASE):
            merchant_match = self._PERSON_SENT_RE.search(subject)
            transaction_type = "transfer"
        else:
            merchant_match = self._PERSON_RECEIVED_RE.search(subject)
            transaction_type = "payment"

        if not merchant_match:
            return ParseResult(status="parse_error", reason="amount_found_but_no_person_name")
        merchant = merchant_match.group(1).strip()

        transaction_date = (
            self._extract_written_date(body)
            or datetime.now(timezone.utc)
        )

        logger.info(
            "[ZELLE] Native Zelle parsed: merchant=%r amount=%s type=%s",
            merchant, amount, transaction_type,
        )

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=transaction_date,
                card_last_four=None,
                transaction_type=transaction_type,
                confidence_score=90.0,
                p2p_source="zelle",
            ),
        )

    # ── Date helpers ───────────────────────────────────────────────────────────

    def _extract_labeled_date(self, text: str) -> datetime | None:
        """Parse 'Sent on\tMarch 28, 2026 ...' labeled date."""
        m = self._LABELED_DATE_RE.search(text)
        if m:
            try:
                return datetime.strptime(
                    f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y"
                )
            except ValueError:
                pass
        return None

    def _extract_written_date(self, text: str) -> datetime | None:
        """Parse any written date like 'March 28, 2026'."""
        m = self._WRITTEN_DATE_RE.search(text)
        if m:
            try:
                return datetime.strptime(
                    f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y"
                )
            except ValueError:
                pass
        return None
