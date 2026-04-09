"""
Venmo transaction email parser.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from .base import EmailParser, ParsedTransactionData, ParseResult


class VenmoParser(EmailParser):
    """Parser for Venmo payment notifications."""

    provider = "venmo"

    SENDER_PATTERN = r"@venmo\.com$"
    SUBJECT_PATTERN = r"You paid|You received"
    AMOUNT_PATTERN = r"\$(\d{1,3}(?:,\d{3})*\.\d{2})"
    PERSON_PAID_PATTERN = r"You paid ([^\$]+) \$"
    PERSON_RECEIVED_PATTERN = r"([^\$]+) paid you \$"
    # Venmo handle in body: "@username"
    VENMO_HANDLE_PATTERN = r"@([\w]+)"
    # Venmo transaction ID sometimes appears in footer links
    VENMO_TX_ID_PATTERN = r"payment[_\-/](\w{8,})"

    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if email is from Venmo."""
        return bool(
            re.search(self.SENDER_PATTERN, sender, re.IGNORECASE) and
            re.search(self.SUBJECT_PATTERN, subject)
        )

    def parse(self, subject: str, body: str) -> ParseResult:
        """Extract transaction data from Venmo email."""
        try:
            # Extract amount from subject
            amount_match = re.search(self.AMOUNT_PATTERN, subject)
            if not amount_match:
                return ParseResult(
                    status="non_transaction",
                    reason="no_amount_in_subject"
                )
            amount = Decimal(amount_match.group(1).replace(',', ''))

            # Determine if payment or receipt
            if "You paid" in subject:
                merchant_match = re.search(self.PERSON_PAID_PATTERN, subject)
                transaction_type = "payment"
            else:
                merchant_match = re.search(self.PERSON_RECEIVED_PATTERN, subject)
                transaction_type = "transfer"

            if not merchant_match:
                return ParseResult(
                    status="parse_error",
                    reason="amount_found_but_no_person_name"
                )
            merchant = merchant_match.group(1).strip()

            # Try to enrich merchant name with Venmo handle from body (@username)
            handle_match = re.search(self.VENMO_HANDLE_PATTERN, body)
            if handle_match:
                merchant = f"{merchant} (@{handle_match.group(1)})"

            # Try to extract transaction ID from body links
            p2p_transaction_id: Optional[str] = None
            txid_match = re.search(self.VENMO_TX_ID_PATTERN, body, re.IGNORECASE)
            if txid_match:
                p2p_transaction_id = txid_match.group(1)

            # Venmo emails typically don't include the exact date in parseable format
            # Use current date as approximation
            transaction_date = datetime.now(timezone.utc)

            return ParseResult(
                status="transaction",
                data=ParsedTransactionData(
                    merchant_name=merchant,
                    amount=amount,
                    transaction_date=transaction_date,
                    card_last_four=None,
                    transaction_type=transaction_type,
                    confidence_score=90.0,  # Slightly lower due to date approximation
                    p2p_source="venmo",
                    p2p_transaction_id=p2p_transaction_id,
                )
            )

        except Exception as e:
            return ParseResult(
                status="parse_error",
                reason=f"unexpected_error: {str(e)}"
            )
