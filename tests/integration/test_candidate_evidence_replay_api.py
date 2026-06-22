from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.domain import IdeaLifecycleStatus
from app.main import app


def source_ref(product_id: str, *, suffix: str = "", freshness: str = "current") -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}{suffix}",
        "dataQualityStatus": "complete",
        "freshness": freshness,
    }


def current_source_refs(*, suffix: str = "", freshness: str = "current") -> list[dict[str, str]]:
    return [
        source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix=suffix, freshness=freshness),
        source_ref("lotus-core:HoldingsAsOf:v1", suffix=suffix, freshness=freshness),
        source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            suffix=suffix,
            freshness=freshness,
        ),
        source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            suffix=suffix,
            freshness=freshness,
        ),
    ]


def high_cash_payload(*, suffix: str = "") -> dict[str, Any]:
    refs = current_source_refs(suffix=suffix)
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": refs[0],
            "holdingsRef": refs[1],
            "cashMovementRef": refs[2],
            "cashflowProjectionRef": refs[3],
        },
        "entitlementAllowed": True,
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": idempotency_key,
    }


def replay_headers(capabilities: str = "idea.candidate.evidence.replay") -> dict[str, str]:
    return {
        "X-Caller-Subject": "ops-001",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-candidate-evidence-replay-api",
    }


def replay_payload(*, suffix: str = "", freshness: str = "current") -> dict[str, Any]:
    return {
        "evaluatedAtUtc": "2026-06-21T10:30:00Z",
        "currentSourceRefs": current_source_refs(suffix=suffix, freshness=freshness),
    }


def persisted_candidate_id(client: TestClient, *, suffix: str, idempotency_key: str) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(suffix=suffix),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def test_candidate_evidence_replay_api_returns_matched_posture_without_source_payloads() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        suffix="-matched",
        idempotency_key="evidence-replay-matched-001",
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-matched"),
        headers=replay_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-candidate-evidence-replay-api"
    payload = response.json()
    assert payload["candidateId"] == candidate_id
    assert payload["replayStatus"] == "matched"
    assert payload["evidencePacketId"].startswith("iep_high_cash_")
    assert payload["recordedEvidenceHash"].startswith("sha256:")
    assert payload["currentEvidenceHash"] == payload["recordedEvidenceHash"]
    assert payload["sourceRefCount"] == 4
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["grantsDownstreamAuthority"] is False
    assert "route" not in payload
    assert "contentHash" not in payload


def test_candidate_evidence_replay_api_reports_hash_mismatch_and_stale_source() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        suffix="-compare",
        idempotency_key="evidence-replay-compare-001",
    )
    mismatched_payload = replay_payload(suffix="-compare")
    mismatched_payload = deepcopy(mismatched_payload)
    mismatched_payload["currentSourceRefs"][3]["contentHash"] = "sha256:changed-cashflow"

    mismatch = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=mismatched_payload,
        headers=replay_headers(),
    )
    stale = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-compare", freshness="stale"),
        headers=replay_headers(),
    )

    assert mismatch.status_code == 200
    assert mismatch.json()["replayStatus"] == "hash_mismatch"
    assert mismatch.json()["currentEvidenceHash"] != mismatch.json()["recordedEvidenceHash"]
    assert stale.status_code == 200
    assert stale.json()["replayStatus"] == "stale_source"
    assert stale.json()["currentEvidenceHash"] is None


def test_candidate_evidence_replay_api_reports_expired_posture() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        suffix="-expired",
        idempotency_key="evidence-replay-expired-001",
    )
    get_idea_repository().record_lifecycle_transition(
        candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        idempotency_key="evidence-replay-expired-transition-001",
        payload={"target": IdeaLifecycleStatus.EXPIRED.value},
        actor_subject="signal-expiry-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 20, tzinfo=UTC),
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-expired"),
        headers=replay_headers(),
    )

    assert response.status_code == 200
    assert response.json()["replayStatus"] == "expired"
    assert response.json()["currentEvidenceHash"] is None


def test_candidate_evidence_replay_api_requires_operator_permission_and_existing_candidate() -> (
    None
):
    reset_idea_repository_for_tests()
    client = TestClient(app)

    denied = client.post(
        "/api/v1/idea-candidates/missing-candidate/evidence-replay",
        json=replay_payload(),
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Roles": "advisor",
            "X-Caller-Capabilities": "idea.candidate.detail.read",
        },
    )
    missing = client.post(
        "/api/v1/idea-candidates/missing-candidate/evidence-replay",
        json=replay_payload(),
        headers=replay_headers(),
    )

    assert denied.status_code == 403
    assert denied.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to replay idea candidate evidence.",
    }
    assert missing.status_code == 404
    assert missing.json() == {
        "type": "about:blank",
        "status": 404,
        "code": "candidate_not_found",
        "title": "Candidate not found",
        "detail": "The idea candidate was not found for evidence replay.",
    }


def test_candidate_evidence_replay_api_rejects_missing_current_source_refs() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        suffix="-invalid",
        idempotency_key="evidence-replay-invalid-001",
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json={"evaluatedAtUtc": "2026-06-21T10:30:00Z", "currentSourceRefs": []},
        headers=replay_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_candidate_evidence_replay_api_rejects_naive_timestamp_and_blank_candidate() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    naive_timestamp = client.post(
        "/api/v1/idea-candidates/missing-candidate/evidence-replay",
        json={
            "evaluatedAtUtc": "2026-06-21T10:30:00",
            "currentSourceRefs": current_source_refs(),
        },
        headers=replay_headers(),
    )
    blank_candidate = client.post(
        "/api/v1/idea-candidates/%20/evidence-replay",
        json=replay_payload(),
        headers=replay_headers(),
    )

    assert naive_timestamp.status_code == 400
    assert naive_timestamp.json()["code"] == "invalid_request"
    assert blank_candidate.status_code == 400
    assert blank_candidate.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "candidateId and currentSourceRefs are required for evidence replay.",
    }
