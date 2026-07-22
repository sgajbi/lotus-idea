from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture
from tests.support.http import ManagedTestClient, managed_test_client

import app.api.downstream_realization as downstream_realization_api
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.runtime.downstream_realization_state import (
    ADVISE_BASE_URL_ENV,
    ADVISE_SUBMIT_PATH_ENV,
    MANAGE_BASE_URL_ENV,
    MANAGE_SUBMIT_PATH_ENV,
    REPORT_BASE_URL_ENV,
    REPORT_SUBMIT_PATH_ENV,
    ConversionRealizationClients,
    reset_downstream_realization_clients_for_tests,
)
from app.main import app
from app.ports.downstream_realization import DownstreamRealizationOutcome


def test_downstream_submission_operation_log_includes_request_correlation_id(
    caplog: LogCaptureFixture,
) -> None:
    client = managed_test_client(app)

    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        response = client.post(
            "/api/v1/conversion-intents/conversion-denied/downstream-submissions",
            headers={
                "Idempotency-Key": "downstream-denied-correlation",
                "X-Correlation-Id": "corr-downstream-log",
                "X-Trace-Id": "trace-downstream-log",
            },
        )

    assert response.status_code == 403
    assert response.headers["X-Correlation-Id"] == "corr-downstream-log"
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "idea.operation.downstream_realization_submission"
    assert payload["operation"] == "downstream_realization_submission"
    assert payload["outcome"] == "permission_denied"
    assert payload["correlation_id"] == "corr-downstream-log"
    assert payload["trace_id"] == "trace-downstream-log"
    assert "conversion-denied" not in str(payload)


@dataclass
class CapturingConversionClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[Any, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None

    def submit_proposal_intent(
        self,
        intent: Any,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome

    def submit_action_intent(
        self,
        intent: Any,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome


@dataclass
class CapturingReportClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[Any, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: Any,
        *,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, evidence_pack)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome


def test_conversion_downstream_submission_api_accepts_advise_intent_with_support_reference(
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
        suffix="-advise-downstream",
        idempotency_prefix="advise-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-advise-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-advise-api-001"),
    )

    assert response.status_code == 200
    payload = response.json()
    support_reference = payload["downstreamSubmission"]["supportReference"]
    assert support_reference.startswith("downstream-submission-")
    assert "downstream-submit-advise-api-001" not in support_reference
    assert payload == {
        "downstreamSubmission": {
            "submissionStatus": "accepted_by_downstream",
            "sourceAuthority": "lotus-advise",
            "target": "advise_proposal",
            "downstreamFailureReason": None,
            "supportReference": support_reference,
            "idempotencyReplayed": False,
            "recordsDownstreamOutcome": False,
            "grantsDownstreamAuthority": False,
            "supportedFeaturePromoted": False,
        },
        "durableStorageBacked": False,
        "supportedFeaturePromoted": False,
    }
    assert response.headers["X-Correlation-Id"] == "corr-downstream-submission-api"
    assert response.headers["X-Trace-Id"] == "trace-downstream-submission-api"
    assert advise_client.submitted[0].intent.conversion_intent_id == "conversion-advise-api-001"
    assert advise_client.correlation_id == "corr-downstream-submission-api"
    assert advise_client.trace_id == "trace-downstream-submission-api"
    assert advise_client.idempotency_key == "downstream-submit-advise-api-001"
    assert manage_client.submitted == ()


def test_conversion_downstream_submission_api_replays_same_idempotency_key(
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
        suffix="-advise-downstream-replay",
        idempotency_prefix="advise-downstream-replay",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-replay-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-replay-api-001",
    )

    first = client.post(
        "/api/v1/conversion-intents/conversion-advise-replay-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-advise-replay-api-001"),
    )
    second = client.post(
        "/api/v1/conversion-intents/conversion-advise-replay-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-advise-replay-api-001"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["downstreamSubmission"]["idempotencyReplayed"] is False
    assert second.json()["downstreamSubmission"]["idempotencyReplayed"] is True
    assert len(advise_client.submitted) == 1
    assert manage_client.submitted == ()


def test_conversion_downstream_submission_api_rejects_idempotency_conflict(
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
        suffix="-advise-downstream-conflict",
        idempotency_prefix="advise-downstream-conflict",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-conflict-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-conflict-api-001",
    )
    second_candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-downstream-conflict-second",
        idempotency_prefix="advise-downstream-conflict-second",
    )
    record_conversion_intent(
        client,
        second_candidate_id,
        conversion_intent_id="conversion-advise-conflict-api-002",
        target="advise_proposal",
        idempotency_key="conversion-advise-conflict-api-002",
    )

    first = client.post(
        "/api/v1/conversion-intents/conversion-advise-conflict-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-advise-conflict-api-001"),
    )
    conflict = client.post(
        "/api/v1/conversion-intents/conversion-advise-conflict-api-002/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-advise-conflict-api-001"),
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert len(advise_client.submitted) == 1
    assert manage_client.submitted == ()


