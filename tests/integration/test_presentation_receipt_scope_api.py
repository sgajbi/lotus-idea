from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.api.runtime_dependencies import get_idea_repository
from app.domain import InMemoryIdeaRepository
from app.main import app
from app.runtime import trusted_clock_state
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_presentation_receipts_api import (
    _candidate,
    _headers,
    _path,
    _payload,
)
from tests.support.fixed_utc_clock import FixedUtcClock
from tests.support.http import managed_test_client
from tests.support.opportunity_effectiveness_fixture import (
    record_fixture,
    snapshot_fixture,
)


@pytest.fixture(autouse=True)
def reset_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trusted_clock_state,
        "_TRUSTED_CLOCK",
        FixedUtcClock(datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC)),
    )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(snapshot_fixture(record_fixture(_candidate())))
    )


@pytest.mark.parametrize(
    ("header_name", "header_value"),
    (
        ("X-Caller-Tenant-Ids", None),
        ("X-Caller-Book-Ids", None),
        ("X-Caller-Portfolio-Ids", None),
        ("X-Caller-Client-Ids", None),
        ("X-Caller-Tenant-Ids", "tenant-other"),
        ("X-Caller-Book-Ids", "book-other"),
        ("X-Caller-Portfolio-Ids", "portfolio-other"),
        ("X-Caller-Client-Ids", "client-other"),
    ),
)
def test_presentation_receipt_api_denies_incomplete_or_mismatched_candidate_scope(
    header_name: str,
    header_value: str | None,
) -> None:
    client = managed_test_client(app)
    repository = get_idea_repository()
    before = repository.snapshot()
    headers = _headers()
    if header_value is None:
        headers.pop(header_name)
    else:
        headers[header_name] = header_value

    response = client.post(_path(), json=_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert repository.snapshot() == before


def test_presentation_receipt_api_refuses_tenant_only_entitlement_before_any_write() -> None:
    client = managed_test_client(app)
    repository = get_idea_repository()
    before = repository.snapshot()
    headers = _headers()
    for header_name in ("X-Caller-Book-Ids", "X-Caller-Portfolio-Ids", "X-Caller-Client-Ids"):
        headers.pop(header_name)

    response = client.post(_path(), json=_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert repository.snapshot() == before


def test_presentation_receipt_api_accepts_plural_and_reordered_grants_with_exact_replay() -> None:
    client = managed_test_client(app)

    accepted = client.post(
        _path(),
        json=_payload(),
        headers=_headers(
            tenant_ids="tenant-other,tenant-a",
            book_ids="book-other,book-001",
            portfolio_ids="portfolio-other,portfolio-001",
            client_ids="client-other,client-001",
        ),
    )
    replayed = client.post(
        _path(),
        json=_payload(),
        headers=_headers(
            tenant_ids="tenant-a,tenant-other",
            book_ids="book-001,book-other",
            portfolio_ids="portfolio-001,portfolio-other",
            client_ids="client-001,client-other",
        ),
    )

    assert accepted.status_code == 201
    assert replayed.status_code == 200
    assert replayed.json()["receipt"] == accepted.json()["receipt"]


def test_presentation_receipt_api_rejects_malformed_scope_without_mutation() -> None:
    client = managed_test_client(app)
    repository = get_idea_repository()
    before = repository.snapshot()
    headers = _headers()
    headers["X-Caller-Book-Ids"] = "book-001,,book-other"

    response = client.post(_path(), json=_payload(), headers=headers)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert repository.snapshot() == before
