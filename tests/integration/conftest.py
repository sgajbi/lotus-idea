from __future__ import annotations

import os
from typing import Iterator

import pytest

from app.infrastructure.migrations import MigrationDirection
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    POSTGRES_REQUIRED_ENV,
    POSTGRES_URL_ENV,
    execute_migrations,
)
from tests.support.http import managed_test_client_scope


@pytest.fixture(autouse=True)
def _close_integration_test_clients() -> Iterator[None]:
    with managed_test_client_scope():
        yield


@pytest.fixture
def postgres_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    database_url = os.getenv(POSTGRES_URL_ENV, "").strip()
    if not database_url:
        if os.getenv(POSTGRES_REQUIRED_ENV) == "1":
            pytest.fail(f"{POSTGRES_URL_ENV} is required for PostgreSQL integration proof")
        pytest.skip(f"{POSTGRES_URL_ENV} is not configured")

    execute_migrations(database_url, MigrationDirection.ROLLBACK)
    execute_migrations(database_url, MigrationDirection.APPLY)
    monkeypatch.setenv("LOTUS_IDEA_DATABASE_URL", database_url)
    reset_idea_repository_for_tests(reload_from_environment=True)
    try:
        yield database_url
    finally:
        reset_idea_repository_for_tests()
        execute_migrations(database_url, MigrationDirection.ROLLBACK)
