"""Trainer use cases and transaction/error translation."""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation

from app.dtos.trainers import TrainerDTO
from app.errors import ConflictError, NotFoundError
from app.repositories.trainers import TrainerRepository


class TransactionManager(Protocol):
    def transaction(self) -> Any: ...


class TrainerService:
    """Coordinates trainer persistence without coupling HTTP to SQL."""

    def __init__(self, transactions: TransactionManager, repository: TrainerRepository) -> None:
        self._transactions = transactions
        self._repository = repository

    def create(self, payload: dict[str, Any]) -> dict[str, str | None]:
        try:
            with self._transactions.transaction() as connection:
                trainer = self._repository.create(connection, trainer_id=uuid4(), data=payload)
        except UniqueViolation as exc:
            raise ConflictError("A trainer with this email already exists") from exc
        return trainer.to_dict()

    def get(self, trainer_id: UUID) -> dict[str, str | None]:
        with self._transactions.transaction() as connection:
            trainer = self._repository.get(connection, trainer_id)
        return self._require_trainer(trainer, trainer_id).to_dict()

    def update(self, trainer_id: UUID, payload: dict[str, Any]) -> dict[str, str | None]:
        try:
            with self._transactions.transaction() as connection:
                trainer = self._repository.update(connection, trainer_id, data=payload)
        except UniqueViolation as exc:
            raise ConflictError("A trainer with this email already exists") from exc
        return self._require_trainer(trainer, trainer_id).to_dict()

    def delete(self, trainer_id: UUID) -> None:
        with self._transactions.transaction() as connection:
            deleted = self._repository.delete(connection, trainer_id)
        if not deleted:
            raise NotFoundError("Trainer not found")

    def list(self, *, page: int, per_page: int) -> dict[str, Any]:
        with self._transactions.transaction() as connection:
            trainers, total = self._repository.list(connection, page=page, per_page=per_page)
        return {
            "items": [trainer.to_dict() for trainer in trainers],
            "page": page,
            "per_page": per_page,
            "total": total,
        }

    @staticmethod
    def _require_trainer(trainer: TrainerDTO | None, trainer_id: UUID) -> TrainerDTO:
        if trainer is None:
            raise NotFoundError("Trainer not found")
        return trainer
