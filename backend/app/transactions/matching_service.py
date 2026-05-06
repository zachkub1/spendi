"""
Payment instrument matching service.
Matches parsed transactions to user's payment instruments (cards, P2P accounts).
"""
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
import logging

from app.db.models import (
    ParsedTransaction,
    PaymentInstrument,
    NormalizedTransaction,
    PaymentInstrumentType,
    PaymentInstrumentStatus,
    ReimbursementStatus
)
from app.transactions.merchant_normalization import normalize_merchant_name
from app.transactions.categorization import infer_category

logger = logging.getLogger(__name__)


class PaymentInstrumentMatchingService:
    """Service for matching parsed transactions to payment instruments."""

    @staticmethod
    def match_and_normalize(
        db: Session,
        parsed_transaction: ParsedTransaction,
        user_id: str
    ) -> NormalizedTransaction:
        """
        Match a parsed transaction to a payment instrument and create a normalized transaction.

        Always creates a NormalizedTransaction. If no matching instrument is found,
        payment_instrument_id is left NULL so the transaction still appears in the UI
        (shown as "Unlinked"). Users can later associate it with a card.

        Args:
            db: Database session
            parsed_transaction: The parsed transaction to normalize
            user_id: User ID for scoping payment instruments

        Returns:
            NormalizedTransaction (payment_instrument_id may be None if no match)
        """
        payment_instrument = PaymentInstrumentMatchingService._find_matching_instrument(
            db=db,
            parsed_transaction=parsed_transaction,
            user_id=user_id
        )

        if payment_instrument:
            logger.info(
                f"[MATCH] Linked to {payment_instrument.display_name} "
                f"(last4={payment_instrument.last_four_digits!r} "
                f"acct={payment_instrument.account_identifier!r})"
            )
        else:
            logger.warning(
                f"[MATCH] No instrument for: {parsed_transaction.merchant_name!r} "
                f"last4={parsed_transaction.card_last_four!r} "
                f"p2p={parsed_transaction.p2p_source!r} "
                f"type={parsed_transaction.transaction_type!r} — "
                f"creating unlinked NormalizedTransaction"
            )

        # Normalize merchant name
        merchant_normalized = normalize_merchant_name(parsed_transaction.merchant_name)

        # Infer category
        category, confidence = infer_category(
            merchant_name=merchant_normalized,
            transaction_type=parsed_transaction.transaction_type
        )

        # Calculate net amount based on direction.
        # Incoming P2P (someone sent you money) starts at 0 — it only reduces
        # a target expense's net_amount when explicitly matched as a reimbursement.
        # Outgoing purchases/payments start positive (they ARE the spending).
        direction = getattr(parsed_transaction, 'direction', 'outgoing')
        net_amount = (
            Decimal("0.00") if direction == "incoming" else parsed_transaction.amount
        )

        # For P2P transactions, use merchant_name as the initial sender_name
        sender_name = (
            parsed_transaction.merchant_name
            if parsed_transaction.p2p_source
            else None
        )

        # Create normalized transaction (payment_instrument_id=None for unlinked)
        normalized_txn = NormalizedTransaction(
            parsed_transaction_id=parsed_transaction.id,
            payment_instrument_id=payment_instrument.id if payment_instrument else None,
            user_id=user_id,
            merchant_normalized=merchant_normalized,
            amount=parsed_transaction.amount,
            currency=parsed_transaction.currency,
            transaction_date=parsed_transaction.transaction_date,
            transaction_type=parsed_transaction.transaction_type,
            category=category,
            category_confidence=Decimal(str(confidence)),
            category_source="auto_rules",
            reimbursement_status=ReimbursementStatus.NONE,
            reimbursed_amount=Decimal("0.00"),
            net_amount=net_amount,
            direction=direction,
            version="1.0",
            sender_name=sender_name,
            p2p_transaction_id=parsed_transaction.p2p_transaction_id,
            p2p_source=parsed_transaction.p2p_source,
        )

        db.add(normalized_txn)
        db.flush()

        linked = payment_instrument.display_name if payment_instrument else "unlinked"
        logger.info(
            f"[NORMALIZE] {linked}: "
            f"{normalized_txn.merchant_normalized} ${normalized_txn.amount} "
            f"date={normalized_txn.transaction_date.date()} "
            f"category={normalized_txn.category}"
        )

        return normalized_txn

    @staticmethod
    def _find_matching_instrument(
        db: Session,
        parsed_transaction: ParsedTransaction,
        user_id: str
    ) -> Optional[PaymentInstrument]:
        """
        Find payment instrument matching the parsed transaction.

        Matching strategy:
        1. For credit/debit cards: Match by last 4 digits
        2. For P2P (Venmo, Zelle): Match by account identifier from merchant name

        Args:
            db: Database session
            parsed_transaction: Parsed transaction to match
            user_id: User ID for scoping

        Returns:
            Matching PaymentInstrument or None
        """
        # Strategy 1: Match by card last 4 digits
        if parsed_transaction.card_last_four:
            instrument = db.query(PaymentInstrument).filter(
                PaymentInstrument.user_id == user_id,
                PaymentInstrument.last_four_digits == parsed_transaction.card_last_four,
                PaymentInstrument.type.in_([
                    PaymentInstrumentType.CREDIT_CARD,
                    PaymentInstrumentType.DEBIT_CARD
                ]),
                PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE
            ).first()

            if instrument:
                return instrument

        # Strategy 2: P2P accounts — only when the transaction is explicitly a P2P source
        # (Venmo/Zelle) or an incoming transfer. Bill payments from card issuers
        # (Discover, Amex) also use type="payment" but must NOT be routed here.
        is_p2p = (
            parsed_transaction.p2p_source is not None
            or parsed_transaction.transaction_type == "transfer"
        )
        if is_p2p:
            instrument = db.query(PaymentInstrument).filter(
                PaymentInstrument.user_id == user_id,
                PaymentInstrument.type == PaymentInstrumentType.P2P_ACCOUNT,
                PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE
            ).first()
            if instrument:
                return instrument

        # Strategy 3: Bill payments (type="payment", no card_last_four) — match to
        # any active credit/debit card as a best-effort fallback so payments are
        # not silently dropped when the card number isn't present in the email.
        if parsed_transaction.transaction_type == "payment":
            instrument = db.query(PaymentInstrument).filter(
                PaymentInstrument.user_id == user_id,
                PaymentInstrument.type.in_([
                    PaymentInstrumentType.CREDIT_CARD,
                    PaymentInstrumentType.DEBIT_CARD,
                ]),
                PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE
            ).first()
            if instrument:
                return instrument

        return None