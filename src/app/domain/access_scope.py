from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

ScopeFilterValue = str | Iterable[str] | None


def _clean_optional_values(value: ScopeFilterValue) -> tuple[str, ...]:
    if value is None:
        return ()
    values = (value,) if isinstance(value, str) else tuple(value)
    cleaned = tuple(item.strip() for item in values)
    if any(not item for item in cleaned):
        raise ValueError("scope fields cannot be blank")
    return tuple(dict.fromkeys(cleaned))


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


@dataclass(frozen=True, init=False)
class QueueAccessScopeFilter:
    tenant_id: tuple[str, ...]
    book_id: tuple[str, ...]
    portfolio_id: tuple[str, ...]
    client_id: tuple[str, ...]

    def __init__(
        self,
        tenant_id: ScopeFilterValue = None,
        book_id: ScopeFilterValue = None,
        portfolio_id: ScopeFilterValue = None,
        client_id: ScopeFilterValue = None,
    ) -> None:
        object.__setattr__(self, "tenant_id", _clean_optional_values(tenant_id))
        object.__setattr__(self, "book_id", _clean_optional_values(book_id))
        object.__setattr__(self, "portfolio_id", _clean_optional_values(portfolio_id))
        object.__setattr__(self, "client_id", _clean_optional_values(client_id))

    @property
    def is_empty(self) -> bool:
        return all(
            not value for value in (self.tenant_id, self.book_id, self.portfolio_id, self.client_id)
        )

    def is_subset_of(self, entitlement_scope: "QueueAccessScopeFilter") -> bool:
        return (
            self._is_allowed(self.tenant_id, entitlement_scope.tenant_id)
            and self._is_allowed(self.book_id, entitlement_scope.book_id)
            and self._is_allowed(self.portfolio_id, entitlement_scope.portfolio_id)
            and self._is_allowed(self.client_id, entitlement_scope.client_id)
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
    def _matches_field(expected: tuple[str, ...], actual: str) -> bool:
        return not expected or actual in expected

    @staticmethod
    def _is_allowed(requested: tuple[str, ...], allowed: tuple[str, ...]) -> bool:
        return not requested or not allowed or set(requested).issubset(allowed)
