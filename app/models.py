"""Relational domain model for the gym API."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    TRAINER = "trainer"
    MEMBER = "member"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MemberMembershipStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class ProfileStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TrainerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"


class WorkoutStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, native_enum=False, length=16), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    member: Mapped[Optional["Member"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    trainer: Mapped[Optional["Trainer"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Trainer(Timestamped, Base):
    __tablename__ = "trainers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(120))
    experience: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[TrainerStatus] = mapped_column(SqlEnum(TrainerStatus, native_enum=False, length=16), nullable=False, default=TrainerStatus.ACTIVE, server_default="active")
    user: Mapped[User] = relationship(back_populates="trainer")
    assigned_members: Mapped[list["Member"]] = relationship(back_populates="assigned_trainer", foreign_keys="Member.trainer_id")
    attendance_records: Mapped[list["Attendance"]] = relationship(back_populates="trainer")
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(back_populates="trainer")


class Member(Timestamped, Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    trainer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trainers.id", ondelete="SET NULL"), index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(32))
    address: Mapped[Optional[str]] = mapped_column(Text)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(120))
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    membership_status: Mapped[MemberMembershipStatus] = mapped_column(SqlEnum(MemberMembershipStatus, native_enum=False, length=16), nullable=False, default=MemberMembershipStatus.PENDING, server_default="pending")
    profile_status: Mapped[ProfileStatus] = mapped_column(SqlEnum(ProfileStatus, native_enum=False, length=16), nullable=False, default=ProfileStatus.ACTIVE, server_default="active")
    user: Mapped[User] = relationship(back_populates="member")
    assigned_trainer: Mapped[Optional[Trainer]] = relationship(back_populates="assigned_members", foreign_keys=[trainer_id])
    memberships: Mapped[list["Membership"]] = relationship(back_populates="member")
    attendance_records: Mapped[list["Attendance"]] = relationship(back_populates="member")
    payments: Mapped[list["Payment"]] = relationship(back_populates="member")
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(back_populates="member")


class MembershipPlan(Timestamped, Base):
    __tablename__ = "membership_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    duration_days: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="plan")


class Membership(Timestamped, Base):
    __tablename__ = "memberships"
    __table_args__ = (Index("ix_memberships_member_status", "member_id", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(SqlEnum(MembershipStatus, native_enum=False, length=16), nullable=False, index=True)
    member: Mapped[Member] = relationship(back_populates="memberships")
    plan: Mapped[MembershipPlan] = relationship(back_populates="memberships")
    payments: Mapped[list["Payment"]] = relationship(back_populates="membership")


class Attendance(Timestamped, Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("member_id", "attended_on", name="uq_attendance_member_date"), Index("ix_attendance_member_date", "member_id", "attended_on"))
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    trainer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trainers.id", ondelete="SET NULL"), index=True)
    attended_on: Mapped[date] = mapped_column(Date, nullable=False)
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(SqlEnum(AttendanceStatus, native_enum=False, length=16), nullable=False, default=AttendanceStatus.PRESENT)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    member: Mapped[Member] = relationship(back_populates="attendance_records")
    trainer: Mapped[Optional[Trainer]] = relationship(back_populates="attendance_records")


class Payment(Timestamped, Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_member_status", "member_id", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="RESTRICT"), nullable=False)
    membership_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memberships.id", ondelete="SET NULL"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus, native_enum=False, length=16), nullable=False, default=PaymentStatus.PENDING)
    payment_method: Mapped[PaymentMethod] = mapped_column(SqlEnum(PaymentMethod, native_enum=False, length=16), nullable=False)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    member: Mapped[Member] = relationship(back_populates="payments")
    membership: Mapped[Optional[Membership]] = relationship(back_populates="payments")


class WorkoutPlan(Timestamped, Base):
    __tablename__ = "workout_plans"
    __table_args__ = (Index("ix_workout_plans_member_status", "member_id", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=True)
    trainer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trainers.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WorkoutStatus] = mapped_column(SqlEnum(WorkoutStatus, native_enum=False, length=16), nullable=False, default=WorkoutStatus.ACTIVE)
    member: Mapped[Member] = relationship(back_populates="workout_plans")
    trainer: Mapped[Trainer] = relationship(back_populates="workout_plans")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="workout_plan", cascade="all, delete-orphan", order_by="WorkoutExercise.position")


class WorkoutExercise(Timestamped, Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (UniqueConstraint("workout_plan_id", "position", name="uq_workout_exercise_position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workout_plan_id: Mapped[int] = mapped_column(ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(150), nullable=False)
    muscle_group: Mapped[Optional[str]] = mapped_column(String(100))
    sets: Mapped[Optional[int]] = mapped_column()
    repetitions: Mapped[Optional[int]] = mapped_column()
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    duration: Mapped[Optional[int]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    workout_plan: Mapped[WorkoutPlan] = relationship(back_populates="exercises")
