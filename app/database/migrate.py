from __future__ import annotations
from pathlib import Path
import logging
from app.database.connection import TransactionManager
from app.settings import Settings
logger=logging.getLogger(__name__)
def run() -> None:
    manager=TransactionManager(Settings.from_environment().database_url)
    with manager.transaction() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
            for path in sorted(Path("migrations").glob("*.sql")):
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version=%s",(path.name,))
                if cursor.fetchone() is None:
                    cursor.execute(path.read_text())
                    cursor.execute("INSERT INTO schema_migrations(version) VALUES(%s)",(path.name,)); logger.info("Applied migration %s",path.name)
if __name__ == "__main__": run()
