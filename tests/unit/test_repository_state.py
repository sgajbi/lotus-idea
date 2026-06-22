from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.domain import InMemoryIdeaRepository
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.runtime import repository_state


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_repository_state_defaults_to_process_local_repository(monkeypatch: Any) -> None:
    monkeypatch.delenv(repository_state.DATABASE_URL_ENV, raising=False)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)

    repository = repository_state.get_idea_repository()

    assert isinstance(repository, InMemoryIdeaRepository)
    assert repository_state.get_idea_repository() is repository
    assert repository_state.idea_repository_durable_storage_backed(repository) is False


def test_repository_state_uses_postgres_repository_when_database_url_is_configured(
    monkeypatch: Any,
) -> None:
    connection = FakeConnection()
    calls: list[dict[str, Any]] = []

    def fake_connect(database_url: str, *, row_factory: object) -> FakeConnection:
        calls.append({"database_url": database_url, "row_factory": row_factory})
        return connection

    monkeypatch.setenv(
        repository_state.DATABASE_URL_ENV,
        "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea",
    )
    monkeypatch.setattr("app.runtime.repository_state.psycopg.connect", fake_connect)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)

    repository = repository_state.get_idea_repository()

    assert isinstance(repository, PostgresIdeaRepository)
    assert repository_state.get_idea_repository() is repository
    assert repository_state.idea_repository_durable_storage_backed(repository) is True
    assert calls == [
        {
            "database_url": "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea",
            "row_factory": dict_row,
        }
    ]


def test_repository_state_reset_closes_configured_connection(monkeypatch: Any) -> None:
    connection = FakeConnection()

    def fake_connect(database_url: str, *, row_factory: object) -> FakeConnection:
        return connection

    monkeypatch.setenv(
        repository_state.DATABASE_URL_ENV,
        "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea",
    )
    monkeypatch.setattr("app.runtime.repository_state.psycopg.connect", fake_connect)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)
    assert isinstance(repository_state.get_idea_repository(), PostgresIdeaRepository)

    repository_state.reset_idea_repository_for_tests()

    assert connection.closed is True
    assert isinstance(repository_state.get_idea_repository(), InMemoryIdeaRepository)
