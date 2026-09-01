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
from app.application.advise_realization_reconciliation import (
    AdviseRealizationAccessScopeDenied,
    AdviseRealizationReconciliationResult,
    AdviseRealizationReconciliationStatus,
    ReconcileAdviseRealizationCommand,
    reconcile_advise_realization_history,
)
from app.domain import AdviseProposalRealizationHistory
from app.observability import IdeaOperation, OperationOutcome
from app.api.operation_events import emit_api_foundation_operation_event
from app.ports.downstream_realization import AdviseProposalRealizationReader
from app.security.caller_context import CallerContext, PermissionDeniedError


_RECONCILE_CAPABILITY = "idea.downstream-realization.reconcile"


class AdviseRealizationOutcomeResponse(CamelModel):
    outcome_id: str = Field(alias="outcomeId")
    source_event_version: int = Field(alias="sourceEventVersion")
    status: str
    reason_code: str = Field(alias="reasonCode")
    occurred_at_utc: str = Field(alias="occurredAtUtc")
    review_work_id: str | None = Field(default=None, alias="reviewWorkId")
    proposal_id: str | None = Field(default=None, alias="proposalId")
    terminal: bool


class AdviseRealizationHistoryResponse(CamelModel):
    realization_id: str = Field(alias="realizationId")
    intake_id: str = Field(alias="intakeId")
    review_work_id: str | None = Field(default=None, alias="reviewWorkId")
    review_work_status: str | None = Field(default=None, alias="reviewWorkStatus")
    realization_authority: str = Field(alias="realizationAuthority")
    current_status: str = Field(alias="currentStatus")
    current_source_event_version: int = Field(alias="currentSourceEventVersion")
    proposal_id: str | None = Field(default=None, alias="proposalId")
    proposal_record_created: bool = Field(alias="proposalRecordCreated")
    outcomes: tuple[AdviseRealizationOutcomeResponse, ...]
    suitability_authority_granted: bool = Field(alias="suitabilityAuthorityGranted")
    order_created: bool = Field(alias="orderCreated")
    client_publication_authorized: bool = Field(alias="clientPublicationAuthorized")

    @classmethod
    def from_domain(
        cls,
        history: AdviseProposalRealizationHistory,
    ) -> "AdviseRealizationHistoryResponse":
        return cls(
            realizationId=history.realization_id,
            intakeId=history.intake_id,
            reviewWorkId=history.review_work_id,
            reviewWorkStatus=(
                history.review_work_status.value if history.review_work_status else None
            ),
            realizationAuthority=history.realization_authority,
            currentStatus=history.current_status.value,
            currentSourceEventVersion=history.current_source_event_version,
            proposalId=history.proposal_id,
            proposalRecordCreated=history.proposal_record_created,
            outcomes=tuple(
                AdviseRealizationOutcomeResponse(
                    outcomeId=outcome.outcome_id,
                    sourceEventVersion=outcome.source_event_version,
                    status=outcome.status.value,
                    reasonCode=outcome.reason_code,
                    occurredAtUtc=outcome.occurred_at_utc.isoformat(),
                    reviewWorkId=outcome.review_work_id,
                    proposalId=outcome.proposal_id,
                    terminal=outcome.terminal,
                )
                for outcome in history.outcomes
            ),
            suitabilityAuthorityGranted=history.suitability_authority_granted,
            orderCreated=history.order_created,
            clientPublicationAuthorized=history.client_publication_authorized,
        )


