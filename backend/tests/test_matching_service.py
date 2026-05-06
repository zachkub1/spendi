"""
Unit tests for payment instrument matching service.
Tests matching logic for credit/debit cards and P2P accounts.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from app.transactions.matching_service import PaymentInstrumentMatchingService
from app.db.models import (
    PaymentInstrument,
    ParsedTransaction,
    NormalizedTransaction,
    PaymentInstrumentType,
    PaymentInstrumentStatus,
    TransactionCategory,
    ReimbursementStatus
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def user_id():
    """Test user ID."""
    return str(uuid4())


@pytest.fixture
def credit_card_instrument(user_id):
    """Sample credit card payment instrument."""
    return PaymentInstrument(
        id=uuid4(),
        user_id=user_id,
        type=PaymentInstrumentType.CREDIT_CARD,
        issuer="chase",
        display_name="Chase Sapphire Reserve",
        last_four_digits="5678",
        network="visa",
        status=PaymentInstrumentStatus.ACTIVE
    )


@pytest.fixture
def p2p_instrument(user_id):
    """Sample P2P payment instrument."""
    return PaymentInstrument(
        id=uuid4(),
        user_id=user_id,
        type=PaymentInstrumentType.P2P_ACCOUNT,
        issuer="venmo",
        display_name="Venmo (@johndoe)",
        account_identifier="@johndoe",
        status=PaymentInstrumentStatus.ACTIVE
    )


@pytest.fixture
def parsed_transaction_card(user_id):
    """Sample parsed transaction with card last 4."""
    return ParsedTransaction(
        id=uuid4(),
        raw_email_id=uuid4(),
        email_account_id=uuid4(),
        merchant_name="STARBUCKS 12345",
        amount=Decimal("12.50"),
        currency="USD",
        transaction_date=datetime(2026, 2, 10),
        card_last_four="5678",
        transaction_type="purchase"
    )


@pytest.fixture
def parsed_transaction_p2p(user_id):
    """Sample parsed transaction for P2P transfer."""
    return ParsedTransaction(
        id=uuid4(),
        raw_email_id=uuid4(),
        email_account_id=uuid4(),
        merchant_name="VENMO FROM SARAH",
        amount=Decimal("50.00"),
        currency="USD",
        transaction_date=datetime(2026, 2, 10),
        card_last_four=None,
        transaction_type="transfer"
    )


class TestPaymentInstrumentMatching:
    """Test suite for payment instrument matching."""

    def test_match_credit_card_by_last_four(self, mock_db, user_id, credit_card_instrument, parsed_transaction_card):
        """Test matching credit card by last 4 digits."""
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = credit_card_instrument
        mock_db.query.return_value = mock_query

        # Execute matching
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        # Assertions
        assert result is not None
        assert result.id == credit_card_instrument.id
        assert result.last_four_digits == "5678"
        assert result.type == PaymentInstrumentType.CREDIT_CARD

    def test_match_p2p_account_by_type(self, mock_db, user_id, p2p_instrument, parsed_transaction_p2p):
        """Test matching P2P account by transaction type."""
        # parsed_transaction_p2p has card_last_four=None, so the card-matching branch is
        # skipped entirely and only ONE db.query().filter().first() call is made (the P2P query).
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = p2p_instrument
        mock_db.query.return_value = mock_query

        # Execute matching
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_p2p,
            user_id=user_id
        )

        # Assertions
        assert result is not None
        assert result.id == p2p_instrument.id
        assert result.type == PaymentInstrumentType.P2P_ACCOUNT

    def test_no_match_found(self, mock_db, user_id, parsed_transaction_card):
        """Test when no matching payment instrument found."""
        # Setup mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute matching
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        # Assertions
        assert result is None

    def test_match_only_active_instruments(self, mock_db, user_id, parsed_transaction_card):
        """Test that only active instruments are matched."""
        # Create inactive instrument
        _inactive_instrument = PaymentInstrument(
            id=uuid4(),
            user_id=user_id,
            type=PaymentInstrumentType.CREDIT_CARD,
            last_four_digits="5678",
            status=PaymentInstrumentStatus.INACTIVE
        )

        # Setup mock to verify status filter
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute matching
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        # Should not match inactive instrument
        assert result is None

    def test_match_and_normalize_success(self, mock_db, user_id, credit_card_instrument, parsed_transaction_card):
        """Test full match and normalize flow."""
        # Setup mocks
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = credit_card_instrument
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.flush = Mock()

        # Execute
        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        # Assertions
        assert result is not None
        assert isinstance(result, NormalizedTransaction)
        assert result.payment_instrument_id == credit_card_instrument.id
        assert result.merchant_normalized == "Starbucks"
        assert result.amount == Decimal("12.50")
        assert result.category == TransactionCategory.DINING
        assert result.category_confidence >= 90.0
        assert result.category_source == "auto_rules"
        assert result.reimbursement_status == ReimbursementStatus.NONE
        assert result.reimbursed_amount == Decimal("0.00")
        assert result.net_amount == Decimal("12.50")

        # Verify db calls
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_match_and_normalize_no_instrument(self, mock_db, user_id, parsed_transaction_card):
        """Test normalize when no matching instrument found.

        match_and_normalize always produces a NormalizedTransaction.
        When no instrument matches, payment_instrument_id is None (unlinked)
        so the transaction still appears in the UI.
        """
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        assert result is not None
        assert result.payment_instrument_id is None
        assert result.merchant_normalized is not None
        assert result.amount == parsed_transaction_card.amount

    def test_merchant_normalization_applied(self, mock_db, user_id, credit_card_instrument):
        """Test that merchant normalization is applied during matching."""
        # Create transaction with raw merchant name
        parsed_txn = ParsedTransaction(
            id=uuid4(),
            raw_email_id=uuid4(),
            email_account_id=uuid4(),
            merchant_name="SQ *COFFEE SHOP",
            amount=Decimal("10.00"),
            currency="USD",
            transaction_date=datetime(2026, 2, 10),
            card_last_four="5678",
            transaction_type="purchase"
        )

        # Setup mocks
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = credit_card_instrument
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.flush = Mock()

        # Execute
        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=mock_db,
            parsed_transaction=parsed_txn,
            user_id=user_id
        )

        # Check normalized merchant name
        assert result.merchant_normalized == "Square"

    def test_categorization_applied(self, mock_db, user_id, credit_card_instrument):
        """Test that categorization is applied during matching."""
        # Create transaction
        parsed_txn = ParsedTransaction(
            id=uuid4(),
            raw_email_id=uuid4(),
            email_account_id=uuid4(),
            merchant_name="WHOLE FOODS",
            amount=Decimal("75.00"),
            currency="USD",
            transaction_date=datetime(2026, 2, 10),
            card_last_four="5678",
            transaction_type="purchase"
        )

        # Setup mocks
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = credit_card_instrument
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.flush = Mock()

        # Execute
        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=mock_db,
            parsed_transaction=parsed_txn,
            user_id=user_id
        )

        # Check category
        assert result.category == TransactionCategory.GROCERIES
        assert result.category_confidence >= 90.0

    def test_p2p_transfer_categorization(self, mock_db, user_id, p2p_instrument, parsed_transaction_p2p):
        """Test that P2P transfers get correct category."""
        # parsed_transaction_p2p has card_last_four=None, so only the P2P query fires.
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = p2p_instrument
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.flush = Mock()

        # Execute
        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=mock_db,
            parsed_transaction=parsed_transaction_p2p,
            user_id=user_id
        )

        # Check transfer category
        assert result.category == TransactionCategory.TRANSFER
        assert result.category_confidence >= 90.0

    def test_debit_card_matching(self, mock_db, user_id, parsed_transaction_card):
        """Test matching debit card (similar to credit card)."""
        # Create debit card instrument
        debit_card = PaymentInstrument(
            id=uuid4(),
            user_id=user_id,
            type=PaymentInstrumentType.DEBIT_CARD,
            issuer="chase",
            display_name="Chase Checking",
            last_four_digits="5678",
            network="visa",
            status=PaymentInstrumentStatus.ACTIVE
        )

        # Setup mock
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = debit_card
        mock_db.query.return_value = mock_query

        # Execute
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=user_id
        )

        # Assertions
        assert result is not None
        assert result.type == PaymentInstrumentType.DEBIT_CARD

    def test_user_scoping(self, mock_db, credit_card_instrument, parsed_transaction_card):
        """Test that instruments are scoped to correct user."""
        different_user_id = str(uuid4())

        # Setup mock
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute with different user
        result = PaymentInstrumentMatchingService._find_matching_instrument(
            db=mock_db,
            parsed_transaction=parsed_transaction_card,
            user_id=different_user_id
        )

        # Should not match (different user)
        assert result is None