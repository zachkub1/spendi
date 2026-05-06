"""add_reimbursement_links

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-05-06 00:00:00.000000

Replaces the one-to-one matched_to_transaction_id FK on normalized_transactions
with a many-to-many junction table (reimbursement_links) that allows a single
incoming P2P payment to be split across multiple expense reimbursements.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the new junction table
    op.create_table(
        'reimbursement_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('p2p_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('normalized_transactions.id'), nullable=False),
        sa.Column('target_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('normalized_transactions.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        # Enforce one link per (P2P payment, expense) pair — prevents duplicate rows
        sa.UniqueConstraint('p2p_transaction_id', 'target_transaction_id', name='uq_reimbursement_link_pair'),
    )
    op.create_index(
        'ix_reimbursement_links_p2p_transaction_id',
        'reimbursement_links',
        ['p2p_transaction_id'],
    )

    # Drop the old one-to-one FK column
    op.drop_column('normalized_transactions', 'matched_to_transaction_id')


def downgrade() -> None:
    # Re-add the old column (data loss: existing links are not migrated back)
    op.add_column(
        'normalized_transactions',
        sa.Column(
            'matched_to_transaction_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('normalized_transactions.id'),
            nullable=True,
        ),
    )

    # Drop the junction table
    op.drop_index('ix_reimbursement_links_p2p_transaction_id', table_name='reimbursement_links')
    op.drop_table('reimbursement_links')
