"""add_direction_field

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-06 01:00:00.000000

Adds a direction column ('incoming' | 'outgoing' | 'transfer') to
parsed_transactions and normalized_transactions.

- outgoing: expense the user paid (positive net_amount)
- incoming: money received, e.g. Zelle/Venmo receipt (negative net_amount)
- transfer: neutral bank movement (bank cashout, bill payment)

Existing rows default to 'outgoing' so historical data is unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'parsed_transactions',
        sa.Column('direction', sa.String(20), nullable=False, server_default='outgoing'),
    )
    op.add_column(
        'normalized_transactions',
        sa.Column('direction', sa.String(20), nullable=False, server_default='outgoing'),
    )


def downgrade() -> None:
    op.drop_column('normalized_transactions', 'direction')
    op.drop_column('parsed_transactions', 'direction')
