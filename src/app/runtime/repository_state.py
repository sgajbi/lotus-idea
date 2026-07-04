from __future__ import annotations

from typing import cast

import psycopg
from psycopg.rows import dict_row

from app.domain import InMemoryIdeaRepository
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.ports.idea_repository import IdeaRepository
from app.runtime import settings as runtime_settings
from app.runtime.settings import (
    DURABLE_REPOSITORY_UNAVAILABLE,
    LotusIdeaRuntimeSettings,
    RuntimeStoragePosture,
    load_runtime_settings,
    runtime_storage_posture,
)

DATABASE_URL_ENV = runtime_settings.DATABASE_URL_ENV

_IDEA_REPOSITORY: IdeaRepository | None = None
_REPOSITORY_INITIALIZATION_BLOCKER: str | None = None


class UnavailableIdeaRepository:
    durable_storage_backed = False
    _connection = None

    def __getattr__(self, name: str) -> object:
        raise RuntimeError("durable repository is unavailable")


def get_idea_repository() -> IdeaRepository:
    global _IDEA_REPOSITORY
    if _IDEA_REPOSITORY is None:
        _IDEA_REPOSITORY = _build_idea_repository()
    return _IDEA_REPOSITORY


def idea_repository_durable_storage_backed(repository: object | None = None) -> bool:
    active_repository = repository if repository is not None else get_idea_repository()
    return bool(getattr(active_repository, "durable_storage_backed", False))


def idea_repository_runtime_posture(
    repository: object | None = None,
    *,
    settings: LotusIdeaRuntimeSettings | None = None,
) -> RuntimeStoragePosture:
    active_repository = repository if repository is not None else get_idea_repository()
    return runtime_storage_posture(
        settings=settings,
        durable_storage_backed=idea_repository_durable_storage_backed(active_repository),
        durable_repository_initialization_blocker=_REPOSITORY_INITIALIZATION_BLOCKER,
    )


def reset_idea_repository_for_tests(
    repository: IdeaRepository | None = None,
    *,
    reload_from_environment: bool = False,
) -> None:
    global _IDEA_REPOSITORY, _REPOSITORY_INITIALIZATION_BLOCKER
    _close_repository_if_supported(_IDEA_REPOSITORY)
    _REPOSITORY_INITIALIZATION_BLOCKER = None
    if reload_from_environment:
        _IDEA_REPOSITORY = None
        return
    _IDEA_REPOSITORY = repository or InMemoryIdeaRepository()


def _build_idea_repository() -> IdeaRepository:
    global _REPOSITORY_INITIALIZATION_BLOCKER
    settings = load_runtime_settings()
    if settings.database_url is None:
        _REPOSITORY_INITIALIZATION_BLOCKER = None
        return InMemoryIdeaRepository()
    try:
        connection = psycopg.connect(settings.database_url, row_factory=dict_row)
    except (OSError, ValueError, psycopg.Error):
        _REPOSITORY_INITIALIZATION_BLOCKER = DURABLE_REPOSITORY_UNAVAILABLE
        return cast(IdeaRepository, UnavailableIdeaRepository())
    _REPOSITORY_INITIALIZATION_BLOCKER = None
    return PostgresIdeaRepository(cast(PostgresConnection, connection))


def _close_repository_if_supported(repository: object | None) -> None:
    connection = getattr(repository, "_connection", None)
    close = getattr(connection, "close", None)
    if callable(close):
        close()
