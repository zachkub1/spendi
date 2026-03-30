"""
Transaction management routes.
API endpoints for viewing and managing transactions, payment instruments, and categories.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID
import logging

from app.db.session import get_db
from app.db.models import (
    User,
    EmailAccount,
    ParsedTransaction,
    NormalizedTransaction,
    PaymentInstrument,
    PaymentInstrumentType,
    PaymentInstrumentStatus,
    TransactionCategory
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ========== Pydantic Models ==========

class PaymentInstrumentCreate(BaseModel):
    """Request model for creating a payment instrument."""
    type: PaymentInstrumentType
    issuer: Optional[str] = None
    display_name: str
    network: Optional[str] = None
    last_four_digits: Optional[str] = Field(None, min_length=4, max_length=4)
    account_identifier: Optional[str] = None

    class Config:
        use_enum_values = True


class PaymentInstrumentResponse(BaseModel):
    """Response model for payment instrument."""
    id: UUID
    type: PaymentInstrumentType
    issuer: Optional[str]
    display_name: str
    network: Optional[str]
    last_four_digits: Optional[str]
    account_identifier: Optional[str]
    status: PaymentInstrumentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class TransactionResponse(BaseModel):
    """Response model for normalized transaction."""
    id: UUID
    merchant_normalized: str
    amount: Decimal
    currency: str
    transaction_date: datetime
    transaction_type: str
    category: TransactionCategory
    category_confidence: Optional[Decimal]
    category_source: Optional[str]
    reimbursement_status: str
    reimbursed_amount: Decimal
    net_amount: Decimal
    payment_instrument: PaymentInstrumentResponse
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class CategoryUpdateRequest(BaseModel):
    """Request model for updating transaction category."""
    category: TransactionCategory

    class Config:
        use_enum_values = True


class MonthlyInsightItem(BaseModel):
    """Spending totals for a single month."""
    month: int          # 1–12
    total_amount: str   # gross amount charged (Decimal as string)
    reimbursed: str     # total reimbursed (Decimal as string)
    net: str            # net spending = total_amount − reimbursed
    count: int          # number of transactions


class YearlyInsightItem(BaseModel):
    """Spending totals for a single year."""
    year: int
    total_amount: str
    reimbursed: str
    net: str
    count: int


# ========== Payment Instrument Endpoints ==========

@router.post("/payment-instruments", response_model=PaymentInstrumentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_instrument(
    instrument_data: PaymentInstrumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new payment instrument (credit card, debit card, or P2P account).

    This allows users to register their payment methods so transactions can be
    automatically matched to the correct card/account.
    """
    # Validate that either last_four_digits or account_identifier is provided
    if instrument_data.type in [PaymentInstrumentType.CREDIT_CARD, PaymentInstrumentType.DEBIT_CARD]:
        if not instrument_data.last_four_digits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_four_digits is required for credit/debit cards"
            )
    elif instrument_data.type == PaymentInstrumentType.P2P_ACCOUNT:
        if not instrument_data.account_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="account_identifier is required for P2P accounts"
            )

    # Check for duplicate
    existing = db.query(PaymentInstrument).filter(
        PaymentInstrument.user_id == current_user.id,
        PaymentInstrument.last_four_digits == instrument_data.last_four_digits if instrument_data.last_four_digits else False,
        PaymentInstrument.account_identifier == instrument_data.account_identifier if instrument_data.account_identifier else False
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment instrument with these details already exists"
        )

    # Create payment instrument
    instrument = PaymentInstrument(
        user_id=current_user.id,
        type=instrument_data.type,
        issuer=instrument_data.issuer,
        display_name=instrument_data.display_name,
        network=instrument_data.network,
        last_four_digits=instrument_data.last_four_digits,
        account_identifier=instrument_data.account_identifier,
        status=PaymentInstrumentStatus.ACTIVE
    )

    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    logger.info(f"[PAYMENT_INSTRUMENT] Created: {instrument.display_name} for user {current_user.id}")

    return instrument


