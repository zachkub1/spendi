"""make_payment_instrument_nullable

Revision ID: e1f2a3b4c5d6
Revises: d6e7f8a9b0c1
Create Date: 2026-05-06 00:00:00.000000

Makes payment_instrument_id nullable on normalized_transactions so that
parsed transactions without a matching card instrument still appear in the
UI (shown as "Unlinked"). Previously, unmatched transactions were silently
dropped, causing the dashboard to look empty even after Gmail sync.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'normalized_transactions',
        'payment_instrument_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    # Remove unlinked rows first to satisfy the NOT NULL constraint
    op.execute(
        "DELETE FROM normalized_transactions WHERE payment_instrument_id IS NULL"
    )
    op.alter_column(
        'normalized_transactions',
        'payment_instrument_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
