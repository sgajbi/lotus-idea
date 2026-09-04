from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Path, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders, caller_access_scope_filter
from app.api.durable_write_guard import (
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.problem_details import (
    conflict_metadata,
    not_found_metadata,
    permission_denied_metadata,
    problem_details_response,
    service_unavailable_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    DownstreamRealizationClientsUnavailableError,
    get_conversion_realization_clients,
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.manage_realization_reconciliation import (
    ManageRealizationAccessScopeDenied,
    ManageRealizationReconciliationResult,
    ManageRealizationReconciliationStatus,
    ReconcileManageRealizationCommand,
    reconcile_manage_realization_history,
)
from app.domain import ManageActionRealizationHistory
from app.api.realization_reconciliation_common import (
    emit_reconciliation_event,
    request_context_id,
    require_reconciliation_caller,
)
from app.observability import OperationOutcome
from app.ports.downstream_realization import ManageActionRealizationReader
from app.security.caller_context import PermissionDeniedError


class ManageRealizationEventResponse(CamelModel):
    event_id: str = Field(alias="eventId")
    source_event_version: int = Field(alias="sourceEventVersion")
    event_type: str = Field(alias="eventType")
    previous_status: str | None = Field(default=None, alias="previousStatus")
    status: str
    occurred_at_utc: str = Field(alias="occurredAtUtc")
    actor_role: str = Field(alias="actorRole")
    reason_code: str = Field(alias="reasonCode")


class ManageRealizationHistoryResponse(CamelModel):
    intake_id: str = Field(alias="intakeId")
    management_action_id: str = Field(alias="managementActionId")
    realization_authority: str = Field(alias="realizationAuthority")
    portfolio_id: str = Field(alias="portfolioId")
    status: str
    source_event_version: int = Field(alias="sourceEventVersion")
    events: tuple[ManageRealizationEventResponse, ...]
    rebalance_execution_proven: bool = Field(alias="rebalanceExecutionProven")
    order_execution_proven: bool = Field(alias="orderExecutionProven")
    client_publication_proven: bool = Field(alias="clientPublicationProven")

    @classmethod
    def from_domain(
        cls,
        history: ManageActionRealizationHistory,
    ) -> "ManageRealizationHistoryResponse":
        return cls(
            intakeId=history.intake_id,
            managementActionId=history.management_action_id,
            realizationAuthority=history.source_authority,
            portfolioId=history.portfolio_id,
            status=history.status.value,
            sourceEventVersion=history.source_event_version,
            events=tuple(
                ManageRealizationEventResponse(
                    eventId=event.event_id,
                    sourceEventVersion=event.source_event_version,
                    eventType=event.event_type.value,
                    previousStatus=(
                        event.previous_status.value if event.previous_status is not None else None
                    ),
                    status=event.status.value,
                    occurredAtUtc=event.occurred_at_utc.isoformat(),
                    actorRole=event.actor_role,
                    reasonCode=event.reason_code,
                )
                for event in history.events
            ),
            rebalanceExecutionProven=history.rebalance_execution_proven,
            orderExecutionProven=history.order_execution_proven,
            clientPublicationProven=history.client_publication_proven,
        )


class ManageRealizationReconciliationResponse(CamelModel):
    reconciliation_status: ManageRealizationReconciliationStatus = Field(
        alias="reconciliationStatus"
    )
    appended_event_count: int = Field(
        alias="appendedEventCount",
        description=(
            "Number of owner events appended by this committed mutation; exact and concurrent "
            "replays return zero."
        ),
    )
    history: ManageRealizationHistoryResponse
    durable_storage_backed: bool = Field(alias="durableStorageBacked")
    grants_rebalance_execution_authority: bool = Field(alias="grantsRebalanceExecutionAuthority")
    grants_order_authority: bool = Field(alias="grantsOrderAuthority")
    grants_client_publication_authority: bool = Field(alias="grantsClientPublicationAuthority")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def post_manage_realization_reconciliation(
    request: Request,
    caller: CallerContextHeaders,
    support_reference: str = Path(
        ...,
        alias="supportReference",
        pattern=r"^downstream-submission-[a-f0-9]{24}$",
    ),
) -> ManageRealizationReconciliationResponse | JSONResponse:
    try:
        require_reconciliation_caller(caller)
    except PermissionDeniedError:
        emit_reconciliation_event(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to reconcile Manage realization outcomes.",
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    access_scope_filter = caller_access_scope_filter(caller)
    assert access_scope_filter is not None
    try:
        clients = get_conversion_realization_clients()
        manage_reader = cast(ManageActionRealizationReader, clients.manage_client)
    except DownstreamRealizationClientsUnavailableError:
        manage_reader = None
    try:
        result = reconcile_manage_realization_history(
            ReconcileManageRealizationCommand(
                support_reference=support_reference,
                actor_subject=caller.subject,
                access_scope_filter=access_scope_filter,
                correlation_id=request_context_id(request, "correlation_id"),
                trace_id=request_context_id(request, "trace_id"),
            ),
            repository=repository,
            manage_reader=manage_reader,
        )
    except ManageRealizationAccessScopeDenied:
        emit_reconciliation_event(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller scope does not cover this Manage realization.",
        )
    return _response(
        result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )


def _response(
    result: ManageRealizationReconciliationResult,
    *,
    durable_storage_backed: bool,
) -> ManageRealizationReconciliationResponse | JSONResponse:
    if result.status is ManageRealizationReconciliationStatus.NOT_FOUND:
        emit_reconciliation_event(OperationOutcome.NOT_FOUND, "downstream_submission_not_found")
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
        )
    if result.status in {
        ManageRealizationReconciliationStatus.NOT_ELIGIBLE,
        ManageRealizationReconciliationStatus.CONFLICT,
    }:
        emit_reconciliation_event(OperationOutcome.CONFLICT, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code=result.blocker or "manage_realization_reconciliation_conflict",
            title="Manage realization reconciliation conflict",
            detail="The owner history failed eligibility or evidence validation.",
        )
    if result.status is ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE:
        emit_reconciliation_event(OperationOutcome.BLOCKED, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=result.blocker or "manage_realization_owner_unavailable",
            title="Manage realization owner unavailable",
            detail="The authoritative Manage history could not be read; no evidence changed.",
        )
    assert result.history is not None
    emit_reconciliation_event(
        OperationOutcome.REPLAYED
        if result.status is ManageRealizationReconciliationStatus.REPLAYED
        else OperationOutcome.ACCEPTED,
        None,
    )
    return ManageRealizationReconciliationResponse(
        reconciliationStatus=result.status,
        appendedEventCount=result.appended_event_count,
        history=ManageRealizationHistoryResponse.from_domain(result.history),
        durableStorageBacked=durable_storage_backed,
        grantsRebalanceExecutionAuthority=result.grants_rebalance_execution_authority,
        grantsOrderAuthority=result.grants_order_authority,
        grantsClientPublicationAuthority=result.grants_client_publication_authority,
        supportedFeaturePromoted=False,
    )


MANAGE_REALIZATION_RECONCILIATION_ROUTE: RouteMetadata = {
    "path": ("/api/v1/downstream-submissions/{supportReference}/manage-realization-reconciliation"),
    "operation_id": "reconcileIdeaManageRealizationHistory",
    "summary": "Reconcile authoritative Manage realization outcomes",
    "description": (
        "Reads the exact trusted-scope Manage-owned action outcome history for an accepted "
        "Idea submission and persists only an append-only, identity-consistent owner history. "
        "The owner's review status is not absorbing - REQUEST_CHANGES reopens APPROVED and "
        "REJECTED reviews - so monotonicity is enforced on the append-only event versions. "
        "HTTP transport acceptance is never treated as review, rebalance-execution, order, "
        "fill, settlement, or client-publication evidence. Missing receipts, scope drift, "
        "identity drift, version gaps, chain defects, and unsupported authority claims fail "
        "closed."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ManageRealizationReconciliationResponse,
    "tags": ["Idea Downstream Realization"],
    "responses": {
        200: {
            "description": "Authoritative Manage history accepted or replayed.",
            "content": {
                "application/json": {
                    "example": {
                        "reconciliationStatus": "accepted",
                        "appendedEventCount": 2,
                        "history": {
                            "intakeId": "iai_1f2e3d4c5b6a7f8e9d0c",
                            "managementActionId": "ima_9f8e7d6c5b4a3f2e1d0c",
                            "realizationAuthority": "lotus-manage",
                            "portfolioId": "portfolio-001",
                            "status": "APPROVED",
                            "sourceEventVersion": 2,
                            "events": [
                                {
                                    "eventId": "imae_0001",
                                    "sourceEventVersion": 1,
                                    "eventType": "INTAKE_ACCEPTED",
                                    "previousStatus": None,
                                    "status": "PENDING_REVIEW",
                                    "occurredAtUtc": "2026-09-03T10:00:00+00:00",
                                    "actorRole": "SERVICE",
                                    "reasonCode": (
                                        "idea_conversion_intent_accepted_for_management_review"
                                    ),
                                },
                                {
                                    "eventId": "imae_0002",
                                    "sourceEventVersion": 2,
                                    "eventType": "APPROVE",
                                    "previousStatus": "PENDING_REVIEW",
                                    "status": "APPROVED",
                                    "occurredAtUtc": "2026-09-03T10:05:00+00:00",
                                    "actorRole": "PORTFOLIO_MANAGER",
                                    "reasonCode": "REVIEW_APPROVED",
                                },
                            ],
                            "rebalanceExecutionProven": False,
                            "orderExecutionProven": False,
                            "clientPublicationProven": False,
                        },
                        "durableStorageBacked": True,
                        "grantsRebalanceExecutionAuthority": False,
                        "grantsOrderAuthority": False,
                        "grantsClientPublicationAuthority": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller cannot reconcile this Manage realization.",
            description="Caller capability or complete entitlement scope is missing.",
        ),
        **not_found_metadata(
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
            description="The source submission does not exist.",
        ),
        **conflict_metadata(
            code="manage_realization_reconciliation_conflict",
            title="Manage realization reconciliation conflict",
            detail="The owner history failed eligibility or evidence validation.",
            description="Receipt, scope, identity, version, chain, or authority conflict.",
        ),
        **service_unavailable_metadata(
            code="manage_realization_owner_unavailable",
            title="Manage realization owner unavailable",
            detail="The authoritative Manage history could not be read; no evidence changed.",
            description="Manage read configuration or availability prevented reconciliation.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_manage_realization_reconciliation_routes(app: FastAPI) -> None:
    app.post(
        path=MANAGE_REALIZATION_RECONCILIATION_ROUTE["path"],
        operation_id=MANAGE_REALIZATION_RECONCILIATION_ROUTE["operation_id"],
        summary=MANAGE_REALIZATION_RECONCILIATION_ROUTE["summary"],
        description=MANAGE_REALIZATION_RECONCILIATION_ROUTE["description"],
        status_code=MANAGE_REALIZATION_RECONCILIATION_ROUTE["status_code"],
        response_model=MANAGE_REALIZATION_RECONCILIATION_ROUTE["response_model"],
        tags=MANAGE_REALIZATION_RECONCILIATION_ROUTE["tags"],
        responses=MANAGE_REALIZATION_RECONCILIATION_ROUTE["responses"],
    )(post_manage_realization_reconciliation)
