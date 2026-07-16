from __future__ import annotations

from typing import Any, Mapping

import pytest
from tests.support.http import managed_test_client

import app.api.data_lifecycle as data_lifecycle_api
from app.main import app


def test_data_lifecycle_api_emits_bounded_permission_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str | None, bool, Mapping[str, str] | None]] = []

    def capture_event(
        operation: Any,
        outcome: Any,
        error_code: str | None = None,
        durable_storage_backed: bool = False,
        attributes: Mapping[str, str] | None = None,
    ) -> None:
        events.append(
            (
                operation.value,
                outcome.value,
                error_code,
                durable_storage_backed,
                attributes,
            )
        )

    monkeypatch.setattr(data_lifecycle_api, "_emit_event", capture_event)
    response = managed_test_client(app).post(
        "/api/v1/data-lifecycle/candidates/candidate-001/actions",
        json={
            "tenantId": "tenant-001",
            "action": "erase",
            "authorityRef": "bank-privacy-governance:decision-001",
            "reason": "approved_lifecycle_request",
            "changeReference": "privacy-case-001",
            "requestedAtUtc": "2026-07-10T09:00:00Z",
            "dryRun": True,
            "approverSubject": "privacy-approver-001",
        },
        headers={"Idempotency-Key": "operation-data-lifecycle-denied-001"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert events == [
        ("data_lifecycle_action", "permission_denied", None, False, None),
    ]
