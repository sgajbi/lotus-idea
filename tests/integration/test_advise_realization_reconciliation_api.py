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
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    downstream_submission_headers,
    record_conversion_intent,
    seed_approved_candidate,
)
from tests.support.http import managed_test_client


RECORDED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


@dataclass
class OwnerLifecycleClient:
    intent: Any = None

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