class AdviseRealizationReconciliationResponse(CamelModel):
    reconciliation_status: AdviseRealizationReconciliationStatus = Field(
        alias="reconciliationStatus"
    )
    appended_outcome_count: int = Field(alias="appendedOutcomeCount")
    history: AdviseRealizationHistoryResponse
    durable_storage_backed: bool = Field(alias="durableStorageBacked")
    grants_execution_authority: bool = Field(alias="grantsExecutionAuthority")
    grants_suitability_authority: bool = Field(alias="grantsSuitabilityAuthority")
    grants_client_publication_authority: bool = Field(
        alias="grantsClientPublicationAuthority"
    )
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def post_advise_realization_reconciliation(
    request: Request,
    caller: CallerContextHeaders,
    support_reference: str = Path(
        ...,
        alias="supportReference",
        pattern=r"^downstream-submission-[a-f0-9]{24}$",
    ),
) -> AdviseRealizationReconciliationResponse | JSONResponse:
    try:
        _require_reconciliation_caller(caller)
    except PermissionDeniedError:
        _emit(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to reconcile Advise realization outcomes.",
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    access_scope_filter = caller_access_scope_filter(caller)
    assert access_scope_filter is not None
    try:
        clients = get_conversion_realization_clients()
        advise_reader = cast(AdviseProposalRealizationReader, clients.advise_client)
    except DownstreamRealizationClientsUnavailableError:
        advise_reader = None
    try:
        result = reconcile_advise_realization_history(
            ReconcileAdviseRealizationCommand(
                support_reference=support_reference,
                actor_subject=caller.subject,
                access_scope_filter=access_scope_filter,
                correlation_id=_request_context_id(request, "correlation_id"),
                trace_id=_request_context_id(request, "trace_id"),
            ),
            repository=repository,
            advise_reader=advise_reader,
        )
    except AdviseRealizationAccessScopeDenied:
        _emit(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller scope does not cover this Advise realization.",
        )
    return _response(
        result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )


def _response(
    result: AdviseRealizationReconciliationResult,
    *,
    durable_storage_backed: bool,
) -> AdviseRealizationReconciliationResponse | JSONResponse:
    if result.status is AdviseRealizationReconciliationStatus.NOT_FOUND:
        _emit(OperationOutcome.NOT_FOUND, "downstream_submission_not_found")
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
        )
    if result.status in {
        AdviseRealizationReconciliationStatus.NOT_ELIGIBLE,
        AdviseRealizationReconciliationStatus.CONFLICT,
    }:
        _emit(OperationOutcome.CONFLICT, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code=result.blocker or "advise_realization_reconciliation_conflict",
            title="Advise realization reconciliation conflict",
            detail="The owner history failed eligibility or evidence validation.",
        )
    if result.status is AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE:
        _emit(OperationOutcome.BLOCKED, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=result.blocker or "advise_realization_owner_unavailable",
            title="Advise realization owner unavailable",
            detail="The authoritative Advise history could not be read; no evidence changed.",
        )
    assert result.history is not None
    _emit(
        OperationOutcome.REPLAYED
        if result.status is AdviseRealizationReconciliationStatus.REPLAYED
        else OperationOutcome.ACCEPTED,
        None,
    )
    return AdviseRealizationReconciliationResponse(
        reconciliationStatus=result.status,
        appendedOutcomeCount=result.appended_outcome_count,
        history=AdviseRealizationHistoryResponse.from_domain(result.history),
        durableStorageBacked=durable_storage_backed,
        grantsExecutionAuthority=result.grants_execution_authority,
        grantsSuitabilityAuthority=result.grants_suitability_authority,
        grantsClientPublicationAuthority=result.grants_client_publication_authority,
        supportedFeaturePromoted=False,
    )


def _require_reconciliation_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_RECONCILE_CAPABILITY):
        raise PermissionDeniedError(_RECONCILE_CAPABILITY)
    scope = caller.entitlement_scope
    if not (scope.tenant_ids and scope.book_ids and scope.portfolio_ids and scope.client_ids):
        raise PermissionDeniedError("idea.downstream-realization.entitlement_scope")


def _request_context_id(request: Request, attribute: str) -> str | None:
    value = getattr(request.state, attribute, None)
    return str(value) if value else None


def _emit(outcome: OperationOutcome, error_code: str | None) -> None:
    emit_api_foundation_operation_event(
        IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
        outcome,
        error_code,
    )


