"""add_p2p_fields

Revision ID: c3f1a2b4d5e6
Revises: aa0066a212d9
Create Date: 2026-04-08 00:00:00.000000

Adds P2P metadata columns to parsed_transactions and normalized_transactions,
plus a self-referential matched_to_transaction_id on normalized_transactions
for reimbursement matching.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f1a2b4d5e6'
down_revision: Union[str, None] = 'aa0066a212d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── parsed_transactions: add p2p metadata ──────────────────────────────
    op.add_column('parsed_transactions',
        sa.Column('p2p_transaction_id', sa.String(length=255), nullable=True))
    op.add_column('parsed_transactions',
        sa.Column('p2p_source', sa.String(length=50), nullable=True))

    # ── normalized_transactions: add p2p metadata + matching FK ───────────
    op.add_column('normalized_transactions',
        sa.Column('sender_name', sa.String(length=255), nullable=True))
    op.add_column('normalized_transactions',
        sa.Column('p2p_transaction_id', sa.String(length=255), nullable=True))
    op.add_column('normalized_transactions',
        sa.Column('p2p_source', sa.String(length=50), nullable=True))
    op.add_column('normalized_transactions',
        sa.Column('matched_to_transaction_id', sa.UUID(), nullable=True))

    op.create_foreign_key(
        'fk_normalized_txn_matched_to',
        'normalized_transactions',
        'normalized_transactions',
        ['matched_to_transaction_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_normalized_txn_matched_to', 'normalized_transactions', type_='foreignkey')
    op.drop_column('normalized_transactions', 'matched_to_transaction_id')
    op.drop_column('normalized_transactions', 'p2p_source')
    op.drop_column('normalized_transactions', 'p2p_transaction_id')
    op.drop_column('normalized_transactions', 'sender_name')
    op.drop_column('parsed_transactions', 'p2p_source')
    op.drop_column('parsed_transactions', 'p2p_transaction_id')