def test_report_downstream_submission_api_accepts_pack_with_support_reference(
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
        suffix="-report-downstream",
        idempotency_prefix="report-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-api-001",
        report_evidence_pack_id="report-pack-api-001",
        idempotency_key="report-pack-api-001",
    )

    response = client.post(
        "/api/v1/report-evidence-packs/report-pack-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-api-001"),
    )

    assert response.status_code == 200
    payload = response.json()
    support_reference = payload["downstreamSubmission"]["supportReference"]
    assert support_reference.startswith("downstream-submission-")
    assert "downstream-submit-report-api-001" not in support_reference
    assert payload == {
        "downstreamSubmission": {
            "submissionStatus": "accepted_by_downstream",
            "sourceAuthority": "lotus-report",
            "target": "report_evidence",
            "downstreamFailureReason": None,
            "supportReference": support_reference,
            "idempotencyReplayed": False,
            "recordsDownstreamOutcome": False,
            "grantsDownstreamAuthority": False,
            "supportedFeaturePromoted": False,
        },
        "durableStorageBacked": False,
        "supportedFeaturePromoted": False,
    }
    assert report_client.submitted[0].report_evidence_pack_id == "report-pack-api-001"
    assert report_client.correlation_id == "corr-downstream-submission-api"
    assert report_client.trace_id == "trace-downstream-submission-api"
    assert report_client.idempotency_key == "downstream-submit-report-api-001"


def test_report_downstream_submission_api_replays_same_idempotency_key(
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
        suffix="-report-downstream-replay",
        idempotency_prefix="report-downstream-replay",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-replay-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-replay-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-replay-api-001",
        report_evidence_pack_id="report-pack-replay-api-001",
        idempotency_key="report-pack-replay-api-001",
    )

    first = client.post(
        "/api/v1/report-evidence-packs/report-pack-replay-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-replay-api-001"),
    )
    second = client.post(
        "/api/v1/report-evidence-packs/report-pack-replay-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-replay-api-001"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["downstreamSubmission"]["idempotencyReplayed"] is False
    assert second.json()["downstreamSubmission"]["idempotencyReplayed"] is True
    assert len(report_client.submitted) == 1


def test_report_downstream_submission_api_rejects_idempotency_conflict(
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
        suffix="-report-downstream-conflict",
        idempotency_prefix="report-downstream-conflict",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-conflict-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-conflict-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-conflict-api-001",
        report_evidence_pack_id="report-pack-conflict-api-001",
        idempotency_key="report-pack-conflict-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-conflict-api-001",
        report_evidence_pack_id="report-pack-conflict-api-002",
        idempotency_key="report-pack-conflict-api-002",
    )

    first = client.post(
        "/api/v1/report-evidence-packs/report-pack-conflict-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-conflict-api-001"),
    )
    conflict = client.post(
        "/api/v1/report-evidence-packs/report-pack-conflict-api-002/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-conflict-api-001"),
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert len(report_client.submitted) == 1


