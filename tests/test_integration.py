import os
import pytest

pytestmark = pytest.mark.skipif(not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_API_KEY")), reason="TEST_DATABASE_URL and TEST_API_KEY are required for PostgreSQL integration tests")

def test_integration_environment_is_available() -> None:
    assert os.environ["TEST_DATABASE_URL"]
