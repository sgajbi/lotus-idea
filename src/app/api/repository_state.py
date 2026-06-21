from __future__ import annotations

from app.domain import InMemoryIdeaRepository

_IDEA_REPOSITORY = InMemoryIdeaRepository()


def get_idea_repository() -> InMemoryIdeaRepository:
    return _IDEA_REPOSITORY


def reset_idea_repository_for_tests() -> None:
    global _IDEA_REPOSITORY
    _IDEA_REPOSITORY = InMemoryIdeaRepository()