def test_downstream_submission_api_fails_closed_without_adapter_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_downstream_realization_clients_for_tests(conversion_clients=None, report_client=None)
    for env_name in (
        ADVISE_BASE_URL_ENV,
        ADVISE_SUBMIT_PATH_ENV,
        MANAGE_BASE_URL_ENV,
        MANAGE_SUBMIT_PATH_ENV,
        REPORT_BASE_URL_ENV,
        REPORT_SUBMIT_PATH_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)
    client = managed_test_client(app)
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-downstream-unconfigured",
        idempotency_prefix="advise-downstream-unconfigured",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-unconfigured-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-unconfigured-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-advise-unconfigured-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-unconfigured-api-001"),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "downstream_realization_not_configured"
    assert response.headers["X-Correlation-Id"] == "corr-downstream-submission-api"


def test_downstream_submission_api_requires_submission_capability() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/conversion-intents/missing-conversion/downstream-submissions",
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Capabilities": "idea.conversion.intent.record",
            "X-Correlation-Id": "corr-downstream-denied-api",
            "Idempotency-Key": "downstream-submit-denied-api-001",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_report_downstream_submission_api_requires_submission_capability() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/report-evidence-packs/missing-pack/downstream-submissions",
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Capabilities": "idea.report-evidence-pack.request",
            "X-Correlation-Id": "corr-report-downstream-denied-api",
            "Idempotency-Key": "report-downstream-submit-denied-api-001",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_downstream_submission_api_rejects_blank_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/conversion-intents/missing-conversion/downstream-submissions",
        headers=downstream_submission_headers(" "),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()


def test_report_downstream_submission_api_rejects_blank_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/report-evidence-packs/missing-pack/downstream-submissions",
        headers=downstream_submission_headers(" "),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert report_client.submitted == ()


def test_conversion_downstream_submission_api_returns_not_found_with_configured_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/conversion-intents/missing-conversion/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-missing-api-001"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "downstream_realization_resource_not_found"
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()


def test_conversion_downstream_submission_api_returns_bounded_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(
        DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected")
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-manage-rejected-downstream",
        idempotency_prefix="manage-rejected-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-manage-rejected-api-001",
        target="manage_review",
        idempotency_key="conversion-manage-rejected-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-manage-rejected-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-manage-rejected-api-001"),
    )

    assert response.status_code == 200
    submission = response.json()["downstreamSubmission"]
    support_reference = submission["supportReference"]
    assert support_reference.startswith("downstream-submission-")
    assert submission == {
        "submissionStatus": "rejected_by_downstream",
        "sourceAuthority": "lotus-manage",
        "target": "manage_review",
        "downstreamFailureReason": "downstream_rejected",
        "supportReference": support_reference,
        "idempotencyReplayed": False,
        "recordsDownstreamOutcome": False,
        "grantsDownstreamAuthority": False,
        "supportedFeaturePromoted": False,
    }
    assert advise_client.submitted == ()
    assert manage_client.submitted[0].intent.conversion_intent_id == (
        "conversion-manage-rejected-api-001"
    )


def test_conversion_downstream_submission_api_returns_durable_uncertain_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(
        DownstreamRealizationOutcome.unknown("downstream_timeout")
    )
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-uncertain-downstream",
        idempotency_prefix="advise-uncertain-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-uncertain-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-uncertain-api-001",
    )
    headers = downstream_submission_headers("downstream-submit-advise-uncertain-api-001")

    first = client.post(
        "/api/v1/conversion-intents/conversion-advise-uncertain-api-001/downstream-submissions",
        headers=headers,
    )
    retry = client.post(
        "/api/v1/conversion-intents/conversion-advise-uncertain-api-001/downstream-submissions",
        headers=headers,
    )

    assert first.status_code == 202
    assert retry.status_code == 202
    first_submission = first.json()["downstreamSubmission"]
    retry_submission = retry.json()["downstreamSubmission"]
    assert first_submission["submissionStatus"] == "reconciliation_required"
    assert first_submission["downstreamFailureReason"] == "downstream_timeout"
    assert first_submission["supportReference"].startswith("downstream-submission-")
    assert retry_submission["supportReference"] == first_submission["supportReference"]
    assert retry_submission["idempotencyReplayed"] is True
    assert len(advise_client.submitted) == 1
    assert manage_client.submitted == ()


