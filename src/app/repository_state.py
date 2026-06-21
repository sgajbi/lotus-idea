from __future__ import annotations

import os
from typing import cast

import psycopg
from psycopg.rows import dict_row

from app.domain import InMemoryIdeaRepository
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.ports.idea_repository import IdeaRepository

DATABASE_URL_ENV = "LOTUS_IDEA_DATABASE_URL"

_IDEA_REPOSITORY: IdeaRepository | None = None


def get_idea_repository() -> IdeaRepository:
    global _IDEA_REPOSITORY
    if _IDEA_REPOSITORY is None:
        _IDEA_REPOSITORY = _build_idea_repository()
    return _IDEA_REPOSITORY


def idea_repository_durable_storage_backed(repository: object | None = None) -> bool:
    active_repository = repository if repository is not None else get_idea_repository()
    return bool(getattr(active_repository, "durable_storage_backed", False))


def reset_idea_repository_for_tests(
    repository: IdeaRepository | None = None,
    *,
    reload_from_environment: bool = False,
) -> None:
    global _IDEA_REPOSITORY
    _close_repository_if_supported(_IDEA_REPOSITORY)
    if reload_from_environment:
        _IDEA_REPOSITORY = None
        return
    _IDEA_REPOSITORY = repository or InMemoryIdeaRepository()


def _build_idea_repository() -> IdeaRepository:
    database_url = os.getenv(DATABASE_URL_ENV, "").strip()
    if not database_url:
        return InMemoryIdeaRepository()
    connection = psycopg.connect(database_url, row_factory=dict_row)
    return PostgresIdeaRepository(cast(PostgresConnection, connection))


def _close_repository_if_supported(repository: object | None) -> None:
    connection = getattr(repository, "_connection", None)
    close = getattr(connection, "close", None)
    if callable(close):
        close()
