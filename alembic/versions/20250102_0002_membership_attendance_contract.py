"""Reconcile membership and attendance fields with the public API contract.

Revision ID: 20250102_0002
Revises: 20250101_0001
Create Date: 2025-01-02 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250102_0002"
down_revision: Union[str, Sequence[str], None] = "20250101_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


plan_status = sa.Enum("ACTIVE", "INACTIVE", name="planstatus", native_enum=False, length=16)
payment_status = sa.Enum("PENDING", "PAID", "FAILED", "REFUNDED", name="paymentstatus", native_enum=False, length=16)


def upgrade() -> None:
    # Add nullable first so populated installations can be safely backfilled.
    with op.batch_alter_table("membership_plans") as batch:
        batch.add_column(sa.Column("features", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("status", plan_status, nullable=True))
    op.execute("UPDATE membership_plans SET features = '[]' WHERE features IS NULL")
    op.execute("UPDATE membership_plans SET status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END")
    with op.batch_alter_table("membership_plans") as batch:
        batch.alter_column("features", existing_type=sa.JSON(), nullable=False)
        batch.alter_column("status", existing_type=plan_status, nullable=False, server_default="ACTIVE")
        batch.drop_column("is_active")

    with op.batch_alter_table("memberships") as batch:
        batch.add_column(sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=True))
        batch.add_column(sa.Column("payment_status", payment_status, nullable=True))
    # A membership's historical plan price is the least-surprising amount backfill.
    op.execute("UPDATE memberships SET amount = (SELECT price FROM membership_plans WHERE membership_plans.id = memberships.plan_id) WHERE amount IS NULL")
    op.execute("UPDATE memberships SET payment_status = 'PENDING' WHERE payment_status IS NULL")
    with op.batch_alter_table("memberships") as batch:
        batch.alter_column("amount", existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
        batch.alter_column("payment_status", existing_type=payment_status, nullable=False, server_default="PENDING")

    # Rename preserves recorded check-in timestamps. Older absent/partial rows get a
    # deterministic migration-time timestamp before the new required constraint.
    with op.batch_alter_table("attendance") as batch:
        batch.alter_column("checked_in_at", new_column_name="check_in_at",
                           existing_type=sa.DateTime(timezone=True), existing_nullable=True)
    op.execute("UPDATE attendance SET check_in_at = CURRENT_TIMESTAMP WHERE check_in_at IS NULL")
    with op.batch_alter_table("attendance") as batch:
        batch.alter_column("check_in_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.drop_column("status")
        batch.drop_column("notes")


def downgrade() -> None:
    with op.batch_alter_table("attendance") as batch:
        batch.add_column(sa.Column("status", sa.Enum("PRESENT", "ABSENT", name="attendancestatus", native_enum=False, length=16),
                                  nullable=False, server_default="PRESENT"))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch.alter_column("check_in_at", new_column_name="checked_in_at",
                           existing_type=sa.DateTime(timezone=True), nullable=True)

    with op.batch_alter_table("memberships") as batch:
        batch.drop_column("payment_status")
        batch.drop_column("amount")

    with op.batch_alter_table("membership_plans") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))
    op.execute("UPDATE membership_plans SET is_active = CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END")
    with op.batch_alter_table("membership_plans") as batch:
        batch.alter_column("is_active", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("1"))
        batch.drop_column("status")
        batch.drop_column("features")
