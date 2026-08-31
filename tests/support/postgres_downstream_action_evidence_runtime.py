from __future__ import annotations

from typing import Any

import psycopg
from tests.support.http import ManagedTestClient

from app.runtime.repository_state import reset_idea_repository_for_tests


_EVIDENCE_SIDE_EFFECT_TABLES = frozenset(
    {
        "idea_audit_event",
        "idea_outbox_event",
    }
)


def assert_postgres_downstream_action_evidence_runtime_proof(
    client: ManagedTestClient,
    candidate_id: str,
    postgres_database_url: str,
) -> None:
    _assert_conversion_outcome_persists_and_replays(client, postgres_database_url)
    _assert_report_evidence_pack_persists_replays_and_rejects_escalation(
        client,
        candidate_id,
        postgres_database_url,
    )


def _assert_conversion_outcome_persists_and_replays(
    client: ManagedTestClient,
    postgres_database_url: str,
) -> None:
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")
    headers = _conversion_outcome_headers()
    payload = _conversion_outcome_payload()
    accepted = client.post(
        "/api/v1/conversion-intents/conversion-report-001/outcomes",
        json=payload,
        headers=headers,
    )

    assert accepted.status_code == 200
    accepted_response = accepted.json()
    assert accepted_response["durableStorageBacked"] is True
    assert accepted_response["persistence"]["decision"] == "accepted"
    _assert_single_side_effect(postgres_database_url, before_audit, before_outbox)

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = client.post(
        "/api/v1/conversion-intents/conversion-report-001/outcomes",
        json=payload,
        headers=headers,
    )

    assert replayed.status_code == 200
    replayed_response = replayed.json()
    assert replayed_response["durableStorageBacked"] is True
    assert replayed_response["persistence"]["decision"] == "replayed"
    assert replayed_response["conversionOutcome"] == accepted_response["conversionOutcome"]
    _assert_single_side_effect(postgres_database_url, before_audit, before_outbox)


def _assert_report_evidence_pack_persists_replays_and_rejects_escalation(
    client: ManagedTestClient,
    candidate_id: str,
    postgres_database_url: str,
) -> None:
    reset_idea_repository_for_tests(reload_from_environment=True)
    headers = _report_evidence_pack_headers()
    payload = _report_evidence_pack_payload()
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")
    accepted = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=payload,
        headers=headers,
    )

    assert accepted.status_code == 200
    accepted_response = accepted.json()
    assert accepted_response["durableStorageBacked"] is True
    assert accepted_response["persistence"]["decision"] == "accepted"
    assert accepted_response["reportEvidencePack"]["candidateId"] == candidate_id
    assert accepted_response["reportEvidencePack"]["createsRenderedOutput"] is False
    assert accepted_response["reportEvidencePack"]["createsArchiveRecord"] is False
    _assert_single_side_effect(postgres_database_url, before_audit, before_outbox)

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=payload,
        headers=headers,
    )

    assert replayed.status_code == 200
    replayed_response = replayed.json()
    assert replayed_response["durableStorageBacked"] is True
    assert replayed_response["persistence"]["decision"] == "replayed"
    assert replayed_response["reportEvidencePack"] == accepted_response["reportEvidencePack"]
    _assert_single_side_effect(postgres_database_url, before_audit, before_outbox)

    publication_escalation = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json={**payload, "clientReadyPublicationRequested": True},
        headers=headers,
    )

    assert publication_escalation.status_code == 409
    assert publication_escalation.json()["code"] == "idempotency_conflict"
    _assert_single_side_effect(postgres_database_url, before_audit, before_outbox)


def _assert_single_side_effect(
    postgres_database_url: str,
    before_audit: int,
    before_outbox: int,
) -> None:
    assert _table_count(postgres_database_url, "idea_audit_event") == before_audit + 1
    assert _table_count(postgres_database_url, "idea_outbox_event") == before_outbox + 1


def _table_count(database_url: str, table_name: str) -> int:
    if table_name not in _EVIDENCE_SIDE_EFFECT_TABLES:
        raise ValueError(f"Unsupported downstream-action evidence table: {table_name}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


def _conversion_outcome_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": "idea.conversion.outcome.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-outcome",
        "X-Trace-Id": "trace-postgres-runtime-proof-conversion-outcome",
        "Idempotency-Key": "postgres-runtime-proof-conversion-outcome-001",
    }


def _report_evidence_pack_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
        "X-Correlation-Id": "corr-postgres-runtime-proof-report-pack",
        "X-Trace-Id": "trace-postgres-runtime-proof-report-pack",
        "Idempotency-Key": "postgres-runtime-proof-report-evidence-pack-001",
    }


def _conversion_outcome_payload() -> dict[str, Any]:
    return {
        "conversionOutcomeId": "conversion-report-outcome-001",
        "sourceEventVersion": 1,
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "downstreamReference": "report-evidence-pack-001",
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def _report_evidence_pack_payload() -> dict[str, Any]:
    return {
        "reportEvidencePackId": "report-evidence-pack-001",
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": False,
    }