@router.get("/payment-instruments", response_model=List[PaymentInstrumentResponse])
async def list_payment_instruments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_inactive: bool = Query(False, description="Include inactive instruments")
):
    """
    List all payment instruments for the current user.
    """
    query = db.query(PaymentInstrument).filter(
        PaymentInstrument.user_id == current_user.id
    )

    if not include_inactive:
        query = query.filter(PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE)

    instruments = query.order_by(PaymentInstrument.created_at.desc()).all()

    return instruments


@router.delete("/payment-instruments/{instrument_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_instrument(
    instrument_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a payment instrument as inactive (soft delete).
    """
    instrument = db.query(PaymentInstrument).filter(
        PaymentInstrument.id == instrument_id,
        PaymentInstrument.user_id == current_user.id
    ).first()

    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment instrument not found"
        )

    instrument.status = PaymentInstrumentStatus.INACTIVE
    db.commit()

    logger.info(f"[PAYMENT_INSTRUMENT] Deactivated: {instrument.display_name} for user {current_user.id}")

    return None


# ========== Transaction Endpoints ==========

def _apply_demo_filter(query, include_demo: bool):
    """Join through ParsedTransaction → EmailAccount to exclude demo-account rows."""
    if not include_demo:
        query = (
            query
            .join(ParsedTransaction, ParsedTransaction.id == NormalizedTransaction.parsed_transaction_id)
            .join(EmailAccount, EmailAccount.id == ParsedTransaction.email_account_id)
            .filter(EmailAccount.provider != "demo")
        )
    return query


@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[TransactionCategory] = Query(None, description="Filter by category"),
    payment_instrument_id: Optional[UUID] = Query(None, description="Filter by payment instrument"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    include_demo: bool = Query(True, description="Include demo-account transactions"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List normalized transactions for the current user.

    Supports filtering by category, payment instrument, date range, and demo visibility.
    Results are paginated and sorted by transaction date (most recent first).
    """
    query = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.user_id == current_user.id
    )

    query = _apply_demo_filter(query, include_demo)

    # Apply filters
    if category:
        query = query.filter(NormalizedTransaction.category == category)

    if payment_instrument_id:
        query = query.filter(NormalizedTransaction.payment_instrument_id == payment_instrument_id)

    if start_date:
        query = query.filter(NormalizedTransaction.transaction_date >= start_date)

    if end_date:
        query = query.filter(NormalizedTransaction.transaction_date <= end_date)

    # Sort by transaction date (most recent first)
    query = query.order_by(NormalizedTransaction.transaction_date.desc())

    # Paginate
    transactions = query.offset(offset).limit(limit).all()

    return transactions