def test_conversion_downstream_submission_api_rejects_report_target_on_conversion_route(
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
        suffix="-unsupported-downstream",
        idempotency_prefix="unsupported-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-target-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-target-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-report-target-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-unsupported-api-001"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "unsupported_downstream_realization_target"
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()


def test_report_downstream_submission_api_returns_not_found_with_configured_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/report-evidence-packs/missing-pack/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-missing-report-api-001"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "downstream_realization_resource_not_found"
    assert report_client.submitted == ()


def test_report_downstream_submission_api_returns_bounded_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = CapturingReportClient(
        DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected")
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-report-rejected-downstream",
        idempotency_prefix="report-rejected-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-rejected-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-rejected-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-rejected-api-001",
        report_evidence_pack_id="report-pack-rejected-api-001",
        idempotency_key="report-pack-rejected-api-001",
    )

    response = client.post(
        "/api/v1/report-evidence-packs/report-pack-rejected-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-rejected-api-001"),
    )

    assert response.status_code == 200
    submission = response.json()["downstreamSubmission"]
    support_reference = submission["supportReference"]
    assert support_reference.startswith("downstream-submission-")
    assert submission == {
        "submissionStatus": "rejected_by_downstream",
        "sourceAuthority": "lotus-report",
        "target": "report_evidence",
        "downstreamFailureReason": "downstream_rejected",
        "supportReference": support_reference,
        "idempotencyReplayed": False,
        "recordsDownstreamOutcome": False,
        "grantsDownstreamAuthority": False,
        "supportedFeaturePromoted": False,
    }
    assert report_client.submitted[0].report_evidence_pack_id == "report-pack-rejected-api-001"


def test_report_downstream_submission_api_returns_durable_uncertain_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = CapturingReportClient(
        DownstreamRealizationOutcome.unknown("downstream_unavailable")
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-report-uncertain-downstream",
        idempotency_prefix="report-uncertain-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-uncertain-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-uncertain-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-uncertain-api-001",
        report_evidence_pack_id="report-pack-uncertain-api-001",
        idempotency_key="report-pack-uncertain-api-001",
    )
    headers = downstream_submission_headers("downstream-submit-report-uncertain-api-001")

    first = client.post(
        "/api/v1/report-evidence-packs/report-pack-uncertain-api-001/downstream-submissions",
        headers=headers,
    )
    retry = client.post(
        "/api/v1/report-evidence-packs/report-pack-uncertain-api-001/downstream-submissions",
        headers=headers,
    )

    assert first.status_code == 202
    assert retry.status_code == 202
    first_submission = first.json()["downstreamSubmission"]
    retry_submission = retry.json()["downstreamSubmission"]
    assert first_submission["submissionStatus"] == "reconciliation_required"
    assert first_submission["downstreamFailureReason"] == "downstream_unavailable"
    assert retry_submission["supportReference"] == first_submission["supportReference"]
    assert retry_submission["idempotencyReplayed"] is True
    assert len(report_client.submitted) == 1


def test_report_downstream_submission_api_fails_closed_without_adapter_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_downstream_realization_clients_for_tests(conversion_clients=None, report_client=None)
    monkeypatch.delenv(REPORT_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(REPORT_SUBMIT_PATH_ENV, "/reports/idea-evidence-intake")
    client = managed_test_client(app)
    candidate_id = seed_approved_candidate(
        client,
        suffix="-report-downstream-unconfigured",
        idempotency_prefix="report-downstream-unconfigured",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-unconfigured-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-unconfigured-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-unconfigured-api-001",
        report_evidence_pack_id="report-pack-unconfigured-api-001",
        idempotency_key="report-pack-unconfigured-api-001",
    )

    response = client.post(
        "/api/v1/report-evidence-packs/report-pack-unconfigured-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-unconfigured-api-001"),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "downstream_realization_not_configured"


def test_downstream_submission_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    events: list[tuple[str, str, str, str, bool, str | None]] = []
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )

    def capture_event(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.source_authority,
                event.supportability_status.value,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(downstream_realization_api, "emit_operation_event", capture_event)
    candidate_id = seed_approved_candidate(
        client,
        suffix="-event-downstream",
        idempotency_prefix="event-downstream",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-event-api-001",
        target="advise_proposal",
        idempotency_key="conversion-event-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-event-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-event-api-001"),
    )

    assert response.status_code == 200
    assert events == [
        (
            "downstream_realization_submission",
            "accepted",
            "lotus-idea",
            "not_certified",
            False,
            None,
        )
    ]