ADVISE_REALIZATION_RECONCILIATION_ROUTE: RouteMetadata = {
    "path": (
        "/api/v1/downstream-submissions/{supportReference}/"
        "advise-realization-reconciliation"
    ),
    "operation_id": "reconcileIdeaAdviseRealizationHistory",
    "summary": "Reconcile authoritative Advise realization outcomes",
    "description": (
        "Reads the exact trusted-scope Advise proposal-realization history for an accepted "
        "Idea submission and persists only an append-only, identity-consistent owner history. "
        "HTTP transport acceptance is not treated as proposal, suitability, execution, "
        "settlement, or client-publication evidence. Missing receipts, scope drift, identity "
        "drift, version gaps, chronology defects, and unsupported authority claims fail closed."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AdviseRealizationReconciliationResponse,
    "tags": ["Idea Downstream Realization"],
    "responses": {
        200: {
            "description": "Authoritative Advise history accepted or replayed.",
            "content": {
                "application/json": {
                    "example": {
                        "reconciliationStatus": "accepted",
                        "appendedOutcomeCount": 2,
                        "history": {
                            "realizationId": "ipr_73d5330c532f",
                            "intakeId": "ipi_7a1d2b3c4d5e",
                            "reviewWorkId": "iarw_a1c9106760cb",
                            "reviewWorkStatus": "PROPOSAL_LINKED",
                            "realizationAuthority": "lotus-advise",
                            "currentStatus": "PROPOSAL_LINKED",
                            "currentSourceEventVersion": 2,
                            "proposalId": "proposal-001",
                            "proposalRecordCreated": True,
                            "outcomes": [
                                {
                                    "outcomeId": "ipro_001",
                                    "sourceEventVersion": 1,
                                    "status": "ACCEPTED_FOR_REVIEW",
                                    "reasonCode": "idea_intake_accepted_for_adviser_review",
                                    "occurredAtUtc": "2026-09-01T10:00:00+00:00",
                                    "reviewWorkId": "iarw_a1c9106760cb",
                                    "proposalId": None,
                                    "terminal": False,
                                },
                                {
                                    "outcomeId": "ipro_002",
                                    "sourceEventVersion": 2,
                                    "status": "PROPOSAL_LINKED",
                                    "reasonCode": "advise_proposal_linked",
                                    "occurredAtUtc": "2026-09-01T10:01:00+00:00",
                                    "reviewWorkId": "iarw_a1c9106760cb",
                                    "proposalId": "proposal-001",
                                    "terminal": False,
                                },
                            ],
                            "suitabilityAuthorityGranted": False,
                            "orderCreated": False,
                            "clientPublicationAuthorized": False,
                        },
                        "durableStorageBacked": True,
                        "grantsExecutionAuthority": False,
                        "grantsSuitabilityAuthority": False,
                        "grantsClientPublicationAuthority": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller cannot reconcile this Advise realization.",
            description="Caller capability or complete entitlement scope is missing.",
        ),
        **not_found_metadata(
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
            description="The source submission does not exist.",
        ),
        **conflict_metadata(
            code="advise_realization_reconciliation_conflict",
            title="Advise realization reconciliation conflict",
            detail="The owner history failed eligibility or evidence validation.",
            description="Receipt, scope, identity, version, chronology, or authority conflict.",
        ),
        **service_unavailable_metadata(
            code="advise_realization_owner_unavailable",
            title="Advise realization owner unavailable",
            detail="The authoritative Advise history could not be read; no evidence changed.",
            description="Advise read configuration or availability prevented reconciliation.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_advise_realization_reconciliation_routes(app: FastAPI) -> None:
    app.post(
        path=ADVISE_REALIZATION_RECONCILIATION_ROUTE["path"],
        operation_id=ADVISE_REALIZATION_RECONCILIATION_ROUTE["operation_id"],
        summary=ADVISE_REALIZATION_RECONCILIATION_ROUTE["summary"],
        description=ADVISE_REALIZATION_RECONCILIATION_ROUTE["description"],
        status_code=ADVISE_REALIZATION_RECONCILIATION_ROUTE["status_code"],
        response_model=ADVISE_REALIZATION_RECONCILIATION_ROUTE["response_model"],
        tags=ADVISE_REALIZATION_RECONCILIATION_ROUTE["tags"],
        responses=ADVISE_REALIZATION_RECONCILIATION_ROUTE["responses"],
    )(post_advise_realization_reconciliation)
