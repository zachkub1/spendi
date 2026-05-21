"""make_parsed_transaction_id_nullable

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-21 00:00:00.000000

Allow normalized_transactions.parsed_transaction_id to be NULL so that
manually-entered cash transactions (which have no email origin) can be
persisted directly. Email-sourced transactions continue to set this FK.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'normalized_transactions',
        'parsed_transaction_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    # Remove manual-entry rows before re-enforcing NOT NULL
    op.execute(
        "DELETE FROM normalized_transactions WHERE parsed_transaction_id IS NULL"
    )
    op.alter_column(
        'normalized_transactions',
        'parsed_transaction_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
