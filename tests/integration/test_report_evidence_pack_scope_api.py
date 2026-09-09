from __future__ import annotations

import pytest

from app.api.runtime_dependencies import get_idea_repository
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
from tests.support.http import ManagedTestClient, managed_test_client


@pytest.mark.parametrize(
    ("header_name", "header_value"),
    (
        ("X-Caller-Tenant-Ids", None),
        ("X-Caller-Book-Ids", None),
        ("X-Caller-Portfolio-Ids", None),
        ("X-Caller-Client-Ids", None),
        ("X-Caller-Tenant-Ids", "tenant-private-bank-hk"),
        ("X-Caller-Book-Ids", "book-other"),
        ("X-Caller-Portfolio-Ids", "portfolio-other"),
        ("X-Caller-Client-Ids", "client-other"),
    ),
)
def test_report_evidence_pack_api_denies_incomplete_or_mismatched_candidate_scope(
    header_name: str,
    header_value: str | None,
) -> None:
    client = managed_test_client(app)
    intent_id = _seed_report_ready_intent(client, suffix="denial")
    repository = get_idea_repository()
    before = repository.snapshot()
    headers = report_evidence_pack_headers("report-pack-scope-denial")
    if header_value is None:
        headers.pop(header_name)
    else:
        headers[header_name] = header_value

    response = client.post(
        f"/api/v1/conversion-intents/{intent_id}/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-scope-denial"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert repository.snapshot() == before


def test_report_evidence_pack_api_accepts_matching_multi_value_scope_and_replay() -> None:
    client = managed_test_client(app)
    intent_id = _seed_report_ready_intent(client, suffix="multi")
    headers = report_evidence_pack_headers("report-pack-multi-scope")
    headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-private-bank-hk,tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-other,book-advisor-001",
            "X-Caller-Portfolio-Ids": "portfolio-other,PB_SG_GLOBAL_BAL_001",
            "X-Caller-Client-Ids": "client-other,client-001",
        }
    )
    payload = report_evidence_pack_payload(report_evidence_pack_id="report-pack-multi-scope")

    accepted = client.post(
        f"/api/v1/conversion-intents/{intent_id}/report-evidence-packs",
        json=payload,
        headers=headers,
    )
    replayed = client.post(
        f"/api/v1/conversion-intents/{intent_id}/report-evidence-packs",
        json=payload,
        headers=headers,
    )

    assert accepted.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["reportEvidencePack"] == accepted.json()["reportEvidencePack"]
    assert replayed.json()["persistence"]["decision"] == "replayed"


def test_report_evidence_pack_api_rejects_malformed_scope_without_mutation() -> None:
    client = managed_test_client(app)
    intent_id = _seed_report_ready_intent(client, suffix="malformed")
    repository = get_idea_repository()
    before = repository.snapshot()
    headers = report_evidence_pack_headers("report-pack-malformed-scope")
    headers["X-Caller-Tenant-Ids"] = "tenant-private-bank-sg,,tenant-other"

    response = client.post(
        f"/api/v1/conversion-intents/{intent_id}/report-evidence-packs",
        json=report_evidence_pack_payload(report_evidence_pack_id="report-pack-malformed-scope"),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert repository.snapshot() == before


def _seed_report_ready_intent(client: ManagedTestClient, *, suffix: str) -> str:
    reset_idea_repository_for_tests()
    candidate_id = persisted_candidate_id(client, idempotency_key=f"seed-report-scope-{suffix}")
    approve_candidate_for_conversion(client, candidate_id)
    intent_id = f"conversion-report-scope-{suffix}"
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=intent_id),
        headers=conversion_intent_headers(f"intent-report-scope-{suffix}"),
    )
    assert response.status_code == 200
    return intent_id
