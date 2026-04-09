"""
P2P transaction routes (Zelle + Venmo).

Endpoints for listing, searching, renaming senders, matching to existing
transactions for reimbursement tracking, and changing transaction types.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID
import logging

from app.db.session import get_db
from app.db.models import (
    User,
    NormalizedTransaction,
    ReimbursementStatus,
    TransactionCategory,
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions/p2p", tags=["P2P Transactions"])


# ========== Pydantic Models ==========

class P2PTransactionResponse(BaseModel):
    """Response model for a P2P (Zelle/Venmo) transaction."""
    id: UUID
    sender_name: Optional[str]
    merchant_normalized: str
    amount: Decimal
    currency: str
    transaction_date: datetime
    transaction_type: str
    p2p_source: Optional[str]
    p2p_transaction_id: Optional[str]
    category: TransactionCategory
    reimbursement_status: str
    matched_to_transaction_id: Optional[UUID]
    matched_to_transaction: Optional["MatchedTransactionSummary"]
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class MatchedTransactionSummary(BaseModel):
    """Summary of the transaction a P2P payment is matched to."""
    id: UUID
    merchant_normalized: str
    amount: Decimal
    transaction_date: datetime
    category: TransactionCategory

    class Config:
        from_attributes = True
        use_enum_values = True


# Allow forward reference resolution
P2PTransactionResponse.model_rebuild()


class RecentTransactionResponse(BaseModel):
    """Lightweight transaction for the match-picker list."""
    id: UUID
    merchant_normalized: str
    amount: Decimal
    transaction_date: datetime
    category: TransactionCategory
    reimbursement_status: str

    class Config:
        from_attributes = True
        use_enum_values = True


class SenderNameUpdate(BaseModel):
    sender_name: str


class MatchRequest(BaseModel):
    target_transaction_id: UUID


class TypeUpdateRequest(BaseModel):
    category: TransactionCategory

    class Config:
        use_enum_values = True


# ========== Helpers ==========

def _get_p2p_txn(db: Session, txn_id: UUID, user_id) -> NormalizedTransaction:
    """Fetch a P2P transaction owned by the user or raise 404."""
    txn = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == txn_id,
        NormalizedTransaction.user_id == user_id,
        NormalizedTransaction.p2p_source.isnot(None),
    ).first()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="P2P transaction not found")
    return txn


# ========== Endpoints ==========

@router.get("/", response_model=List[P2PTransactionResponse])
async def list_p2p_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    source: Optional[str] = Query(None, description="Filter by source: 'zelle' or 'venmo'"),
    hours: Optional[int] = Query(24, description="Transactions within the last N hours (0 = all)"),
    search: Optional[str] = Query(None, description="Search by sender name, amount, or transaction ID"),
    unmatched_only: bool = Query(False, description="Only show unmatched transactions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List Zelle and Venmo transactions for the current user.

    Defaults to last 24 hours. Pass hours=0 to return all P2P transactions.
    Results are sorted: unmatched first, then by date descending.
    """
    query = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.user_id == current_user.id,
        NormalizedTransaction.p2p_source.isnot(None),
    )

    if source:
        query = query.filter(NormalizedTransaction.p2p_source == source.lower())

    if hours and hours > 0:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        # transaction_date may be naive UTC — compare without tz
        since_naive = since.replace(tzinfo=None)
        query = query.filter(NormalizedTransaction.transaction_date >= since_naive)

    if unmatched_only:
        query = query.filter(NormalizedTransaction.matched_to_transaction_id.is_(None))

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            or_(
                NormalizedTransaction.sender_name.ilike(search_lower),
                NormalizedTransaction.merchant_normalized.ilike(search_lower),
                NormalizedTransaction.p2p_transaction_id.ilike(search_lower),
            )
        )

    # Unmatched first, then most recent
    query = query.order_by(
        NormalizedTransaction.matched_to_transaction_id.asc().nullsfirst(),
        NormalizedTransaction.transaction_date.desc(),
    )

    transactions = query.offset(offset).limit(limit).all()
    return transactions


@router.get("/recent-transactions", response_model=List[RecentTransactionResponse])
async def list_recent_transactions_for_matching(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Filter by merchant name or amount"),
    days: int = Query(30, description="Transactions within the last N days"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Return recent non-P2P transactions to populate the match picker.

    Excludes transactions that are already fully reimbursed so users only
    see candidates that still need matching.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_naive = since.replace(tzinfo=None)

    query = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.user_id == current_user.id,
        NormalizedTransaction.p2p_source.is_(None),  # exclude P2P transactions themselves
        NormalizedTransaction.transaction_date >= since_naive,
        NormalizedTransaction.reimbursement_status != ReimbursementStatus.COMPLETE,
    )

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            NormalizedTransaction.merchant_normalized.ilike(search_lower)
        )

    transactions = query.order_by(NormalizedTransaction.transaction_date.desc()).limit(limit).all()
    return transactions


