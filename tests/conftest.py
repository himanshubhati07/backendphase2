"""Integration-test fixtures using the dedicated PostgreSQL database."""
from __future__ import annotations

import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict


DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _database_name(url: str, variable_name: str) -> str:
    """Read the target database name while rejecting malformed test settings."""
    try:
        database_name = conninfo_to_dict(url).get("dbname")
    except Exception as error:
        raise RuntimeError(f"{variable_name} must be a valid PostgreSQL connection URL") from error
    if not database_name:
        raise RuntimeError(f"{variable_name} must include a PostgreSQL database name")
    return database_name


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set when running integration tests")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must be set when running integration tests; tests never default to the app database"
    )
if TEST_DATABASE_URL == DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL before tests can truncate tables")
if _database_name(TEST_DATABASE_URL, "TEST_DATABASE_URL") == _database_name(DATABASE_URL, "DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must target a database distinct from DATABASE_URL")

# Configure the application pool for the validated dedicated test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def configured_test_database() -> None:
    """Initialize the app schema once, using the explicitly separate test DB."""
    from app.config import get_settings
    from app.database import close_database, initialize_database

    get_settings.cache_clear()
    initialize_database()
    yield
    close_database()


@pytest.fixture
def db_connection(configured_test_database: None):
    """Provide a clean, real PostgreSQL connection for persistence assertions."""
    connection = psycopg.connect(TEST_DATABASE_URL)
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tasks, users RESTART IDENTITY CASCADE")
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tasks, users RESTART IDENTITY CASCADE")
        connection.commit()
        connection.close()


@pytest.fixture
def client(db_connection) -> TestClient:
    """Exercise the actual FastAPI routes and their real dependencies."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient, email: str, password: str = "CorrectHorse1") -> dict[str, str]:
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201, registration.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


@pytest.fixture
def user_headers(client: TestClient) -> dict[str, str]:
    """Authorization headers for the primary isolated test user."""
    return _register_and_login(client, "owner@example.com")


@pytest.fixture
def second_user_headers(client: TestClient, user_headers: dict[str, str]) -> dict[str, str]:
    """Authorization headers for a separate user, used to test ownership."""
    return _register_and_login(client, "other@example.com")
