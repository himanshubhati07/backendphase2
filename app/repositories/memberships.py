"""PostgreSQL persistence for membership plans and membership lifecycles.

All statements intentionally use psycopg's ``%s`` placeholders.  Connections are
provided by the transaction manager; this repository never commits a transaction.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID


class MembershipRepository:
    """Repository scoped to a caller-owned psycopg connection."""

    @staticmethod
    def _one(cursor: Any) -> dict[str, Any] | None:
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(zip((column.name for column in cursor.description), row, strict=True))

    def create_plan(
        self,
        connection: Any,
        *,
        plan_id: UUID,
        name: str,
        description: str | None,
        duration_days: int,
        price: Decimal,
        is_active: bool,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO membership_plans
                    (id, name, description, duration_days, price, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, duration_days, price, is_active,
                          created_at, updated_at
                """,
                (plan_id, name, description, duration_days, price, is_active),
            )
            return self._one(cursor)  # type: ignore[return-value]

    def get_plan(self, connection: Any, plan_id: UUID, *, active_only: bool = False) -> dict[str, Any] | None:
        query = """
            SELECT id, name, description, duration_days, price, is_active, created_at, updated_at
            FROM membership_plans
            WHERE id = %s
        """
        if active_only:
            query += " AND is_active = TRUE"
        with connection.cursor() as cursor:
            cursor.execute(query, (plan_id,))
            return self._one(cursor)

    def get_member(self, connection: Any, member_id: UUID, *, lock: bool = False) -> dict[str, Any] | None:
        query = "SELECT id FROM members WHERE id = %s"
        if lock:
            query += " FOR UPDATE"
        with connection.cursor() as cursor:
            cursor.execute(query, (member_id,))
            return self._one(cursor)

    def find_active_for_member(self, connection: Any, member_id: UUID) -> dict[str, Any] | None:
        # Assignment locks its member row first, serializing this check for a
        # member even when there is not yet an active membership row to lock.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM memberships
                WHERE member_id = %s AND status = 'active'
                FOR UPDATE
                """,
                (member_id,),
            )
            return self._one(cursor)

    def create_membership(
        self,
        connection: Any,
        *,
        membership_id: UUID,
        member_id: UUID,
        plan_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO memberships
                    (id, member_id, plan_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
                RETURNING id, member_id, plan_id, start_date, end_date,
                          status, cancelled_at, created_at, updated_at
                """,
                (membership_id, member_id, plan_id, start_date, end_date),
            )
            return self._one(cursor)  # type: ignore[return-value]

    def get_membership(self, connection: Any, membership_id: UUID, *, lock: bool = False) -> dict[str, Any] | None:
        query = """
            SELECT id, member_id, plan_id, start_date, end_date, status,
                   cancelled_at, created_at, updated_at
            FROM memberships WHERE id = %s
        """
        if lock:
            query += " FOR UPDATE"
        with connection.cursor() as cursor:
            cursor.execute(query, (membership_id,))
            return self._one(cursor)

    def update_active_membership(
        self,
        connection: Any,
        *,
        membership_id: UUID,
        plan_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE memberships
                SET plan_id = %s, start_date = %s, end_date = %s, updated_at = NOW()
                WHERE id = %s AND status = 'active'
                RETURNING id, member_id, plan_id, start_date, end_date,
                          status, cancelled_at, created_at, updated_at
                """,
                (plan_id, start_date, end_date, membership_id),
            )
            return self._one(cursor)

    def cancel_membership(self, connection: Any, *, membership_id: UUID) -> dict[str, Any] | None:
        # A cancellation is a state transition, not a delete, so history remains
        # available to reporting and prevents a second cancellation event.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE memberships
                SET status = 'cancelled', cancelled_at = NOW(), updated_at = NOW()
                WHERE id = %s AND status = 'active'
                RETURNING id, member_id, plan_id, start_date, end_date,
                          status, cancelled_at, created_at, updated_at
                """,
                (membership_id,),
            )
            return self._one(cursor)
