from __future__ import annotations

from fastapi import FastAPI, Header, Path, Query, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.downstream_submission_reconciliation_models import (
    DownstreamSubmissionReconciliationListResponse,
    DownstreamSubmissionReconciliationRequest,
    DownstreamSubmissionReconciliationResponse,
    DownstreamSubmissionReconciliationSummaryResponse,
)
from app.api.durable_write_guard import durable_write_problem
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    not_found_metadata,
    permission_denied_metadata,
    problem_details_response,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.downstream_submission_reconciliation import (
    DownstreamSubmissionReconciliationResult,
    DownstreamSubmissionReconciliationStatus,
    list_downstream_submissions_requiring_reconciliation,
    reconcile_uncertain_downstream_submission,
)
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)


_READ_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.downstream-reconciliation.read",
    allowed_roles=("operator",),
)
_RECONCILE_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.downstream-reconciliation.resolve",
    allowed_roles=("operator",),
)


async def get_downstream_submissions_requiring_reconciliation(
    limit: int = Query(default=100, ge=1, le=100),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> DownstreamSubmissionReconciliationListResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _READ_POLICY)
    except PermissionDeniedError:
        _emit_event(IdeaOperation.DOWNSTREAM_RECONCILIATION_READ, OperationOutcome.PERMISSION_DENIED)
        return _permission_denied("inspect")
    repository = get_idea_repository()
    summaries = list_downstream_submissions_requiring_reconciliation(
        repository,
        limit=limit,
    )
    _emit_event(
        IdeaOperation.DOWNSTREAM_RECONCILIATION_READ,
        OperationOutcome.ACCEPTED,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )
    items = tuple(
        DownstreamSubmissionReconciliationSummaryResponse.from_domain(summary)
        for summary in summaries
    )
    return DownstreamSubmissionReconciliationListResponse(
        items=items,
        returnedCount=len(items),
        supportabilityStatus="not_certified",
        supportedFeaturePromoted=False,
    )


async def post_downstream_submission_reconciliation(
    request: DownstreamSubmissionReconciliationRequest,
    support_reference: str = Path(
        ...,
        alias="supportReference",
        pattern=r"^downstream-submission-[a-f0-9]{24}$",
    ),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> DownstreamSubmissionReconciliationResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _RECONCILE_POLICY)
    except PermissionDeniedError:
        _emit_event(
            IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
            OperationOutcome.PERMISSION_DENIED,
        )
        return _permission_denied("reconcile")
    try:
        validate_idempotency_key(idempotency_key)
        if idempotency_key != request.change_reference:
            raise ValueError("Idempotency-Key must equal changeReference")
    except ValueError:
        _emit_event(
            IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
            OperationOutcome.INVALID_REQUEST,
        )
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Idempotency-Key must be valid and equal changeReference.",
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    result = reconcile_uncertain_downstream_submission(
        repository,
        support_reference=support_reference,
        resolution=request.resolution,
        actor_subject=caller.subject,
        reason=request.reason,
        change_reference=request.change_reference,
    )
    return _reconciliation_response(
        result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )


def _reconciliation_response(
    result: DownstreamSubmissionReconciliationResult,
    *,
    durable_storage_backed: bool,
) -> DownstreamSubmissionReconciliationResponse | JSONResponse:
    outcome_by_status = {
        DownstreamSubmissionReconciliationStatus.ACCEPTED: OperationOutcome.ACCEPTED,
        DownstreamSubmissionReconciliationStatus.REPLAYED: OperationOutcome.REPLAYED,
        DownstreamSubmissionReconciliationStatus.NOT_FOUND: OperationOutcome.NOT_FOUND,
        DownstreamSubmissionReconciliationStatus.CONFLICT: OperationOutcome.CONFLICT,
        DownstreamSubmissionReconciliationStatus.NOT_ELIGIBLE: OperationOutcome.NOT_ELIGIBLE,
    }
    _emit_event(
        IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
        outcome_by_status[result.status],
        result.blocker,
        durable_storage_backed=durable_storage_backed,
    )
    if result.status is DownstreamSubmissionReconciliationStatus.NOT_FOUND:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
        )
    if result.status in {
        DownstreamSubmissionReconciliationStatus.CONFLICT,
        DownstreamSubmissionReconciliationStatus.NOT_ELIGIBLE,
    }:
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code=result.blocker or "downstream_submission_not_reconcilable",
            title="Downstream submission not reconcilable",
            detail="The submission remains unchanged pending operations review.",
        )
    return DownstreamSubmissionReconciliationResponse.from_domain(result)


