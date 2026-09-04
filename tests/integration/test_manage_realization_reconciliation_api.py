from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import app.api.manage_realization_reconciliation as reconciliation_api
import app.api.downstream_realization as downstream_realization_api
from app.domain import (
    ManageActionRealizationEvent,
    ManageActionRealizationEventType,
    ManageActionRealizationHistory,
    ManageActionRealizationStatus,
    SourceSystem,
)
from app.main import app
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationOutcome,
)
from app.runtime.downstream_realization_state import ConversionRealizationClients
from app.runtime.downstream_realization_state import DownstreamRealizationClientsUnavailableError
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    downstream_submission_headers,
    record_conversion_intent,
    seed_approved_candidate,
)
from tests.support.http import managed_test_client


RECORDED_AT = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


@dataclass
class OwnerLifecycleClient:
    """Plays lotus-manage end to end: accepts the intake with the shipped
    receipt shape, then serves the exact owner outcome history - including
    the reopened review the owner machine permits."""

    intent: Any = None

    def submit_action_intent(
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
                owner_authority=SourceSystem.LOTUS_MANAGE,
                owner_request_id="iai_api_001",
                owner_realization_id="ima_api_001",
                owner_work_id="ima_api_001",
                source_event_version=1,
                source_evidence_fingerprint="sha256:aabbccddeeff",
            )
        )

    def load_action_realization(
        self,
        *,
        intake_id: str,
        access_scope: Any,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> ManageActionRealizationHistory:
        assert intake_id == "iai_api_001"
        assert self.intent is not None
        events = (
            _owner_event(
                version=1,
                event_type=ManageActionRealizationEventType.INTAKE_ACCEPTED,
                previous_status=None,
                status=ManageActionRealizationStatus.PENDING_REVIEW,
                actor_role="SERVICE",
                reason_code="idea_conversion_intent_accepted_for_management_review",
            ),
            _owner_event(
                version=2,
                event_type=ManageActionRealizationEventType.APPROVE,
                previous_status=ManageActionRealizationStatus.PENDING_REVIEW,
                status=ManageActionRealizationStatus.APPROVED,
                actor_role="PORTFOLIO_MANAGER",
                reason_code="REVIEW_APPROVED",
            ),
            _owner_event(
                version=3,
                event_type=ManageActionRealizationEventType.REQUEST_CHANGES,
                previous_status=ManageActionRealizationStatus.APPROVED,
                status=ManageActionRealizationStatus.PENDING_REVIEW,
                actor_role="PORTFOLIO_MANAGER",
                reason_code="REVIEW_REOPENED_FOR_CHANGES",
            ),
        )
        return ManageActionRealizationHistory(
            contract_version="lotus-manage.idea-action-outcome-history.v1",
            intake_id="iai_api_001",
            management_action_id="ima_api_001",
            source_authority="lotus-manage",
            portfolio_id=access_scope.portfolio_id,
            idea_candidate_id=self.intent.intent.candidate_id,
            conversion_intent_id=self.intent.intent.conversion_intent_id,
            status=ManageActionRealizationStatus.PENDING_REVIEW,
            source_event_version=3,
            rebalance_execution_proven=False,
            order_execution_proven=False,
            client_publication_proven=False,
            events=events,
        )


def _owner_event(
    *,
    version: int,
    event_type: ManageActionRealizationEventType,
    previous_status: ManageActionRealizationStatus | None,
    status: ManageActionRealizationStatus,
    actor_role: str,
    reason_code: str,
) -> ManageActionRealizationEvent:
    return ManageActionRealizationEvent(
        event_id=f"imae_api_{version:04d}",
        action_id="ima_api_001",
        source_event_version=version,
        event_type=event_type,
        previous_status=previous_status,
        status=status,
        occurred_at_utc=RECORDED_AT + timedelta(minutes=version),
        actor_id="pm-api-001",
        actor_role=actor_role,
        reason_code=reason_code,
        correlation_id="corr-owner-api",
        causation_id="conversion-manage-owner-api-001",
    )


def test_manage_realization_reconciliation_api_persists_exact_owner_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    manage_client = OwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
        manage_client=manage_client,
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
        suffix="-manage-owner-reconciliation",
        idempotency_prefix="manage-owner-reconciliation",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-manage-owner-api-001",
        target="manage_review",
        idempotency_key="conversion-manage-owner-api-001",
    )
    submitted = client.post(
        "/api/v1/conversion-intents/conversion-manage-owner-api-001/downstream-submissions",
        headers=downstream_submission_headers("submission-manage-owner-api-001"),
    )
    support_reference = submitted.json()["downstreamSubmission"]["supportReference"]

    response = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/manage-realization-reconciliation",
        headers=_reconciliation_headers(),
    )
    replay = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/manage-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert submitted.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["reconciliationStatus"] == "accepted"
    assert payload["appendedEventCount"] == 3
    assert payload["history"]["status"] == "PENDING_REVIEW"
    assert payload["history"]["managementActionId"] == "ima_api_001"
    assert payload["history"]["realizationAuthority"] == "lotus-manage"
    assert [event["eventType"] for event in payload["history"]["events"]] == [
        "INTAKE_ACCEPTED",
        "APPROVE",
        "REQUEST_CHANGES",
    ]
    assert payload["history"]["rebalanceExecutionProven"] is False
    assert payload["history"]["orderExecutionProven"] is False
    assert payload["history"]["clientPublicationProven"] is False
    assert payload["grantsRebalanceExecutionAuthority"] is False
    assert payload["grantsOrderAuthority"] is False
    assert payload["grantsClientPublicationAuthority"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert replay.status_code == 200
    assert replay.json()["reconciliationStatus"] == "replayed"
    assert replay.json()["appendedEventCount"] == 0

    denied_headers = _reconciliation_headers()
    denied_headers["X-Caller-Portfolio-Ids"] = "PB_OTHER"
    denied = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/manage-realization-reconciliation",
        headers=denied_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"


def test_manage_realization_reconciliation_api_reports_unconfigured_owner_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    manage_client = OwnerLifecycleClient()
    clients = ConversionRealizationClients(
        advise_client=CapturingConversionClient(
            DownstreamRealizationOutcome.accepted_by_downstream()
        ),
        manage_client=manage_client,
    )
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: clients,
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-manage-owner-unconfigured",
        idempotency_prefix="manage-owner-unconfigured",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-manage-owner-api-002",
        target="manage_review",
        idempotency_key="conversion-manage-owner-api-002",
    )
    submitted = client.post(
        "/api/v1/conversion-intents/conversion-manage-owner-api-002/downstream-submissions",
        headers=downstream_submission_headers("submission-manage-owner-api-002"),
    )
    support_reference = submitted.json()["downstreamSubmission"]["supportReference"]
    monkeypatch.setattr(
        reconciliation_api,
        "get_conversion_realization_clients",
        lambda: _raise_unconfigured_owner_reader(),
    )

    response = client.post(
        f"/api/v1/downstream-submissions/{support_reference}/manage-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "manage_realization_reader_not_configured"


def test_manage_realization_reconciliation_api_denial_emits_operation_event(
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
        "manage-realization-reconciliation",
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
        "X-Correlation-Id": "corr-manage-owner-reconciliation",
        "X-Trace-Id": "trace-manage-owner-reconciliation",
    }


def _raise_unconfigured_owner_reader() -> None:
    raise DownstreamRealizationClientsUnavailableError("Manage reader is not configured")


def test_manage_realization_reconciliation_reports_unwritable_durable_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When durable storage cannot accept writes, the route answers with the
    configuration problem BEFORE reading caller scope or calling the owner -
    no evidence can change while the ledger cannot record it."""

    from fastapi.responses import JSONResponse

    monkeypatch.setattr(
        reconciliation_api,
        "durable_write_problem",
        lambda repository: JSONResponse(
            status_code=503,
            content={"code": "durable_repository_not_configured"},
        ),
    )
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/downstream-submissions/downstream-submission-0123456789abcdef01234567/"
        "manage-realization-reconciliation",
        headers=_reconciliation_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "durable_repository_not_configured"