@router.patch("/{txn_id}/sender-name", response_model=P2PTransactionResponse)
async def update_sender_name(
    txn_id: UUID,
    body: SenderNameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the display name for the sender of a P2P transaction.

    Original parsed merchant name is preserved in merchant_normalized;
    sender_name is the user-customizable display label.
    """
    txn = _get_p2p_txn(db, txn_id, current_user.id)
    txn.sender_name = body.sender_name.strip()
    db.commit()
    db.refresh(txn)
    logger.info("[P2P] sender_name updated: txn=%s name=%r user=%s", txn_id, txn.sender_name, current_user.id)
    return txn


@router.patch("/{txn_id}/match", response_model=P2PTransactionResponse)
async def match_p2p_to_transaction(
    txn_id: UUID,
    body: MatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Match a P2P transfer to an existing expense transaction as reimbursement.

    - The target transaction's reimbursed_amount is increased by the P2P amount.
    - Its net_amount and reimbursement_status are updated accordingly.
    - The P2P transaction is linked via matched_to_transaction_id.

    Ownership of both transactions is verified before any mutation.
    """
    p2p_txn = _get_p2p_txn(db, txn_id, current_user.id)

    if p2p_txn.matched_to_transaction_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="P2P transaction is already matched. Unmatch it first.",
        )

    # Fetch target transaction — must belong to same user and not be a P2P tx itself
    target = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == body.target_transaction_id,
        NormalizedTransaction.user_id == current_user.id,
        NormalizedTransaction.p2p_source.is_(None),
    ).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target transaction not found",
        )

    # Apply reimbursement to the target
    new_reimbursed = (target.reimbursed_amount or Decimal("0.00")) + p2p_txn.amount
    new_net = target.amount - new_reimbursed

    if new_reimbursed >= target.amount:
        target.reimbursement_status = ReimbursementStatus.COMPLETE
        target.reimbursed_amount = target.amount  # cap at full amount
        target.net_amount = Decimal("0.00")
    else:
        target.reimbursement_status = ReimbursementStatus.PARTIAL
        target.reimbursed_amount = new_reimbursed
        target.net_amount = new_net

    # Link P2P transaction to the target
    p2p_txn.matched_to_transaction_id = target.id

    db.commit()
    db.refresh(p2p_txn)

    logger.info(
        "[P2P] Matched: p2p_txn=%s -> target=%s amount=%s user=%s",
        txn_id, target.id, p2p_txn.amount, current_user.id,
    )
    return p2p_txn


@router.delete("/{txn_id}/match", response_model=P2PTransactionResponse)
async def unmatch_p2p_transaction(
    txn_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unlink a P2P transaction from the expense it was matched to.

    Reverses the reimbursement applied to the target transaction.
    """
    p2p_txn = _get_p2p_txn(db, txn_id, current_user.id)

    if not p2p_txn.matched_to_transaction_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="P2P transaction is not matched to any transaction.",
        )

    # Reverse reimbursement on target
    target = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == p2p_txn.matched_to_transaction_id,
        NormalizedTransaction.user_id == current_user.id,
    ).first()

    if target:
        new_reimbursed = max(
            Decimal("0.00"),
            (target.reimbursed_amount or Decimal("0.00")) - p2p_txn.amount,
        )
        target.reimbursed_amount = new_reimbursed
        target.net_amount = target.amount - new_reimbursed
        target.reimbursement_status = (
            ReimbursementStatus.PARTIAL if new_reimbursed > Decimal("0.00")
            else ReimbursementStatus.NONE
        )

    p2p_txn.matched_to_transaction_id = None

    db.commit()
    db.refresh(p2p_txn)

    logger.info("[P2P] Unmatched: p2p_txn=%s user=%s", txn_id, current_user.id)
    return p2p_txn


@router.patch("/{txn_id}/type", response_model=P2PTransactionResponse)
async def update_p2p_type(
    txn_id: UUID,
    body: TypeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the category of a P2P transaction (user override).

    Allows marking a P2P transfer as income, reimbursement, gift, etc.
    """
    txn = _get_p2p_txn(db, txn_id, current_user.id)
    txn.category = body.category
    txn.category_confidence = Decimal("100.0")
    txn.category_source = "user_override"
    db.commit()
    db.refresh(txn)
    logger.info("[P2P] Category updated: txn=%s -> %s user=%s", txn_id, body.category, current_user.id)
    return txn