@router.get("/summary")
async def get_transaction_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    include_demo: bool = Query(True),
):
    """
    Return per-category aggregates (count + total net_amount) for the current user.
    Used by the transactions page to populate category summary cards.
    """
    query = db.query(
        NormalizedTransaction.category,
        func.count(NormalizedTransaction.id).label("count"),
        func.sum(NormalizedTransaction.net_amount).label("total_amount"),
    ).filter(NormalizedTransaction.user_id == current_user.id)

    query = _apply_demo_filter(query, include_demo)

    if start_date:
        query = query.filter(NormalizedTransaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(NormalizedTransaction.transaction_date <= end_date)

    rows = query.group_by(NormalizedTransaction.category).all()

    categories = sorted(
        [
            {
                "category": row.category.value,
                "count": row.count,
                "total_amount": str(row.total_amount or "0.00"),
            }
            for row in rows
        ],
        key=lambda x: float(x["total_amount"]),
        reverse=True,
    )

    total_transactions = sum(r["count"] for r in categories)

    return {
        "categories": categories,
        "total_transactions": total_transactions,
    }


# ========== Insights Endpoints ==========

@router.get("/insights/monthly", response_model=List[MonthlyInsightItem])
async def get_monthly_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: int = Query(default=None, description="Year to aggregate (default: current year)"),
    category: Optional[TransactionCategory] = Query(None, description="Filter by category"),
    include_demo: bool = Query(True),
):
    """
    Return monthly spending totals for the given year.

    Always returns 12 items (one per month). Months with no transactions return zeros.
    Amounts are net_amount (gross minus reimbursements) per finance rules.
    """
    if year is None:
        year = datetime.now().year

    query = db.query(
        extract("month", NormalizedTransaction.transaction_date).label("month"),
        func.sum(NormalizedTransaction.amount).label("total_amount"),
        func.sum(NormalizedTransaction.reimbursed_amount).label("reimbursed"),
        func.sum(NormalizedTransaction.net_amount).label("net"),
        func.count(NormalizedTransaction.id).label("count"),
    ).filter(
        NormalizedTransaction.user_id == current_user.id,
        extract("year", NormalizedTransaction.transaction_date) == year,
    )

    query = _apply_demo_filter(query, include_demo)

    if category:
        query = query.filter(NormalizedTransaction.category == category)

    rows = query.group_by(
        extract("month", NormalizedTransaction.transaction_date)
    ).order_by(
        extract("month", NormalizedTransaction.transaction_date)
    ).all()

    # Build a dict keyed by month so we can fill zeros for months with no data
    by_month = {
        int(row.month): MonthlyInsightItem(
            month=int(row.month),
            total_amount=str(row.total_amount or "0.00"),
            reimbursed=str(row.reimbursed or "0.00"),
            net=str(row.net or "0.00"),
            count=row.count,
        )
        for row in rows
    }

    zero = MonthlyInsightItem(month=0, total_amount="0.00", reimbursed="0.00", net="0.00", count=0)
    result = [by_month.get(m, MonthlyInsightItem(**{**zero.__dict__, "month": m})) for m in range(1, 13)]

    logger.debug(f"[INSIGHTS] Monthly {year}: {sum(r.count for r in result)} transactions across {sum(1 for r in result if r.count > 0)} months")
    return result


@router.get("/insights/yearly", response_model=List[YearlyInsightItem])
async def get_yearly_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[TransactionCategory] = Query(None, description="Filter by category"),
    include_demo: bool = Query(True),
):
    """
    Return yearly spending totals across all years with transactions.

    Results are ordered chronologically (earliest year first).
    """
    query = db.query(
        extract("year", NormalizedTransaction.transaction_date).label("year"),
        func.sum(NormalizedTransaction.amount).label("total_amount"),
        func.sum(NormalizedTransaction.reimbursed_amount).label("reimbursed"),
        func.sum(NormalizedTransaction.net_amount).label("net"),
        func.count(NormalizedTransaction.id).label("count"),
    ).filter(
        NormalizedTransaction.user_id == current_user.id,
    )

    query = _apply_demo_filter(query, include_demo)

    if category:
        query = query.filter(NormalizedTransaction.category == category)

    rows = query.group_by(
        extract("year", NormalizedTransaction.transaction_date)
    ).order_by(
        extract("year", NormalizedTransaction.transaction_date)
    ).all()

    result = [
        YearlyInsightItem(
            year=int(row.year),
            total_amount=str(row.total_amount or "0.00"),
            reimbursed=str(row.reimbursed or "0.00"),
            net=str(row.net or "0.00"),
            count=row.count,
        )
        for row in rows
    ]

    logger.debug(f"[INSIGHTS] Yearly: {len(result)} year(s) with data")
    return result


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single transaction by ID.
    """
    transaction = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.patch("/{transaction_id}/category", response_model=TransactionResponse)
async def update_transaction_category(
    transaction_id: UUID,
    category_update: CategoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the category of a transaction (user override).

    This creates a new version of the transaction with the updated category
    and marks the category source as "user_override" for audit trail.
    """
    transaction = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Update category
    transaction.category = category_update.category
    transaction.category_confidence = Decimal("100.0")  # User override = 100% confidence
    transaction.category_source = "user_override"

    db.commit()
    db.refresh(transaction)

    logger.info(
        f"[TRANSACTION] Category updated: {transaction.id} -> {category_update.category} "
        f"by user {current_user.id}"
    )

    return transaction