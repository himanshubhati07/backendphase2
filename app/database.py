"""PostgreSQL pool lifecycle and transactional connection dependency."""
from collections.abc import Generator

from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def initialize_database() -> None:
    """Create the connection pool and idempotent application schema."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=get_settings().database_url, min_size=1, max_size=10, open=True)
    with _pool.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(320) NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL CHECK (length(trim(title)) > 0),
                    description TEXT NOT NULL,
                    priority VARCHAR(10) NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
                    due_date DATE NOT NULL,
                    status VARCHAR(15) NOT NULL CHECK (status IN ('Pending', 'In Progress', 'Completed')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_owner_filters ON tasks(user_id, status, priority);
                CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(user_id, title);
            """)
        connection.commit()


def get_connection() -> Generator[Connection, None, None]:
    """Yield a transactional pooled connection and reliably release it."""
    if _pool is None:
        raise RuntimeError("Database pool has not been initialized")
    with _pool.connection() as connection:
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def close_database() -> None:
    """Close the application pool during shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
