"""Create the initial Gym API schema.

Revision ID: 20250101_0001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250101_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "TRAINER", "MEMBER", name="userrole", native_enum=False, length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_timestamp_columns(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "membership_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        *_timestamp_columns(),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "trainers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=True),
        sa.Column("experience", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "INACTIVE", name="trainerstatus", native_enum=False, length=16), server_default="active", nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_trainers_email", "trainers", ["email"], unique=True)
    op.create_index("ix_trainers_phone", "trainers", ["phone"], unique=True)

    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("emergency_contact", sa.String(length=120), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("membership_status", sa.Enum("ACTIVE", "INACTIVE", "EXPIRED", "CANCELLED", "PENDING", name="membermembershipstatus", native_enum=False, length=16), server_default="pending", nullable=False),
        sa.Column("profile_status", sa.Enum("ACTIVE", "INACTIVE", name="profilestatus", native_enum=False, length=16), server_default="active", nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_members_email", "members", ["email"], unique=True)
    op.create_index("ix_members_phone", "members", ["phone"], unique=True)
    op.create_index("ix_members_trainer_id", "members", ["trainer_id"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "EXPIRED", "CANCELLED", name="membershipstatus", native_enum=False, length=16), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["membership_plans.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_memberships_member_status", "memberships", ["member_id", "status"], unique=False)
    op.create_index("ix_memberships_status", "memberships", ["status"], unique=False)

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=True),
        sa.Column("attended_on", sa.Date(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("PRESENT", "ABSENT", name="attendancestatus", native_enum=False, length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("member_id", "attended_on", name="uq_attendance_member_date"),
    )
    op.create_index("ix_attendance_member_date", "attendance", ["member_id", "attended_on"], unique=False)
    op.create_index("ix_attendance_trainer_id", "attendance", ["trainer_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PAID", "FAILED", "REFUNDED", name="paymentstatus", native_enum=False, length=16), nullable=False),
        sa.Column("payment_method", sa.Enum("CASH", "CARD", "UPI", "BANK_TRANSFER", name="paymentmethod", native_enum=False, length=16), nullable=False),
        sa.Column("transaction_id", sa.String(length=120), nullable=True),
        sa.Column("payment_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_payments_member_status", "payments", ["member_id", "status"], unique=False)
    op.create_index("ix_payments_membership_id", "payments", ["membership_id"], unique=False)

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("trainer_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "INACTIVE", name="workoutstatus", native_enum=False, length=16), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_workout_plans_member_status", "workout_plans", ["member_id", "status"], unique=False)

    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_plan_id", sa.Integer(), nullable=False),
        sa.Column("exercise_name", sa.String(length=150), nullable=False),
        sa.Column("muscle_group", sa.String(length=100), nullable=True),
        sa.Column("sets", sa.Integer(), nullable=True),
        sa.Column("repetitions", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["workout_plan_id"], ["workout_plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workout_plan_id", "position", name="uq_workout_exercise_position"),
    )


def downgrade() -> None:
    op.drop_table("workout_exercises")
    op.drop_index("ix_workout_plans_member_status", table_name="workout_plans")
    op.drop_table("workout_plans")
    op.drop_index("ix_payments_membership_id", table_name="payments")
    op.drop_index("ix_payments_member_status", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_attendance_trainer_id", table_name="attendance")
    op.drop_index("ix_attendance_member_date", table_name="attendance")
    op.drop_table("attendance")
    op.drop_index("ix_memberships_status", table_name="memberships")
    op.drop_index("ix_memberships_member_status", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_members_trainer_id", table_name="members")
    op.drop_index("ix_members_phone", table_name="members")
    op.drop_index("ix_members_email", table_name="members")
    op.drop_table("members")
    op.drop_index("ix_trainers_phone", table_name="trainers")
    op.drop_index("ix_trainers_email", table_name="trainers")
    op.drop_table("trainers")
    op.drop_table("membership_plans")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
