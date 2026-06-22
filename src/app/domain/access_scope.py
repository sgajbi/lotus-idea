from __future__ import annotations

from dataclasses import dataclass


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("scope fields cannot be blank")
    return cleaned


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class ReviewAccessScope:
    tenant_id: str
    book_id: str
    portfolio_id: str
    client_id: str

    def __post_init__(self) -> None:
        _require_text(self.tenant_id, "tenant_id")
        _require_text(self.book_id, "book_id")
        _require_text(self.portfolio_id, "portfolio_id")
        _require_text(self.client_id, "client_id")


@dataclass(frozen=True)
class QueueAccessScopeFilter:
    tenant_id: str | None = None
    book_id: str | None = None
    portfolio_id: str | None = None
    client_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _clean_optional(self.tenant_id))
        object.__setattr__(self, "book_id", _clean_optional(self.book_id))
        object.__setattr__(self, "portfolio_id", _clean_optional(self.portfolio_id))
        object.__setattr__(self, "client_id", _clean_optional(self.client_id))

    @property
    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (self.tenant_id, self.book_id, self.portfolio_id, self.client_id)
        )

    def matches(self, access_scope: ReviewAccessScope | None) -> bool:
        if self.is_empty:
            return True
        if access_scope is None:
            return False
        return (
            self._matches_field(self.tenant_id, access_scope.tenant_id)
            and self._matches_field(self.book_id, access_scope.book_id)
            and self._matches_field(self.portfolio_id, access_scope.portfolio_id)
            and self._matches_field(self.client_id, access_scope.client_id)
        )

    @staticmethod
    def _matches_field(expected: str | None, actual: str) -> bool:
        return expected is None or expected == actual
