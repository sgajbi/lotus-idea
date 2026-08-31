from __future__ import annotations

from typing import Any

from tests.support.http import ManagedTestClient, managed_test_client

from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    approve_candidate_for_conversion,
    conversion_intent_headers,
    conversion_intent_payload,
    persisted_candidate_id,
    report_evidence_pack_headers,
    report_evidence_pack_payload,
)


def test_report_evidence_pack_api_records_request_without_render_or_archive_authority() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-report-pack-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id="conversion-report-pack-001"),
        headers=conversion_intent_headers("conversion-intent-api-report-pack-001"),
    )
    assert intent.status_code == 200

    response = client.post(
        "/api/v1/conversion-intents/conversion-report-pack-001/report-evidence-packs",
        json=report_evidence_pack_payload(),
        headers=report_evidence_pack_headers("report-evidence-pack-api-001"),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-report-evidence-pack-api"
    payload = response.json()
    evidence_pack = payload["reportEvidencePack"]
    assert evidence_pack["reportEvidencePackId"] == "report-evidence-pack-001"
    assert evidence_pack["conversionIntentId"] == "conversion-report-pack-001"
    assert evidence_pack["candidateId"] == candidate_id
    assert evidence_pack["reportSourceAuthority"] == "lotus-report"
    assert evidence_pack["renderSourceAuthority"] == "lotus-render"
    assert evidence_pack["archiveSourceAuthority"] == "lotus-archive"
    assert evidence_pack["boundary"] == "request_only"
    assert evidence_pack["grantsClientPublicationAuthority"] is False
    assert evidence_pack["createsRenderedOutput"] is False
    assert evidence_pack["createsArchiveRecord"] is False
    assert evidence_pack["sourceSummaries"]
    assert "route" not in evidence_pack["sourceSummaries"][0]
    assert payload["persistence"]["decision"] == "accepted"
    assert payload["persistence"]["lifecycleStatus"] == "converted_to_report"
    assert payload["persistence"]["auditEventType"] == "idea.report_evidence_pack.requested"
    assert payload["durableStorageBacked"] is False
    assert payload["supportedFeaturePromoted"] is False


def _report_evidence_pack_url(conversion_intent_id: str) -> str:
    return f"/api/v1/conversion-intents/{conversion_intent_id}/report-evidence-packs"


def _persist_conversion_intent_for_report_evidence_pack(
    client: ManagedTestClient,
) -> str:
    conversion_intent_id = "conversion-report-pack-invalid-001"
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-report-pack-invalid-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=conversion_intent_id),
        headers=conversion_intent_headers("conversion-intent-api-report-pack-invalid-001"),
    )
    assert intent.status_code == 200

    return conversion_intent_id


def _post_report_evidence_pack(
    client: ManagedTestClient,
    conversion_intent_id: str,
    *,
    report_evidence_pack_id: str,
    idempotency_key: str,
    capabilities: str = "idea.report-evidence-pack.request",
    client_ready_publication_requested: bool = False,
) -> Any:
    return client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=report_evidence_pack_payload(
            report_evidence_pack_id=report_evidence_pack_id,
            client_ready_publication_requested=client_ready_publication_requested,
        ),
        headers=report_evidence_pack_headers(
            idempotency_key,
            capabilities=capabilities,
        ),
    )


def _post_report_evidence_pack_payload(
    client: ManagedTestClient,
    conversion_intent_id: str,
    *,
    payload: dict[str, Any],
    idempotency_key: str,
) -> Any:
    return client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=payload,
        headers=report_evidence_pack_headers(idempotency_key),
    )


def _assert_report_evidence_pack_replays_and_conflicts(
    client: ManagedTestClient, conversion_intent_id: str
) -> None:
    headers = report_evidence_pack_headers("report-evidence-pack-api-replay-001")

    first = client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-001"),
        headers=headers,
    )
    replayed = client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-001"),
        headers=headers,
    )
    conflict = client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-replay-002"),
        headers=headers,
    )
    publication_escalation = client.post(
        _report_evidence_pack_url(conversion_intent_id),
        json=report_evidence_pack_payload(
            report_evidence_pack_id="report-pack-replay-001",
            client_ready_publication_requested=True,
        ),
        headers=headers,
    )

    assert first.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["reportEvidencePack"] == first.json()["reportEvidencePack"]
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert publication_escalation.status_code == 409
    assert publication_escalation.json()["code"] == "idempotency_conflict"


