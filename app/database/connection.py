from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any
import psycopg
from psycopg.rows import dict_row


class TransactionManager:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        connection = psycopg.connect(self._database_url, row_factory=dict_row)
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
