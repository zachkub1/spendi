"""
Backfill normalization for ParsedTransactions that have no NormalizedTransaction.

Run with:
  cd backend && source venv/bin/activate
  python scripts/backfill_normalization.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import ParsedTransaction, NormalizedTransaction
from app.transactions.matching_service import PaymentInstrumentMatchingService
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    # Find all ParsedTransactions that have no linked NormalizedTransaction
    subquery = db.query(NormalizedTransaction.parsed_transaction_id)
    unmatched = (
        db.query(ParsedTransaction)
        .filter(ParsedTransaction.id.notin_(subquery))
        .all()
    )

    logger.info(f"Found {len(unmatched)} ParsedTransactions with no NormalizedTransaction")

    success = 0
    skipped = 0
    for pt in unmatched:
        logger.info(
            f"  Processing: {pt.merchant_name} ${pt.amount} "
            f"type={pt.transaction_type} last4={pt.card_last_four} p2p={pt.p2p_source}"
        )
        result = PaymentInstrumentMatchingService.match_and_normalize(
            db=db,
            parsed_transaction=pt,
            user_id=str(pt.email_account.user_id),
        )
        if result:
            success += 1
            logger.info(f"    -> Normalized: {result.merchant_normalized} ({result.category})")
        else:
            skipped += 1
            logger.warning("    -> No match found, skipped")

    db.commit()
    logger.info(f"\nDone: {success} normalized, {skipped} skipped (no matching instrument)")

except Exception as e:
    db.rollback()
    logger.error(f"Backfill failed: {e}", exc_info=True)
    sys.exit(1)
finally:
    db.close()
