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
    ) -> Optional[NormalizedTransaction]:
        """
        Match a parsed transaction to a payment instrument and create normalized transaction.

        Args:
            db: Database session
            parsed_transaction: The parsed transaction to match
            user_id: User ID for scoping payment instruments

        Returns:
            NormalizedTransaction if successful, None if no matching instrument found
        """
        # Find matching payment instrument
        payment_instrument = PaymentInstrumentMatchingService._find_matching_instrument(
            db=db,
            parsed_transaction=parsed_transaction,
            user_id=user_id
        )

        if not payment_instrument:
            logger.warning(
                f"[MATCH] No payment instrument found for transaction: "
                f"{parsed_transaction.merchant_name} ({parsed_transaction.card_last_four or 'P2P'})"
            )
            return None

        logger.info(
            f"[MATCH] Matched transaction to {payment_instrument.display_name} "
            f"({payment_instrument.last_four_digits or payment_instrument.account_identifier})"
        )

        # Normalize merchant name
        merchant_normalized = normalize_merchant_name(parsed_transaction.merchant_name)

        # Infer category
        category, confidence = infer_category(
            merchant_name=merchant_normalized,
            transaction_type=parsed_transaction.transaction_type
        )

        # Calculate net amount (initially same as amount, before reimbursements)
        net_amount = parsed_transaction.amount

        # Create normalized transaction
        normalized_txn = NormalizedTransaction(
            parsed_transaction_id=parsed_transaction.id,
            payment_instrument_id=payment_instrument.id,
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
            version="1.0"
        )

        db.add(normalized_txn)
        db.flush()

        logger.info(
            f"[NORMALIZE] Created normalized transaction: "
            f"{normalized_txn.merchant_normalized} ${normalized_txn.amount} ({normalized_txn.category})"
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

        # Strategy 2: Match P2P accounts by transaction type
        # For Venmo/Zelle, we'll need to extract recipient/sender from merchant name
        if parsed_transaction.transaction_type in ["transfer", "payment"]:
            # Try to find P2P instrument
            # For MVP, we'll match any active P2P account
            # Future: Extract account identifier from merchant name and match specifically
            instrument = db.query(PaymentInstrument).filter(
                PaymentInstrument.user_id == user_id,
                PaymentInstrument.type == PaymentInstrumentType.P2P_ACCOUNT,
                PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE
            ).first()

            if instrument:
                return instrument

        return None