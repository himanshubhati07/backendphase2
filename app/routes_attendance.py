"""Attendance check-in/out and reporting routes."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from bottle import Bottle, abort, request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .auth import can_manage_member, current_user, enforce, require_auth
from .errors import AppError, ValidationError
from .models import Attendance, Member, Membership, MembershipStatus, ProfileStatus, UserRole
from .responses import success
from .validation import json_body


def _date(value: str | None, field: str, *, default: date | None = None) -> date:
    if value is None and default is not None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an ISO-8601 date") from exc


def _member(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        abort(404)
    return member


def _attendance_data(item: Attendance) -> dict[str, Any]:
    return {"id": item.id, "member_id": item.member_id, "trainer_id": item.trainer_id,
            "attended_on": item.attended_on, "check_in_at": item.check_in_at,
            "checked_out_at": item.checked_out_at, "created_at": item.created_at,
            "updated_at": item.updated_at}


def _active_membership(session: Session, member_id: int, on_date: date) -> bool:
    return session.scalar(select(Membership.id).where(Membership.member_id == member_id,
                          Membership.status == MembershipStatus.ACTIVE,
                          Membership.start_date <= on_date, Membership.end_date >= on_date)) is not None


def _parse_range() -> tuple[date, date]:
    start = _date(request.query.get("start_date"), "start_date")
    end = _date(request.query.get("end_date"), "end_date")
    if end < start:
        raise ValidationError("end_date must not be before start_date")
    return start, end


def register_attendance_routes(app: Bottle) -> None:
    @app.post("/api/attendance/check-in")
    @require_auth()
    def check_in() -> Any:
        session: Session = request.environ["gym.db"]
        body = json_body()
        member_id = body.get("member_id")
        if isinstance(member_id, bool) or not isinstance(member_id, int) or member_id <= 0:
            raise ValidationError("member_id must be a positive integer")
        member = _member(session, member_id)
        enforce(can_manage_member(member))
        attended_on = _date(body.get("attended_on"), "attended_on", default=date.today())
        if member.profile_status is ProfileStatus.INACTIVE:
            raise ValidationError("Inactive member profiles cannot check in")
        if not _active_membership(session, member.id, attended_on):
            raise ValidationError("Member does not have an active membership for this date")
        open_record = session.scalar(select(Attendance.id).where(Attendance.member_id == member.id,
                                                                  Attendance.checked_out_at.is_(None)))
        if open_record is not None:
            raise AppError("Member already has an open attendance record", "CONFLICT", 409)
        if session.scalar(select(Attendance.id).where(Attendance.member_id == member.id,
                                                       Attendance.attended_on == attended_on)) is not None:
            raise AppError("Attendance is already recorded for this date", "CONFLICT", 409)
        user = current_user()
        trainer_id = user.trainer.id if user.role is UserRole.TRAINER and user.trainer else None
        item = Attendance(member_id=member.id, trainer_id=trainer_id, attended_on=attended_on,
                          check_in_at=datetime.now(timezone.utc))
        session.add(item)
        session.commit()
        return success(_attendance_data(item), "Member checked in", 201)

    @app.post("/api/attendance/check-out")
    @require_auth()
    def check_out() -> Any:
        session: Session = request.environ["gym.db"]
        attendance_id = json_body().get("attendance_id")
        if isinstance(attendance_id, bool) or not isinstance(attendance_id, int) or attendance_id <= 0:
            raise ValidationError("attendance_id must be a positive integer")
        item = session.get(Attendance, attendance_id)
        if item is None:
            abort(404)
        member = _member(session, item.member_id)
        enforce(can_manage_member(member))
        if item.checked_out_at is not None:
            raise ValidationError("Attendance record is not open")
        item.checked_out_at = datetime.now(timezone.utc)
        session.commit()
        return success(_attendance_data(item), "Member checked out")

    @app.get("/api/members/<member_id:int>/attendance")
    @require_auth()
    def member_attendance(member_id: int) -> Any:
        session: Session = request.environ["gym.db"]
        member = _member(session, member_id)
        enforce(can_manage_member(member))
        query = select(Attendance).where(Attendance.member_id == member.id)
        if request.query.get("start_date") is not None or request.query.get("end_date") is not None:
            start, end = _parse_range()
            query = query.where(Attendance.attended_on >= start, Attendance.attended_on <= end)
        records = session.scalars(query.order_by(Attendance.attended_on.desc(), Attendance.id.desc()))
        return success([_attendance_data(item) for item in records], "Member attendance history")

    @app.get("/api/attendance/daily")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def daily_attendance() -> Any:
        session: Session = request.environ["gym.db"]
        attended_on = _date(request.query.get("date"), "date", default=date.today())
        query = select(Attendance).options(joinedload(Attendance.member)).where(Attendance.attended_on == attended_on)
        user = current_user()
        if user.role is UserRole.TRAINER:
            query = query.join(Attendance.member).where(Member.trainer_id == user.trainer.id)
        records = session.scalars(query.order_by(Attendance.id))
        return success([_attendance_data(item) for item in records], "Daily attendance")

    @app.get("/api/attendance")
    @require_auth(UserRole.ADMIN, UserRole.TRAINER)
    def attendance_date_range() -> Any:
        session: Session = request.environ["gym.db"]
        start, end = _parse_range()
        query = select(Attendance).where(Attendance.attended_on >= start, Attendance.attended_on <= end)
        user = current_user()
        if user.role is UserRole.TRAINER:
            query = query.join(Attendance.member).where(Member.trainer_id == user.trainer.id)
        records = session.scalars(query.order_by(Attendance.attended_on.desc(), Attendance.id.desc()))
        return success([_attendance_data(item) for item in records], "Attendance date range")
