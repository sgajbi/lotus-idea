from __future__ import annotations

import pytest

import app.api.downstream_realization as downstream_realization_api
from app.main import app
from app.ports.downstream_realization import DownstreamRealizationOutcome
from app.runtime.downstream_realization_state import ConversionRealizationClients
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    CapturingReportClient,
    downstream_submission_headers,
    record_conversion_intent,
    record_report_evidence_pack,
    seed_approved_candidate,
)
from tests.support.http import managed_test_client


def test_conversion_submission_rejects_new_key_for_same_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-resource-conflict",
        idempotency_prefix="advise-resource-conflict",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-resource-conflict-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-resource-conflict-001",
    )
    url = (
        "/api/v1/conversion-intents/conversion-advise-resource-conflict-001/downstream-submissions"
    )

    first = client.post(url, headers=downstream_submission_headers("submission-key-one"))
    conflict = client.post(url, headers=downstream_submission_headers("submission-key-two"))

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "downstream_submission_resource_conflict"
    assert len(advise_client.submitted) == 1
    assert manage_client.submitted == ()
    _assert_second_key_was_not_persisted("submission-key-two")


def test_report_submission_rejects_new_key_for_same_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-report-resource-conflict",
        idempotency_prefix="report-resource-conflict",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-resource-conflict-001",
        target="report_evidence",
        idempotency_key="conversion-report-resource-conflict-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-resource-conflict-001",
        report_evidence_pack_id="report-pack-resource-conflict-001",
        idempotency_key="report-pack-resource-conflict-001",
    )
    url = "/api/v1/report-evidence-packs/report-pack-resource-conflict-001/downstream-submissions"

    first = client.post(url, headers=downstream_submission_headers("report-key-one"))
    conflict = client.post(url, headers=downstream_submission_headers("report-key-two"))

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "downstream_submission_resource_conflict"
    assert len(report_client.submitted) == 1
    _assert_second_key_was_not_persisted("report-key-two")


def _assert_second_key_was_not_persisted(idempotency_key: str) -> None:
    repository = get_idea_repository()
    assert len(repository.snapshot().downstream_submission_records) == 1
    assert (
        repository.downstream_submission_by_idempotency_key(
            "tenant-private-bank-sg", idempotency_key
        )
        is None
    )