def _permission_denied(action: str) -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail=f"The caller is not permitted to {action} downstream submissions.",
    )


def _emit_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=operation,
            outcome=outcome,
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


DOWNSTREAM_RECONCILIATION_LIST_ROUTE: RouteMetadata = {
    "path": "/api/v1/downstream-submissions/reconciliation",
    "operation_id": "listIdeaDownstreamSubmissionsRequiringReconciliation",
    "summary": "List uncertain downstream submissions",
    "description": (
        "Returns a bounded operator-only projection of in-flight and uncertain Idea "
        "submissions. The projection omits idempotency keys, resource identifiers, client "
        "and portfolio data, and downstream payloads."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DownstreamSubmissionReconciliationListResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Bounded source-safe reconciliation queue.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "items": [
                            {
                                "supportReference": (
                                    "downstream-submission-0123456789abcdef01234567"
                                ),
                                "resourceType": "conversion_intent",
                                "target": "advise_proposal",
                                "sourceAuthority": "lotus-advise",
                                "submissionPosture": "reconciliation_required",
                                "attemptCount": 1,
                                "submittedAtUtc": "2026-07-10T08:00:00Z",
                                "updatedAtUtc": "2026-07-10T08:00:02Z",
                                "leaseExpiresAtUtc": "2026-07-10T08:05:00Z",
                                "downstreamFailureReason": "downstream_timeout",
                                "auditEntryCount": 2,
                                "reconciliationEligible": True,
                                "owner": "lotus-idea-operations",
                            }
                        ],
                        "returnedCount": 1,
                        "supportabilityStatus": "not_certified",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller is not permitted to inspect downstream submissions.",
            description="Caller lacks downstream reconciliation inspection permission.",
        ),
    },
}

DOWNSTREAM_RECONCILIATION_ROUTE: RouteMetadata = {
    "path": "/api/v1/downstream-submissions/reconciliation/{supportReference}",
    "operation_id": "reconcileIdeaDownstreamSubmission",
    "summary": "Reconcile one uncertain downstream submission",
    "description": (
        "Records an explicit operator resolution against one opaque support reference. "
        "Idempotency-Key must equal changeReference, making an exact retry replay-safe. "
        "The route never retries the downstream call or grants suitability, execution, "
        "report publication, or other downstream authority."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DownstreamSubmissionReconciliationResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Reconciliation accepted or replayed.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "reconciliationStatus": "accepted",
                        "submission": {
                            "supportReference": (
                                "downstream-submission-0123456789abcdef01234567"
                            ),
                            "resourceType": "conversion_intent",
                            "target": "advise_proposal",
                            "sourceAuthority": "lotus-advise",
                            "submissionPosture": "accepted_by_downstream",
                            "attemptCount": 1,
                            "submittedAtUtc": "2026-07-10T08:00:00Z",
                            "updatedAtUtc": "2026-07-10T08:10:00Z",
                            "leaseExpiresAtUtc": "2026-07-10T08:05:00Z",
                            "downstreamFailureReason": None,
                            "auditEntryCount": 3,
                            "reconciliationEligible": False,
                            "owner": "lotus-idea-operations",
                        },
                        "blocker": None,
                        "supportabilityStatus": "not_certified",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Idempotency-Key must be valid and equal changeReference.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to reconcile downstream submissions.",
            description="Caller lacks downstream reconciliation permission.",
        ),
        **not_found_metadata(
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
            description="Opaque support reference does not identify a local submission.",
        ),
        **conflict_metadata(
            code="downstream_submission_not_reconcilable",
            title="Downstream submission not reconcilable",
            detail="The submission remains unchanged pending operations review.",
            description="Submission posture or mutation identity prevents reconciliation.",
        ),
    },
}


def register_downstream_submission_reconciliation_routes(app: FastAPI) -> None:
    app.get(**DOWNSTREAM_RECONCILIATION_LIST_ROUTE)(
        get_downstream_submissions_requiring_reconciliation
    )
    app.post(**DOWNSTREAM_RECONCILIATION_ROUTE)(post_downstream_submission_reconciliation)
