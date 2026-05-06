"""
P2P transaction routes (Zelle + Venmo).

Endpoints for listing, searching, renaming senders, matching to existing
transactions for reimbursement tracking, and changing transaction types.
Supports split reimbursements: one P2P payment can be linked to multiple
expense transactions via the ReimbursementLink junction table.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, exists
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
    ReimbursementLink,
    ReimbursementStatus,
    TransactionCategory,
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions/p2p", tags=["P2P Transactions"])


# ========== Pydantic Models ==========

class ReimbursementLinkResponse(BaseModel):
    """Details of a single reimbursement link attached to a P2P payment."""
    id: UUID
    target_transaction_id: UUID
    target_merchant: str
    target_amount: Decimal
    target_date: datetime
    amount: Decimal   # portion of P2P payment allocated to this expense
    created_at: datetime

    class Config:
        from_attributes = True


class P2PTransactionResponse(BaseModel):
    """Response model for a P2P (Zelle/Venmo) transaction."""
    id: UUID
    sender_name: Optional[str]
    merchant_normalized: str
    amount: Decimal
    amount_remaining: Decimal
    currency: str
    transaction_date: datetime
    transaction_type: str
    direction: str = "outgoing"
    p2p_source: Optional[str]
    p2p_transaction_id: Optional[str]
    category: TransactionCategory
    reimbursement_status: str
    matches: List[ReimbursementLinkResponse]
    created_at: datetime

    class Config:
        use_enum_values = True


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
    amount: Optional[Decimal] = None  # defaults to min(p2p_remaining, target_remaining)


class TypeUpdateRequest(BaseModel):
    category: TransactionCategory

    class Config:
        use_enum_values = True


# ========== Helpers ==========

def _p2p_response(txn: NormalizedTransaction) -> dict:
    """Build a dict for P2PTransactionResponse from a NormalizedTransaction ORM object."""
    links = txn.reimbursement_links_given
    allocated = sum(lnk.amount for lnk in links) if links else Decimal("0.00")
    return {
        **{col.key: getattr(txn, col.key) for col in txn.__table__.columns},
        "matches": [
            {
                "id": lnk.id,
                "target_transaction_id": lnk.target_transaction_id,
                "target_merchant": lnk.target_transaction.merchant_normalized,
                "target_amount": lnk.target_transaction.amount,
                "target_date": lnk.target_transaction.transaction_date,
                "amount": lnk.amount,
                "created_at": lnk.created_at,
            }
            for lnk in links
        ],
        "amount_remaining": txn.amount - allocated,
    }


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
    unmatched_only: bool = Query(False, description="Only show transactions with no reimbursement links"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List Zelle and Venmo transactions for the current user.

    Defaults to last 24 hours. Pass hours=0 to return all P2P transactions.
    Results are sorted by date descending.
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
        query = query.filter(
            ~exists().where(ReimbursementLink.p2p_transaction_id == NormalizedTransaction.id)
        )

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            or_(
                NormalizedTransaction.sender_name.ilike(search_lower),
                NormalizedTransaction.merchant_normalized.ilike(search_lower),
                NormalizedTransaction.p2p_transaction_id.ilike(search_lower),
            )
        )

    query = query.order_by(NormalizedTransaction.transaction_date.desc())

    transactions = query.offset(offset).limit(limit).all()
    return [P2PTransactionResponse(**_p2p_response(t)) for t in transactions]


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
    return P2PTransactionResponse(**_p2p_response(txn))


@router.patch("/{txn_id}/match", response_model=P2PTransactionResponse)
async def match_p2p_to_transaction(
    txn_id: UUID,
    body: MatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Link a P2P transfer to an existing expense transaction as (partial) reimbursement.

    Multiple links are allowed — one P2P payment can be split across several expenses.
    - `amount` is optional; defaults to min(p2p_remaining, target_remaining).
    - The target's reimbursed_amount, net_amount, and reimbursement_status are updated.

    Ownership of both transactions is verified before any mutation.
    """
    p2p_txn = _get_p2p_txn(db, txn_id, current_user.id)

    # Calculate how much of the P2P payment is still unallocated
    allocated = sum(lnk.amount for lnk in p2p_txn.reimbursement_links_given) if p2p_txn.reimbursement_links_given else Decimal("0.00")
    p2p_remaining = p2p_txn.amount - allocated

    if p2p_remaining <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="P2P payment is already fully allocated.",
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

    # Check if a link for this exact (p2p, target) pair already exists.
    # If so, treat this as an update (upsert) — atomically reverse the old
    # allocation and apply the new one, avoiding a unique-constraint violation.
    existing_link = db.query(ReimbursementLink).filter(
        ReimbursementLink.p2p_transaction_id == p2p_txn.id,
        ReimbursementLink.target_transaction_id == target.id,
    ).first()

    if existing_link:
        # Restore the capacity that the old link consumed so we can re-validate
        # against the true available balances.
        effective_p2p_remaining = p2p_remaining + existing_link.amount
        effective_target_remaining = (
            target.amount - (target.reimbursed_amount or Decimal("0.00")) + existing_link.amount
        )
        link_amount = body.amount if body.amount is not None else min(effective_p2p_remaining, effective_target_remaining)

        if link_amount <= Decimal("0.00"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link amount must be greater than zero.")
        if link_amount > effective_p2p_remaining:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Link amount {link_amount} exceeds P2P remaining balance {effective_p2p_remaining}.")

        # Reverse old contribution, apply new one
        base_reimbursed = (target.reimbursed_amount or Decimal("0.00")) - existing_link.amount
        existing_link.amount = link_amount
        logger.info("[P2P] Rematch (upsert): p2p_txn=%s -> target=%s old_amount=%s new_amount=%s user=%s",
                    txn_id, target.id, existing_link.amount, link_amount, current_user.id)
    else:
        target_remaining = target.amount - (target.reimbursed_amount or Decimal("0.00"))
        link_amount = body.amount if body.amount is not None else min(p2p_remaining, target_remaining)

        if link_amount <= Decimal("0.00"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link amount must be greater than zero.")
        if link_amount > p2p_remaining:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Link amount {link_amount} exceeds P2P remaining balance {p2p_remaining}.")

        db.add(ReimbursementLink(p2p_transaction_id=p2p_txn.id, target_transaction_id=target.id, amount=link_amount))
        base_reimbursed = target.reimbursed_amount or Decimal("0.00")
        logger.info("[P2P] Matched: p2p_txn=%s -> target=%s link_amount=%s user=%s",
                    txn_id, target.id, link_amount, current_user.id)

    # Recompute target reimbursement state
    new_reimbursed = base_reimbursed + link_amount
    if new_reimbursed >= target.amount:
        target.reimbursement_status = ReimbursementStatus.COMPLETE
        target.reimbursed_amount = target.amount
        target.net_amount = Decimal("0.00")
    else:
        target.reimbursement_status = ReimbursementStatus.PARTIAL
        target.reimbursed_amount = new_reimbursed
        target.net_amount = target.amount - new_reimbursed

    db.commit()
    db.refresh(p2p_txn)
    return P2PTransactionResponse(**_p2p_response(p2p_txn))


@router.delete("/{txn_id}/match/{link_id}", response_model=P2PTransactionResponse)
async def unmatch_p2p_transaction(
    txn_id: UUID,
    link_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a specific reimbursement link from a P2P transaction.

    Reverses the reimbursement applied to the target transaction for this link only.
    Other links on the same P2P payment are unaffected.
    """
    p2p_txn = _get_p2p_txn(db, txn_id, current_user.id)

    # Fetch the specific link and verify it belongs to this P2P transaction
    link = db.query(ReimbursementLink).filter(
        ReimbursementLink.id == link_id,
        ReimbursementLink.p2p_transaction_id == txn_id,
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reimbursement link not found.",
        )

    # Verify the user owns the target transaction too
    target = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == link.target_transaction_id,
        NormalizedTransaction.user_id == current_user.id,
    ).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target transaction not found or access denied.",
        )

    # Reverse reimbursement on target
    new_reimbursed = max(
        Decimal("0.00"),
        (target.reimbursed_amount or Decimal("0.00")) - link.amount,
    )
    target.reimbursed_amount = new_reimbursed
    target.net_amount = target.amount - new_reimbursed
    target.reimbursement_status = (
        ReimbursementStatus.PARTIAL if new_reimbursed > Decimal("0.00")
        else ReimbursementStatus.NONE
    )

    db.delete(link)
    db.commit()
    db.refresh(p2p_txn)

    logger.info("[P2P] Unmatched link=%s from p2p_txn=%s user=%s", link_id, txn_id, current_user.id)
    return P2PTransactionResponse(**_p2p_response(p2p_txn))


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
    return P2PTransactionResponse(**_p2p_response(txn))