def seed_approved_candidate(
    client: ManagedTestClient,
    *,
    suffix: str,
    idempotency_prefix: str,
) -> str:
    persist_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(suffix=suffix),
        headers=persist_headers(f"{idempotency_prefix}-persist-001"),
    )
    assert persist_response.status_code == 200
    candidate_id = str(persist_response.json()["persistence"]["candidateId"])
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transition_response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=lifecycle_payload(
                transition_id=f"{idempotency_prefix}-lifecycle-{target_status}-001",
                target_status=target_status,
                minute=index,
            ),
            headers=lifecycle_headers(f"{idempotency_prefix}-lifecycle-{target_status}-001"),
        )
        assert transition_response.status_code == 200
    review_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(f"{idempotency_prefix}-review-001"),
        headers=review_headers(f"{idempotency_prefix}-review-001"),
    )
    assert review_response.status_code == 200
    return candidate_id


def record_conversion_intent(
    client: ManagedTestClient,
    candidate_id: str,
    *,
    conversion_intent_id: str,
    target: str,
    idempotency_key: str,
) -> None:
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json={
            "conversionIntentId": conversion_intent_id,
            "target": target,
            "reasonCodes": ["review_approved_for_conversion"],
            "requestedAtUtc": "2026-06-21T10:15:00Z",
        },
        headers=conversion_intent_headers(idempotency_key),
    )
    assert response.status_code == 200


def record_report_evidence_pack(
    client: ManagedTestClient,
    *,
    conversion_intent_id: str,
    report_evidence_pack_id: str,
    idempotency_key: str,
) -> None:
    response = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/report-evidence-packs",
        json={
            "reportEvidencePackId": report_evidence_pack_id,
            "purpose": "client_review_report_section",
            "reasonCodes": ["review_approved_for_conversion"],
            "requestedAtUtc": "2026-06-21T10:25:00Z",
            "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
            "clientReadyPublicationRequested": False,
        },
        headers=report_evidence_pack_headers(idempotency_key),
    )
    assert response.status_code == 200


def source_ref(product_id: str, suffix: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}{suffix}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def high_cash_payload(*, suffix: str) -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1", suffix),
            "cashMovementRef": source_ref(
                "lotus-core:PortfolioCashMovementSummary:v1",
                suffix,
            ),
            "cashflowProjectionRef": source_ref(
                "lotus-core:PortfolioCashflowProjection:v1",
                suffix,
            ),
        },
        "entitlementAllowed": True,
        "accessScope": access_scope(),
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-persist-downstream-api",
        "Idempotency-Key": idempotency_key,
    }


def lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "X-Correlation-Id": "corr-lifecycle-downstream-api",
        "Idempotency-Key": idempotency_key,
    }


def review_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-review-downstream-api",
        "Idempotency-Key": idempotency_key,
    }


def conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-conversion-downstream-api",
        "Idempotency-Key": idempotency_key,
    }


def report_evidence_pack_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
        "X-Correlation-Id": "corr-report-downstream-api",
        "Idempotency-Key": idempotency_key,
    }


def downstream_submission_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.downstream-realization.submit",
        "X-Correlation-Id": "corr-downstream-submission-api",
        "X-Trace-Id": "trace-downstream-submission-api",
        "Idempotency-Key": idempotency_key,
    }


def lifecycle_payload(
    *,
    transition_id: str,
    target_status: str,
    minute: int,
) -> dict[str, Any]:
    return {
        "transitionId": transition_id,
        "targetLifecycleStatus": target_status,
        "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
        "reasonCodes": ["review_required"],
    }


def approve_review_payload(review_id: str) -> dict[str, Any]:
    return {
        "reviewId": review_id,
        "action": "approve_for_conversion",
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }
