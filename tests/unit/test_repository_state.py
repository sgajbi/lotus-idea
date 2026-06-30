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
    monkeypatch.delenv("LOTUS_IDEA_RUNTIME_PROFILE", raising=False)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)

    repository = repository_state.get_idea_repository()
    posture = repository_state.idea_repository_runtime_posture(repository)

    assert isinstance(repository, InMemoryIdeaRepository)
    assert repository_state.get_idea_repository() is repository
    assert repository_state.idea_repository_durable_storage_backed(repository) is False
    assert posture.runtime_profile.value == "local"
    assert posture.process_local_repository_allowed is True
    assert posture.write_ready is True


def test_repository_state_allows_test_profile_without_database_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "test")
    monkeypatch.delenv(repository_state.DATABASE_URL_ENV, raising=False)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)

    repository = repository_state.get_idea_repository()
    posture = repository_state.idea_repository_runtime_posture(repository)

    assert isinstance(repository, InMemoryIdeaRepository)
    assert posture.runtime_profile.value == "test"
    assert posture.process_local_repository_allowed is True
    assert posture.write_ready is True


def test_repository_state_marks_production_like_missing_database_as_not_write_ready(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.delenv(repository_state.DATABASE_URL_ENV, raising=False)
    repository_state.reset_idea_repository_for_tests(reload_from_environment=True)

    repository = repository_state.get_idea_repository()
    posture = repository_state.idea_repository_runtime_posture(repository)

    assert isinstance(repository, InMemoryIdeaRepository)
    assert posture.runtime_profile.value == "production"
    assert posture.process_local_repository_allowed is False
    assert posture.durable_write_repository_required is True
    assert posture.write_ready is False
    assert posture.configuration_blockers == ("durable_repository_not_configured",)


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
