"""add_feedback_table

Revision ID: d6e7f8a9b0c1
Revises: c3f1a2b4d5e6
Create Date: 2026-04-13 00:00:00.000000

Creates the feedback table for user-submitted bug reports, suggestions,
and transaction classification issues.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c3f1a2b4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FEEDBACK_TYPE_ENUM = sa.Enum(
    "bug",
    "suggestion",
    "classification_issue",
    name="feedbacktype",
)


def upgrade() -> None:
    # Let op.create_table own the enum type lifecycle.
    # Explicit pre-creation + create_type=False triggers a duplicate-type error
    # in SQLAlchemy 2.0 because _on_table_create fires regardless of create_type.
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("bug", "suggestion", "classification_issue", name="feedbacktype"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("transaction_example", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    _FEEDBACK_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
