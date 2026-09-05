from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

import app.api.presentation_receipts as presentation_receipts_api
from app.api.durable_write_guard import durable_repository_not_configured_problem
from app.api.presentation_receipt_models import PresentationReceiptResponse
from app.domain import (
    InMemoryIdeaRepository,
    OpportunityFamily,
    PresentationReceiptDecision,
    PresentationReceiptResult,
)
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.support.http import managed_test_client
from tests.support.opportunity_effectiveness_fixture import (
    candidate_fixture,
    record_fixture,
    snapshot_fixture,
)


class FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now_utc(self) -> datetime:
        return self._instant


def _path() -> str:
    return "/api/v1/idea-candidates/candidate-presentation-001/presentation-receipts"


def _payload() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "presentedAtUtc": "2026-08-30T12:00:00Z",
        "rankAtPresentation": 2,
        "visibleCandidateCount": 7,
        "queueSnapshotDigest": f"sha256:{'a' * 64}",
        "queuePolicyVersion": "idea-review-queue-v1",
        "rankingPolicyVersion": "idea-score-v2",
        "candidateMaterialVersion": 1,
        "candidateEvidenceVersion": 1,
    }


def _headers(
    *,
    roles: str = "advisor",
    capabilities: str = "idea.presentation-receipt.record",
    tenant_ids: str = "tenant-a",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "workbench-visible-render-producer",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Caller-Tenant-Ids": tenant_ids,
        "Idempotency-Key": "receipt-presentation-001",
    }


@pytest.fixture(autouse=True)
def reset_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    accepted_at = datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC)
    monkeypatch.setattr(
        presentation_receipts_api,
        "get_trusted_clock",
        lambda: FixedClock(accepted_at),
    )
    candidate = candidate_fixture(
        "candidate-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id="tenant-a",
    )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(snapshot_fixture(record_fixture(candidate)))
    )


