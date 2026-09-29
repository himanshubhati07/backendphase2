"""Add pending to the persisted membership lifecycle contract.

Revision ID: 20250103_0003
Revises: 20250102_0002
Create Date: 2025-01-03 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250103_0003"
down_revision: Union[str, Sequence[str], None] = "20250102_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# These are non-native enums so the revision has identical semantics on SQLite
# and MySQL.  The explicit check constraint is the portable database contract.
old_membership_status = sa.Enum(
    "ACTIVE", "EXPIRED", "CANCELLED", name="membershipstatus",
    native_enum=False, length=16,
)
membership_status = sa.Enum(
    "PENDING", "ACTIVE", "EXPIRED", "CANCELLED", name="membershipstatus",
    native_enum=False, length=16,
)


def upgrade() -> None:
    with op.batch_alter_table("memberships") as batch:
        batch.alter_column(
            "status", existing_type=old_membership_status,
            type_=membership_status, existing_nullable=False,
        )
        batch.create_check_constraint(
            "ck_memberships_status",
            "status IN ('PENDING', 'ACTIVE', 'EXPIRED', 'CANCELLED')",
        )


def downgrade() -> None:
    # The prior schema cannot represent pending.  Preserve a valid lifecycle
    # record by treating unactivated memberships as cancelled before restoring
    # its three-value contract.
    op.execute("UPDATE memberships SET status = 'CANCELLED' WHERE status = 'PENDING'")
    with op.batch_alter_table("memberships") as batch:
        batch.drop_constraint("ck_memberships_status", type_="check")
        batch.alter_column(
            "status", existing_type=membership_status,
            type_=old_membership_status, existing_nullable=False,
        )
