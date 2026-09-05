from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import app.api.advise_realization_reconciliation as reconciliation_api
import app.api.downstream_realization as downstream_realization_api
from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    SourceSystem,
)
from app.main import app
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationOutcome,
)
from app.runtime.downstream_realization_state import ConversionRealizationClients
from app.runtime.downstream_realization_state import DownstreamRealizationClientsUnavailableError
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    downstream_submission_headers,
    record_conversion_intent,
    seed_approved_candidate,
)
from tests.support.fixed_utc_clock import FixedUtcClock
from tests.support.http import managed_test_client


RECORDED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


@dataclass
class OwnerLifecycleClient:
    intent: Any = None
    submission_calls: int = 0
    recovery_calls: int = 0

    def submit_proposal_intent(
        self,
        intent: Any,
        *,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.intent = intent
        self.submission_calls += 1
        return DownstreamRealizationOutcome.accepted_by_downstream(
            DownstreamOwnerReceipt(
                owner_authority=SourceSystem.LOTUS_ADVISE,
                owner_request_id="ipi_api_001",
                owner_realization_id="ipr_api_001",
                owner_work_id="iarw_api_001",
                source_event_version=1,
                source_evidence_fingerprint=intent.evidence_content_hash,
            )
        )

    def load_proposal_realization(
        self,
        *,
        intake_id: str,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AdviseProposalRealizationHistory:
        assert intake_id == "ipi_api_001"
        assert self.intent is not None
        linked_at = RECORDED_AT + timedelta(minutes=1)
        return AdviseProposalRealizationHistory(
            realization_id="ipr_api_001",
            intake_id="ipi_api_001",
            review_work_id="iarw_api_001",
            review_work_status=AdviseProposalReviewWorkStatus.PROPOSAL_LINKED,
            source_authority="lotus-idea",
            realization_authority="lotus-advise",
            tenant_id=access_scope.tenant_id,
            legal_entity_code="SGPB",
            portfolio_id=access_scope.portfolio_id,
            idea_candidate_id=self.intent.intent.candidate_id,
            conversion_intent_id=self.intent.intent.conversion_intent_id,
            source_evidence_fingerprint=self.intent.evidence_content_hash,
            current_status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
            current_source_event_version=2,
            proposal_id="proposal-api-001",
            proposal_record_created=True,
            suitability_authority_granted=False,
            order_created=False,
            client_publication_authorized=False,
            created_at_utc=RECORDED_AT,
            updated_at_utc=linked_at,
            outcomes=(
                AdviseProposalRealizationOutcome(
                    outcome_id="ipro_api_001",
                    source_event_version=1,
                    status=AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW,
                    reason_code="idea_intake_accepted_for_adviser_review",
                    occurred_at_utc=RECORDED_AT,
                    review_work_id="iarw_api_001",
                    proposal_id=None,
                    terminal=False,
                ),
                AdviseProposalRealizationOutcome(
                    outcome_id="ipro_api_002",
                    source_event_version=2,
                    status=AdviseProposalRealizationStatus.PROPOSAL_LINKED,
                    reason_code="advise_proposal_linked",
                    occurred_at_utc=linked_at,
                    review_work_id="iarw_api_001",
                    proposal_id="proposal-api-001",
                    terminal=False,
                ),
            ),
        )

    def load_proposal_realization_by_conversion_intent(
        self,
        *,
        conversion_intent_id: str,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AdviseProposalRealizationHistory:
        self.recovery_calls += 1
        assert conversion_intent_id == self.intent.intent.conversion_intent_id
        return self.load_proposal_realization(
            intake_id="ipi_api_001",
            access_scope=access_scope,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


@dataclass
class LostResponseOwnerLifecycleClient(OwnerLifecycleClient):
    submission_calls: int = 0

    def submit_proposal_intent(
        self,
        intent: Any,
        *,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.intent = intent
        self.submission_calls += 1
        raise TimeoutError("response lost after Advise committed")


def test_advise_realization_reconciliation_api_persists_exact_owner_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = OwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=advise_client,
        manage_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-owner-reconciliation",
        idempotency_prefix="advise-owner-reconciliation",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-owner-api-001",
        target="advise_proposal",
        idempotency_key="conversion-advise-owner-api-001",
    )
    submitted = client.post(
        "/api/v1/conversion-intents/conversion-advise-owner-api-001/downstream-submissions",
        headers=downstream_submission_headers("submission-advise-owner-api-001"),
    )
    support_reference = submitted.json()["downstreamSubmission"]["supportReference"]

    response = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )
    replay = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert submitted.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["reconciliationStatus"] == "accepted"
    assert payload["appendedOutcomeCount"] == 2
    assert payload["history"]["currentStatus"] == "PROPOSAL_LINKED"
    assert payload["history"]["proposalId"] == "proposal-api-001"
    assert payload["history"]["suitabilityAuthorityGranted"] is False
    assert payload["history"]["orderCreated"] is False
    assert payload["history"]["clientPublicationAuthorized"] is False
    assert payload["grantsExecutionAuthority"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert replay.status_code == 200
    assert replay.json()["reconciliationStatus"] == "replayed"
    assert replay.json()["appendedOutcomeCount"] == 0

    denied_headers = _reconciliation_headers()
    denied_headers["X-Caller-Portfolio-Ids"] = "PB_OTHER"
    denied = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=denied_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"


def test_advise_reconciliation_api_recovers_lost_owner_response_without_resubmission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = LostResponseOwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=advise_client,
        manage_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-lost-response",
        idempotency_prefix="advise-lost-response",
    )
    conversion_intent_id = "conversion-advise-lost-response-001"
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id=conversion_intent_id,
        target="advise_proposal",
        idempotency_key=conversion_intent_id,
    )
    submitted = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions",
        headers=downstream_submission_headers("submission-advise-lost-response-001"),
    )
    support_reference = submitted.json()["downstreamSubmission"]["supportReference"]

    recovered = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )
    replayed = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert submitted.status_code == 202
    assert submitted.json()["downstreamSubmission"]["submissionStatus"] == "reconciliation_required"
    assert recovered.status_code == 200
    assert recovered.json()["reconciliationStatus"] == "accepted"
    assert recovered.json()["history"]["intakeId"] == "ipi_api_001"
    assert recovered.json()["appendedOutcomeCount"] == 2
    assert replayed.status_code == 200
    assert replayed.json()["reconciliationStatus"] == "replayed"
    assert advise_client.submission_calls == 1
    assert advise_client.recovery_calls == 1


