from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

PersistedAction = TypeVar("PersistedAction")


class PersistedActionEvidenceUnavailable(RuntimeError):
    """Raised when a successful mutation cannot return one exact persisted action."""


def require_single_persisted_action(
    matches: Iterable[PersistedAction],
) -> PersistedAction:
    persisted_actions = tuple(matches)
    if len(persisted_actions) != 1:
        raise PersistedActionEvidenceUnavailable(
            "Successful mutation did not resolve exactly one persisted action"
        )
    return persisted_actions[0]


__all__ = [
    "PersistedActionEvidenceUnavailable",
    "require_single_persisted_action",
]
