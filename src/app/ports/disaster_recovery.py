from __future__ import annotations

from typing import Protocol

from app.domain.disaster_recovery import RestoredDatabaseSnapshot


class RestoredDatabaseInspector(Protocol):
    def inspect(self, *, expected_tables: frozenset[str]) -> RestoredDatabaseSnapshot: ...