def test_presentation_receipt_api_accepts_and_replays_exact_visible_render_evidence() -> None:
    client = managed_test_client(app)

    accepted = client.post(
        _path(),
        json=_payload(),
        headers=_headers(),
    )
    replayed = client.post(
        _path(),
        json=_payload(),
        headers=_headers(),
    )

    assert accepted.status_code == 201
    assert replayed.status_code == 200
    payload = accepted.json()
    assert payload["receipt"] == {
        "receiptId": "receipt-presentation-001",
        "candidateId": "candidate-presentation-001",
        "tenantId": "tenant-a",
        "presentedAtUtc": "2026-08-30T12:00:00Z",
        "acceptedAtUtc": "2026-08-30T12:00:01Z",
        "acceptanceTimeSource": "server_accepted",
        "rankAtPresentation": 2,
        "visibleCandidateCount": 7,
        "queueSnapshotDigest": f"sha256:{'a' * 64}",
        "queuePolicyVersion": "idea-review-queue-v1",
        "rankingPolicyVersion": "idea-score-v2",
        "candidateMaterialVersion": 1,
        "candidateEvidenceVersion": 1,
        "schemaVersion": "lotus-idea.candidate-presentation-receipt.v1",
        "surface": "advisor_review_queue",
        "producer": "lotus-workbench",
    }
    assert payload["persistenceDecision"] == "accepted"
    assert payload["durableStorageBacked"] is False
    assert payload["effectivenessMeasurementStatus"] == ("stored_consumer_certification_pending")
    assert payload["certificationStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert replayed.json()["persistenceDecision"] == "replayed"


def test_presentation_receipt_api_rejects_changed_idempotent_evidence() -> None:
    client = managed_test_client(app)
    client.post(_path(), json=_payload(), headers=_headers())

    conflict = client.post(
        _path(),
        json={**_payload(), "rankAtPresentation": 3},
        headers=_headers(),
    )

    assert conflict.status_code == 409
    assert conflict.json()["code"] == "presentation_receipt_identity_conflict"
    assert "candidate-presentation-001" not in conflict.text


@pytest.mark.parametrize(
    ("headers", "payload"),
    (
        (_headers(capabilities="idea.review-queue.read"), _payload()),
        (_headers(roles="compliance"), _payload()),
        (_headers(tenant_ids="tenant-b"), _payload()),
        (_headers(), {**_payload(), "tenantId": "tenant-b"}),
    ),
)
def test_presentation_receipt_api_requires_role_capability_and_exact_tenant_scope(
    headers: dict[str, str],
    payload: dict[str, object],
) -> None:
    response = managed_test_client(app).post(_path(), json=payload, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_presentation_receipt_api_does_not_disclose_candidate_outside_entitled_scope() -> None:
    candidate = candidate_fixture(
        "candidate-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 11, tzinfo=UTC),
        tenant_id="tenant-b",
    )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(snapshot_fixture(record_fixture(candidate)))
    )

    response = managed_test_client(app).post(
        _path(),
        json=_payload(),
        headers=_headers(),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert "candidate-presentation-001" not in response.text
    assert "tenant-b" not in response.text


@pytest.mark.parametrize(
    "payload",
    (
        {**_payload(), "candidateMaterialVersion": 2},
        {**_payload(), "candidateEvidenceVersion": 2},
    ),
)
def test_presentation_receipt_api_fails_closed_on_candidate_state_mismatch(
    payload: dict[str, object],
) -> None:
    response = managed_test_client(app).post(
        _path(),
        json=payload,
        headers=_headers(),
    )

    assert response.status_code in {400, 409}
    assert response.json()["code"] in {
        "invalid_request",
        "presentation_receipt_candidate_state_conflict",
    }


def test_presentation_receipt_observed_time_cannot_backdate_server_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted_at = datetime(2026, 8, 30, 11, 0, 1, tzinfo=UTC)
    monkeypatch.setattr(
        presentation_receipts_api,
        "get_trusted_clock",
        lambda: FixedClock(accepted_at),
    )
    response = managed_test_client(app).post(
        _path(),
        json={**_payload(), "presentedAtUtc": "2026-08-30T10:59:59Z"},
        headers=_headers(),
    )

    assert response.status_code == 201
    receipt = response.json()["receipt"]
    assert receipt["presentedAtUtc"] == "2026-08-30T10:59:59Z"
    assert receipt["acceptedAtUtc"] == "2026-08-30T11:00:01Z"


def test_presentation_receipt_api_preserves_global_rank_independently_of_visible_count() -> None:
    response = managed_test_client(app).post(
        _path(),
        json={
            **_payload(),
            "rankAtPresentation": 25,
            "visibleCandidateCount": 1,
        },
        headers={
            **_headers(),
            "Idempotency-Key": "receipt-global-rank-001",
        },
    )

    assert response.status_code == 201
    receipt = response.json()["receipt"]
    assert receipt["rankAtPresentation"] == 25
    assert receipt["visibleCandidateCount"] == 1


@pytest.mark.parametrize(
    "field_name",
    (
        "rankAtPresentation",
        "visibleCandidateCount",
        "candidateMaterialVersion",
        "candidateEvidenceVersion",
    ),
)
@pytest.mark.parametrize("invalid_value", (True, "1"))
def test_presentation_receipt_api_rejects_coerced_integer_evidence(
    field_name: str,
    invalid_value: object,
) -> None:
    response = managed_test_client(app).post(
        _path(),
        json={**_payload(), field_name: invalid_value},
        headers=_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_presentation_receipt_api_returns_not_found_without_creating_evidence() -> None:
    response = managed_test_client(app).post(
        "/api/v1/idea-candidates/candidate-missing/presentation-receipts",
        json=_payload(),
        headers=_headers(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "candidate_not_found"


def test_presentation_receipt_api_emits_only_bounded_operation_event_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        presentation_receipts_api,
        "emit_operation_event",
        lambda event: events.append(event.log_fields()),
    )

    response = managed_test_client(app).post(
        _path(),
        json=_payload(),
        headers=_headers(),
    )

    assert response.status_code == 201
    assert events == [
        {
            "operation": "presentation_receipt_record",
            "outcome": "accepted",
            "source_authority": "lotus-idea",
            "supportability_status": "not_certified",
            "durable_storage_backed": False,
            "supported_feature_promoted": False,
            "visible_candidate_count_bucket": "1-10",
        }
    ]
    assert "candidate-presentation-001" not in str(events)
    assert "tenant-a" not in str(events)


def test_presentation_receipt_api_fails_closed_when_writes_are_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        presentation_receipts_api,
        "durable_write_problem",
        lambda repository: durable_repository_not_configured_problem(),
    )

    response = managed_test_client(app).post(_path(), json=_payload(), headers=_headers())

    assert response.status_code == 503
    assert response.json()["code"] == "durable_repository_not_configured"


def test_presentation_receipt_api_rejects_repository_without_receipt_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(presentation_receipts_api, "durable_write_problem", lambda repository: None)
    monkeypatch.setattr(presentation_receipts_api, "get_idea_repository", object)

    response = managed_test_client(app).post(_path(), json=_payload(), headers=_headers())

    assert response.status_code == 503
    assert response.json()["code"] == "presentation_receipt_unavailable"


def test_presentation_receipt_api_fails_closed_on_repository_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_repository_outage(*args: object, **kwargs: object) -> object:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        InMemoryIdeaRepository,
        "record_presentation_receipt",
        raise_repository_outage,
    )

    response = managed_test_client(app).post(_path(), json=_payload(), headers=_headers())

    assert response.status_code == 503
    assert response.json()["code"] == "presentation_receipt_unavailable"


def test_presentation_receipt_response_rejects_missing_evidence() -> None:
    with pytest.raises(ValueError, match="missing receipt evidence"):
        PresentationReceiptResponse.from_result(
            PresentationReceiptResult(
                decision=PresentationReceiptDecision.ACCEPTED,
                receipt=None,
            ),
            durable_storage_backed=True,
        )
