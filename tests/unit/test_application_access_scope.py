from __future__ import annotations

import pytest

from app.application.access_scope import UNKNOWN_SCOPE_VALUE, portfolio_only_scope


def test_portfolio_only_scope_preserves_portfolio_with_unknown_outer_scope() -> None:
    scope = portfolio_only_scope("portfolio-1")

    assert scope.tenant_id == UNKNOWN_SCOPE_VALUE
    assert scope.book_id == UNKNOWN_SCOPE_VALUE
    assert scope.portfolio_id == "portfolio-1"
    assert scope.client_id == UNKNOWN_SCOPE_VALUE


def test_portfolio_only_scope_rejects_blank_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        portfolio_only_scope(" ")