def test_advise_recovery_api_waits_for_expired_lease_after_local_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = OwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=advise_client,
        manage_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    monkeypatch.setattr(
        reconciliation_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-finalize-failure",
        idempotency_prefix="advise-finalize-failure",
    )
    conversion_intent_id = "conversion-advise-finalize-failure-001"
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id=conversion_intent_id,
        target="advise_proposal",
        idempotency_key=conversion_intent_id,
    )
    repository = get_idea_repository()

    def fail_finalize(**_: object) -> None:
        raise RuntimeError("simulated Idea commit failure after Advise acceptance")

    monkeypatch.setattr(repository, "finalize_downstream_submission", fail_finalize)
    submitted = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions",
        headers=downstream_submission_headers("submission-advise-finalize-failure-001"),
    )
    assert submitted.status_code == 202
    payload = submitted.json()["downstreamSubmission"]
    assert payload["submissionStatus"] == "reconciliation_required"
    support_reference = str(payload["supportReference"])
    persisted = repository.downstream_submission_by_support_reference(support_reference)
    assert persisted is not None
    assert persisted.status.value == "in_flight"
    assert persisted.lease_expires_at_utc is not None

    monkeypatch.setattr(
        reconciliation_api,
        "get_trusted_clock",
        lambda: FixedUtcClock(persisted.lease_expires_at_utc - timedelta(seconds=1)),
    )
    active = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )
    assert active.status_code == 409
    assert active.json()["code"] == "advise_realization_submission_still_in_flight"
    assert advise_client.recovery_calls == 0

    monkeypatch.setattr(
        reconciliation_api,
        "get_trusted_clock",
        lambda: FixedUtcClock(persisted.lease_expires_at_utc),
    )
    recovered = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )
    replayed = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert recovered.status_code == 200
    assert recovered.json()["reconciliationStatus"] == "accepted"
    assert replayed.status_code == 200
    assert replayed.json()["reconciliationStatus"] == "replayed"
    assert advise_client.submission_calls == 1
    assert advise_client.recovery_calls == 1
    final_record = repository.downstream_submission_by_support_reference(support_reference)
    assert final_record is not None
    assert final_record.status.value == "accepted_by_downstream"
    assert final_record.attempt_count == 1
    assert [entry.action.value for entry in final_record.audit_history] == [
        "claimed",
        "reconciled",
    ]


def test_advise_realization_reconciliation_api_reports_unconfigured_owner_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = OwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=advise_client,
        manage_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-advise-owner-unconfigured",
        idempotency_prefix="advise-owner-unconfigured",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-advise-owner-api-002",
        target="advise_proposal",
        idempotency_key="conversion-advise-owner-api-002",
    )
    submitted = client.post(
        "/api/v1/conversion-intents/conversion-advise-owner-api-002/downstream-submissions",
        headers=downstream_submission_headers("submission-advise-owner-api-002"),
    )
    support_reference = submitted.json()["downstreamSubmission"]["supportReference"]
    monkeypatch.setattr(
        reconciliation_api,
        "get_conversion_realization_clients",
        lambda: _raise_unconfigured_owner_reader(),
    )

    response = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/advise-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "advise_realization_reader_not_configured"


def test_advise_realization_reconciliation_api_denial_emits_operation_event(
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
        "advise-realization-reconciliation",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert events == [
        ("downstream_reconciliation_resolve", "permission_denied", "permission_denied")
    ]


def _reconciliation_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.downstream-realization.reconcile",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-advise-owner-reconciliation",
        "X-Trace-Id": "trace-advise-owner-reconciliation",
    }


def _raise_unconfigured_owner_reader() -> None:
    raise DownstreamRealizationClientsUnavailableError("Advise reader is not configured")
