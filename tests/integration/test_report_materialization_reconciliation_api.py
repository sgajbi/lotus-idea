from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import pytest

import app.api.downstream_realization as downstream_realization_api
import app.api.report_materialization_reconciliation as reconciliation_api
from app.domain import GovernedReportEvidencePack
from app.main import app
from app.ports.downstream_realization import DownstreamOwnerReceipt, DownstreamRealizationOutcome
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    downstream_submission_headers,
    record_conversion_intent,
    record_report_evidence_pack,
    seed_approved_candidate,
)
from tests.support.http import managed_test_client
from tests.support.report_materialization import authoritative_report_outcome


@dataclass
class LostResponseReportClient:
    evidence_pack: GovernedReportEvidencePack | None = None
    submission_calls: int = 0
    recovery_calls: int = 0
    contradictory_candidate: bool = False

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.evidence_pack = evidence_pack
        self.submission_calls += 1
        raise TimeoutError("Report committed but its response was lost")

    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        self.recovery_calls += 1
        assert self.evidence_pack == evidence_pack
        assert access_scope.tenant_id == "tenant-private-bank-sg"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        assert idempotency_key == "downstream-submit-report-recovery-api-001"
        receipt = authoritative_report_outcome(evidence_pack).owner_receipt
        assert receipt is not None
        if not self.contradictory_candidate:
            return receipt
        assert receipt.report_materialization is not None
        return replace(
            receipt,
            report_materialization=replace(
                receipt.report_materialization,
                candidate_id="candidate-contradiction",
            ),
        )


def test_report_recovery_api_closes_lost_response_without_second_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = LostResponseReportClient()
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    support_reference = _create_uncertain_report_submission(client)

    response = client.post(
        _recovery_path(support_reference),
        headers=_reconciliation_headers(),
    )
    replay = client.post(
        _recovery_path(support_reference),
        headers=_reconciliation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reconciliationStatus"] == "accepted"
    assert payload["ownerReceipt"]["ownerAuthority"] == "lotus-report"
    assert report_client.evidence_pack is not None
    assert (
        payload["ownerReceipt"]["reportMaterialization"]["candidateId"]
        == report_client.evidence_pack.candidate_id
    )
    assert payload["ownerReceipt"]["reportMaterialization"]["createsReportJob"] is True
    assert payload["grantsClientPublicationAuthority"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert replay.status_code == 200
    assert replay.json() == {
        **payload,
        "reconciliationStatus": "replayed",
    }
    assert report_client.submission_calls == 1
    assert report_client.recovery_calls == 1
    persisted = get_idea_repository().downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status.value == "accepted_by_downstream"
    assert persisted.owner_receipt is not None


def test_report_recovery_api_rejects_contradictory_receipt_without_state_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = LostResponseReportClient(contradictory_candidate=True)
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    support_reference = _create_uncertain_report_submission(client)

    response = client.post(
        _recovery_path(support_reference),
        headers=_reconciliation_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "report_materialization_receipt_invalid"
    persisted = get_idea_repository().downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status.value == "reconciliation_required"
    assert persisted.owner_receipt is None
    assert len(persisted.audit_history) == 2
    assert report_client.submission_calls == 1
    assert report_client.recovery_calls == 1


def test_report_recovery_api_denies_scope_before_owner_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    report_client = LostResponseReportClient()
    monkeypatch.setattr(
        downstream_realization_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_report_evidence_pack_realization_client",
        lambda: report_client,
    )
    support_reference = _create_uncertain_report_submission(client)
    headers = _reconciliation_headers()
    headers["X-Caller-Portfolio-Ids"] = "PB_OTHER"

    response = client.post(_recovery_path(support_reference), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert report_client.submission_calls == 1
    assert report_client.recovery_calls == 0


def test_report_recovery_openapi_publishes_named_failure_modes() -> None:
    operation = app.openapi()["paths"][
        "/api/v1/downstream-submissions/{supportReference}/report-materialization-reconciliation"
    ]["post"]

    assert operation["operationId"] == "reconcileIdeaReportMaterializationReceipt"
    assert set(operation["responses"]) >= {"200", "403", "404", "409", "503"}
    assert operation["security"] == [{"LotusCallerContext": []}]
    assert operation["x-lotus-caller-context"]["requiredCapabilities"] == [
        "idea.downstream-realization.reconcile"
    ]
    example = operation["responses"]["200"]["content"]["application/json"]["example"]
    assert example["grantsClientPublicationAuthority"] is False
    assert example["supportedFeaturePromoted"] is False


def test_report_recovery_api_denial_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str | None]] = []
    import app.api.realization_reconciliation_common as reconciliation_common

    monkeypatch.setattr(
        reconciliation_common,
        "emit_api_foundation_operation_event",
        lambda operation, outcome, error_code: events.append(
            (operation.value, outcome.value, error_code)
        ),
    )
    client = managed_test_client(app)
    headers = _reconciliation_headers()
    headers["X-Caller-Capabilities"] = "idea.downstream-realization.submit"

    response = client.post(
        "/api/v1/downstream-submissions/downstream-submission-0123456789abcdef01234567/"
        "report-materialization-reconciliation",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert events == [
        ("downstream_reconciliation_resolve", "permission_denied", "permission_denied")
    ]


def _create_uncertain_report_submission(client: Any) -> str:
    candidate_id = seed_approved_candidate(
        client,
        suffix="-report-recovery",
        idempotency_prefix="report-recovery",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-report-recovery-api-001",
        target="report_evidence",
        idempotency_key="conversion-report-recovery-api-001",
    )
    record_report_evidence_pack(
        client,
        conversion_intent_id="conversion-report-recovery-api-001",
        report_evidence_pack_id="report-pack-recovery-api-001",
        idempotency_key="report-pack-recovery-api-001",
    )
    submitted = client.post(
        "/api/v1/report-evidence-packs/report-pack-recovery-api-001/downstream-submissions",
        headers=downstream_submission_headers("downstream-submit-report-recovery-api-001"),
    )
    assert submitted.status_code == 202
    payload = submitted.json()["downstreamSubmission"]
    assert payload["submissionStatus"] == "reconciliation_required"
    return str(payload["supportReference"])


def _recovery_path(support_reference: str) -> str:
    return (
        f"/api/v1/downstream-submissions/{support_reference}/report-materialization-reconciliation"
    )


def _reconciliation_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "operator-001",
        "X-Caller-Capabilities": "idea.downstream-realization.reconcile",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-report-owner-recovery",
        "X-Trace-Id": "trace-report-owner-recovery",
    }
