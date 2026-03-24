"""user plan, valid_till, payment_ledger

Revision ID: 003_payment
Revises: 002_firebase
Create Date: 2025-03-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_payment"
down_revision: Union[str, None] = "002_firebase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "plan",
            sa.String(length=32),
            server_default="free",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("valid_till", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "payment_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=64), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_payment_id"),
    )
    op.create_index(
        op.f("ix_payment_ledger_razorpay_order_id"),
        "payment_ledger",
        ["razorpay_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_ledger_user_id"),
        "payment_ledger",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_ledger_user_id"), table_name="payment_ledger")
    op.drop_index(op.f("ix_payment_ledger_razorpay_order_id"), table_name="payment_ledger")
    op.drop_table("payment_ledger")
    op.drop_column("users", "valid_till")
    op.drop_column("users", "plan")
