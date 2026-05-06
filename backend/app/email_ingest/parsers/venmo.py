"""
Venmo transaction email parser.

Handles three email families:
  1. "You paid X $Y"         → outgoing payment
  2. "X paid you $Y"         → incoming transfer
  3. "Transfer to your bank" → bank cashout (transfer)
"""
import re
from decimal import Decimal
from typing import Optional
from .base import EmailParser, ParsedTransactionData, ParseResult


class VenmoParser(EmailParser):
    """Parser for Venmo payment notifications."""

    provider = "venmo"

    SENDER_PATTERN = r"@venmo\.com$"
    # Match any of the three families
    SUBJECT_PATTERN = r"You paid|paid you|Transfer to your bank"

    _AMOUNT_RE = re.compile(r"\$(\d{1,3}(?:,\d{3})*\.\d{2})")
    _PERSON_PAID_RE = re.compile(r"You paid (.+?) \$")     # "You paid John $"
    _PERSON_RECV_RE = re.compile(r"^(.+?) paid you \$")   # "John paid you $"
    _VENMO_HANDLE_RE = re.compile(r"@([\w]+)")
    _VENMO_TX_ID_RE = re.compile(r"payment[_\-/](\w{8,})")

    def can_parse(self, sender: str, subject: str) -> bool:
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE)
            and re.search(self.SUBJECT_PATTERN, subject, re.IGNORECASE)
        )

    def parse(self, subject: str, body: str) -> ParseResult:
        try:
            # ── Bank transfer out (cashout) ────────────────────────────────
            if re.search(r"Transfer to your bank", subject, re.IGNORECASE):
                return self._parse_cashout(subject, body)

            # ── Outgoing payment: "You paid X $Y" ─────────────────────────
            if re.search(r"You paid", subject, re.IGNORECASE):
                return self._parse_outgoing(subject, body)

            # ── Incoming receipt: "X paid you $Y" ─────────────────────────
            if re.search(r"paid you", subject, re.IGNORECASE):
                return self._parse_incoming(subject, body)

            return ParseResult(status="non_transaction", reason="unrecognized_venmo_subject")

        except Exception as e:
            return ParseResult(status="parse_error", reason=f"unexpected_error: {str(e)}")

    # ── Individual parsers ─────────────────────────────────────────────────────

    def _parse_outgoing(self, subject: str, body: str) -> ParseResult:
        amount = self._extract_amount(subject)
        if amount is None:
            return ParseResult(status="non_transaction", reason="no_amount_in_subject")

        merchant_match = self._PERSON_PAID_RE.search(subject)
        if not merchant_match:
            return ParseResult(status="parse_error", reason="amount_found_but_no_person_name")
        merchant = self._enrich_with_handle(merchant_match.group(1).strip(), body)

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=None,  # sync.py falls back to received_at
                card_last_four=None,
                transaction_type="payment",
                confidence_score=92.0,
                direction="outgoing",
                p2p_source="venmo",
                p2p_transaction_id=self._extract_tx_id(body),
            ),
        )

    def _parse_incoming(self, subject: str, body: str) -> ParseResult:
        amount = self._extract_amount(subject)
        if amount is None:
            return ParseResult(status="non_transaction", reason="no_amount_in_subject")

        merchant_match = self._PERSON_RECV_RE.search(subject)
        if not merchant_match:
            return ParseResult(status="parse_error", reason="amount_found_but_no_person_name")
        merchant = self._enrich_with_handle(merchant_match.group(1).strip(), body)

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name=merchant,
                amount=amount,
                transaction_date=None,
                card_last_four=None,
                transaction_type="transfer",
                confidence_score=92.0,
                direction="incoming",
                p2p_source="venmo",
                p2p_transaction_id=self._extract_tx_id(body),
            ),
        )

    def _parse_cashout(self, subject: str, body: str) -> ParseResult:
        # Amount may be in subject or body
        amount = self._extract_amount(subject) or self._extract_amount(body)
        if amount is None:
            return ParseResult(status="parse_error", reason="no_amount_found_in_cashout")

        return ParseResult(
            status="transaction",
            data=ParsedTransactionData(
                merchant_name="Venmo Bank Transfer",
                amount=amount,
                transaction_date=None,
                card_last_four=None,
                transaction_type="transfer",
                confidence_score=88.0,
                direction="transfer",
                p2p_source="venmo",
                p2p_transaction_id=self._extract_tx_id(body),
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_amount(self, text: str) -> Optional[Decimal]:
        m = self._AMOUNT_RE.search(text)
        return Decimal(m.group(1).replace(",", "")) if m else None

    def _extract_tx_id(self, body: str) -> Optional[str]:
        m = self._VENMO_TX_ID_RE.search(body, re.IGNORECASE)
        return m.group(1) if m else None

    def _enrich_with_handle(self, name: str, body: str) -> str:
        """Append Venmo handle from body if present."""
        m = self._VENMO_HANDLE_RE.search(body)
        if m:
            return f"{name} (@{m.group(1)})"
        return name