def _assert_report_evidence_pack_blocks_client_ready_publication(
    client: ManagedTestClient, conversion_intent_id: str
) -> None:
    client_ready = _post_report_evidence_pack(
        client,
        conversion_intent_id,
        report_evidence_pack_id="report-pack-client-ready-001",
        idempotency_key="report-evidence-pack-api-client-ready-001",
        client_ready_publication_requested=True,
    )

    assert client_ready.status_code == 409
    assert client_ready.json()["code"] == "report_evidence_pack_conflict"


def _assert_report_evidence_pack_denies_wrong_authority_and_missing_intent(
    client: ManagedTestClient, conversion_intent_id: str
) -> None:
    denied = _post_report_evidence_pack(
        client,
        conversion_intent_id,
        report_evidence_pack_id="report-pack-denied-001",
        idempotency_key="report-evidence-pack-api-denied-001",
        capabilities="idea.review.record",
    )
    missing = client.post(
        "/api/v1/conversion-intents/missing-intent/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-missing-001"),
        headers=report_evidence_pack_headers("report-evidence-pack-api-missing-001"),
    )

    assert denied.status_code == 403
    assert missing.status_code == 404


def _assert_report_evidence_pack_rejects_invalid_request_shapes(
    client: ManagedTestClient, conversion_intent_id: str
) -> None:
    blank_pack_id = _post_report_evidence_pack(
        client,
        conversion_intent_id,
        report_evidence_pack_id=" ",
        idempotency_key="report-evidence-pack-api-blank-001",
    )
    no_reasons_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-no-reasons-001"
    )
    no_reasons_payload["reasonCodes"] = []
    no_reasons = _post_report_evidence_pack_payload(
        client,
        conversion_intent_id,
        payload=no_reasons_payload,
        idempotency_key="report-evidence-pack-api-no-reasons-001",
    )
    blank_retention_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-blank-retention-001"
    )
    blank_retention_payload["retentionPolicyRef"] = " "
    blank_retention = _post_report_evidence_pack_payload(
        client,
        conversion_intent_id,
        payload=blank_retention_payload,
        idempotency_key="report-evidence-pack-api-blank-retention-001",
    )
    unknown_retention_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-unknown-retention-001"
    )
    unknown_retention_payload["retentionPolicyRef"] = "caller:chosen:retention:v1"
    unknown_retention = _post_report_evidence_pack_payload(
        client,
        conversion_intent_id,
        payload=unknown_retention_payload,
        idempotency_key="report-evidence-pack-api-unknown-retention-001",
    )
    naive_time_payload = report_evidence_pack_payload(
        report_evidence_pack_id="report-pack-naive-time-001"
    )
    naive_time_payload["requestedAtUtc"] = "2026-06-21T10:25:00"
    naive_time = _post_report_evidence_pack_payload(
        client,
        conversion_intent_id,
        payload=naive_time_payload,
        idempotency_key="report-evidence-pack-api-naive-time-001",
    )
    blank_idempotency = _post_report_evidence_pack(
        client,
        conversion_intent_id,
        report_evidence_pack_id="report-pack-blank-key-001",
        idempotency_key=" ",
    )

    assert blank_pack_id.status_code == 400
    assert no_reasons.status_code == 400
    assert blank_retention.status_code == 400
    assert unknown_retention.status_code == 400
    assert naive_time.status_code == 400
    assert blank_idempotency.status_code == 400


def test_report_evidence_pack_api_replays_conflicts_and_blocks_client_ready_publication() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    conversion_intent_id = _persist_conversion_intent_for_report_evidence_pack(client)

    _assert_report_evidence_pack_replays_and_conflicts(client, conversion_intent_id)
    _assert_report_evidence_pack_blocks_client_ready_publication(client, conversion_intent_id)
    _assert_report_evidence_pack_denies_wrong_authority_and_missing_intent(
        client, conversion_intent_id
    )
    _assert_report_evidence_pack_rejects_invalid_request_shapes(client, conversion_intent_id)
