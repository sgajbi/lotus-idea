from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import (
    INVALID_CALLER_SCOPE_DETAIL,
    TRUSTED_CALLER_CONTEXT_HEADER,
    caller_access_scope_filter,
    caller_context_from_headers,
)
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    permission_denied_metadata,
)
from app.api.review_queue_models import (
    AdvisorReviewQueueResponse,
    ReviewQueueCandidateResponse,
    ReviewQueueExclusionResponse,
    ReviewQueueItemResponse,
    ReviewQueuePageResponse,
    ReviewQueueReadinessResponse,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.temporal_validation import is_timezone_aware
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    DEFAULT_REVIEW_QUEUE_PAGE_LIMIT,
    MAX_REVIEW_QUEUE_PAGE_LIMIT,
    build_review_queue_from_repository,
    build_review_queue_readiness_snapshot,
)
from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.review_queue_snapshot import (
    InvalidReviewQueueSnapshotTokenError,
    ReviewQueueSnapshotConflictError,
    ReviewQueueSnapshotTokenRequiredError,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_foundation_operation_event,
    emit_operation_event,
)
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)

__all__ = (
    "AdvisorReviewQueueResponse",
    "ReviewQueueCandidateResponse",
    "ReviewQueueExclusionResponse",
    "ReviewQueueItemResponse",
    "ReviewQueuePageResponse",
    "ReviewQueueReadinessResponse",
    "get_advisor_review_queue",
    "get_advisor_review_queue_readiness",
    "register_review_queue_routes",
)

_READ_ADVISOR_QUEUE_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.review.queue.read",
    allowed_roles=("advisor",),
)

_READ_QUEUE_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.review.queue.readiness.read",
    allowed_roles=("operator",),
)

ACTIVE_ADVISOR_REVIEW_QUEUE_EVALUATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


async def get_advisor_review_queue(
    evaluated_at_utc: datetime | None = Query(default=None, alias="evaluatedAtUtc"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    book_id: str | None = Query(default=None, alias="bookId"),
    portfolio_id: str | None = Query(default=None, alias="portfolioId"),
    client_id: str | None = Query(default=None, alias="clientId"),
    limit: int = Query(
        default=DEFAULT_REVIEW_QUEUE_PAGE_LIMIT,
        ge=1,
        le=MAX_REVIEW_QUEUE_PAGE_LIMIT,
    ),
    offset: int = Query(default=0, ge=0),
    snapshot_token: str | None = Query(default=None, alias="snapshotToken", max_length=69),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> AdvisorReviewQueueResponse | JSONResponse:
    try:
        caller = caller_context_from_headers(
            subject=x_caller_subject,
            roles=x_caller_roles,
            capabilities=x_caller_capabilities,
            tenant_ids=x_caller_tenant_ids,
            book_ids=x_caller_book_ids,
            portfolio_ids=x_caller_portfolio_ids,
            client_ids=x_caller_client_ids,
            trusted_caller_context=x_lotus_trusted_caller_context,
        )
    except ValueError:
        _emit_review_queue_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail=INVALID_CALLER_SCOPE_DETAIL,
        )
    try:
        require_role_and_capability(caller, _READ_ADVISOR_QUEUE_POLICY)
    except PermissionDeniedError:
        _emit_review_queue_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read advisor idea review queues.",
        )
    resolved_evaluated_at_utc = evaluated_at_utc or ACTIVE_ADVISOR_REVIEW_QUEUE_EVALUATED_AT_UTC
    if not is_timezone_aware(resolved_evaluated_at_utc):
        return _invalid_review_queue_evaluation_time_problem()
    try:
        requested_scope_filter = QueueAccessScopeFilter(
            tenant_id=tenant_id,
            book_id=book_id,
            portfolio_id=portfolio_id,
            client_id=client_id,
        )
    except ValueError:
        _emit_review_queue_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Scope query fields cannot be blank.",
        )
    effective_scope_filter = _effective_queue_scope_filter(
        requested_scope_filter=requested_scope_filter,
        caller_scope_filter=caller_access_scope_filter(caller),
    )
    if effective_scope_filter is None:
        _emit_review_queue_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read the requested advisor idea review scope.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    try:
        queue = build_review_queue_from_repository(
            BuildReviewQueueFromRepositoryCommand(
                evaluated_at_utc=resolved_evaluated_at_utc,
                limit=limit,
                offset=offset,
                snapshot_token=snapshot_token,
                access_scope_filter=(
                    None if effective_scope_filter.is_empty else effective_scope_filter
                ),
            ),
            repository=repository,
        )
    except (
        InvalidReviewQueueSnapshotTokenError,
        ReviewQueueSnapshotConflictError,
        ReviewQueueSnapshotTokenRequiredError,
    ) as error:
        return _review_queue_snapshot_problem(
            error,
            durable_storage_backed=durable_storage_backed,
        )
    _emit_review_queue_operation_event(
        OperationOutcome.ACCEPTED,
        durable_storage_backed=durable_storage_backed,
    )
    return AdvisorReviewQueueResponse.from_domain(
        queue,
        durable_storage_backed=durable_storage_backed,
    )


async def get_advisor_review_queue_readiness(
    evaluated_at_utc: datetime = Query(..., alias="evaluatedAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ReviewQueueReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _READ_QUEUE_READINESS_POLICY)
    except PermissionDeniedError:
        _emit_review_queue_readiness_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea review queue readiness.",
        )
    if not is_timezone_aware(evaluated_at_utc):
        _emit_review_queue_readiness_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="evaluatedAtUtc must be timezone-aware.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    snapshot = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=evaluated_at_utc),
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    _emit_review_queue_readiness_operation_event(
        OperationOutcome.ACCEPTED if snapshot.certification_ready else OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
    )
    return ReviewQueueReadinessResponse.from_domain(snapshot)


def _effective_queue_scope_filter(
    *,
    requested_scope_filter: QueueAccessScopeFilter,
    caller_scope_filter: QueueAccessScopeFilter | None,
) -> QueueAccessScopeFilter | None:
    if caller_scope_filter is None:
        return requested_scope_filter
    if not requested_scope_filter.is_subset_of(caller_scope_filter):
        return None
    return QueueAccessScopeFilter(
        tenant_id=requested_scope_filter.tenant_id or caller_scope_filter.tenant_id,
        book_id=requested_scope_filter.book_id or caller_scope_filter.book_id,
        portfolio_id=requested_scope_filter.portfolio_id or caller_scope_filter.portfolio_id,
        client_id=requested_scope_filter.client_id or caller_scope_filter.client_id,
    )


def _review_queue_snapshot_problem(
    error: (
        InvalidReviewQueueSnapshotTokenError
        | ReviewQueueSnapshotConflictError
        | ReviewQueueSnapshotTokenRequiredError
    ),
    *,
    durable_storage_backed: bool,
) -> JSONResponse:
    if isinstance(error, ReviewQueueSnapshotTokenRequiredError):
        outcome = OperationOutcome.INVALID_REQUEST
        status_code = status.HTTP_400_BAD_REQUEST
        code = "review_queue_snapshot_token_required"
        title = "Review queue snapshot token required"
        detail = "snapshotToken is required when offset is greater than zero."
    elif isinstance(error, InvalidReviewQueueSnapshotTokenError):
        outcome = OperationOutcome.INVALID_REQUEST
        status_code = status.HTTP_400_BAD_REQUEST
        code = "invalid_review_queue_snapshot_token"
        title = "Invalid review queue snapshot token"
        detail = "snapshotToken is not a valid opaque advisor queue snapshot token."
    else:
        outcome = OperationOutcome.CONFLICT
        status_code = status.HTTP_409_CONFLICT
        code = "review_queue_snapshot_conflict"
        title = "Review queue snapshot conflict"
        detail = (
            "The advisor queue changed after this snapshot was issued. "
            "Restart paging from offset zero."
        )
    _emit_review_queue_operation_event(outcome, code, durable_storage_backed)
    return problem_response(
        status_code=status_code,
        code=code,
        title=title,
        detail=detail,
    )


def _invalid_review_queue_evaluation_time_problem() -> JSONResponse:
    _emit_review_queue_operation_event(OperationOutcome.INVALID_REQUEST, "invalid_request")
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="evaluatedAtUtc must be timezone-aware.",
    )


def _emit_review_queue_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.REVIEW_QUEUE_READ,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


def _emit_review_queue_readiness_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.REVIEW_QUEUE_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


ADVISOR_REVIEW_QUEUE_ROUTE: RouteMetadata = {
    "path": "/api/v1/review-queues/advisor",
    "operation_id": "getAdvisorIdeaReviewQueue",
    "summary": "Get the advisor idea review queue",
    "description": (
        "Returns the deterministic advisor review queue projection over persisted idea "
        "candidate snapshots. Optional tenantId, bookId, portfolioId, and clientId "
        "query filters constrain results to the requested advisor access scope. "
        "When evaluatedAtUtc is omitted, the route returns the governed active "
        "advisor queue evaluation snapshot. "
        "evaluatedAtUtc is a candidate-creation as-of boundary: candidates created "
        "after it are not visible, while source as-of and evidence generation dates "
        "remain source-authority facts. "
        f"limit and offset page the ranked items and exclusions with a default "
        f"limit of {DEFAULT_REVIEW_QUEUE_PAGE_LIMIT} and maximum limit of "
        f"{MAX_REVIEW_QUEUE_PAGE_LIMIT}. "
        "Page metadata returns an opaque snapshotToken bound to the evaluation time, "
        "entitled scope, ranking policy, and queue state. Requests with offset greater "
        "than zero must return that token; changed queue state returns a 409 snapshot "
        "conflict so consumers restart without silent skips or duplicates. "
        "When platform caller-context scope headers are present, the route applies "
        "those entitlements automatically and rejects broader query scopes fail-closed. "
        "This is a certified internal API foundation for RFC-0002 Slice 07 and Slice 10 "
        "with bounded read-only Gateway publication; it does not expose a Workbench "
        "product surface, data-product certification, or supported feature. "
        "When the durable PostgreSQL repository is active, the advisor queue read path "
        "uses a repository-side bounded candidate projection instead of whole-store "
        "snapshot hydration."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AdvisorReviewQueueResponse,
    "tags": ["Idea Review"],
    "responses": {
        200: {
            "description": "Advisor review queue projection returned.",
            "content": {
                "application/json": {
                    "example": {
                        "policyVersion": "idea-deterministic-ranking-v1",
                        "evaluatedAtUtc": "2026-06-21T10:10:00Z",
                        "items": [
                            {
                                "rank": 1,
                                "candidate": {
                                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                                    "family": "high_cash",
                                    "lifecycleStatus": "generated",
                                    "reviewPosture": "advisor_review_required",
                                    "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                                    "score": "82",
                                    "scorePolicyVersion": "idle-liquidity-v1",
                                    "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                                },
                                "score": "82",
                                "priorityBucket": "high",
                                "policyVersion": "idle-liquidity-v1",
                                "reasonCodes": ["high_cash_ratio", "review_required"],
                            }
                        ],
                        "exclusions": [],
                        "page": {
                            "limit": 25,
                            "offset": 0,
                            "returnedItemCount": 1,
                            "totalReviewableItemCount": 1,
                            "returnedExclusionCount": 0,
                            "totalExcludedCandidateCount": 0,
                            "nextOffset": None,
                            "hasNextPage": False,
                            "snapshotToken": (
                                "rqs1_0123456789abcdef0123456789abcdef"
                                "0123456789abcdef0123456789abcdef"
                            ),
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the advisor review queue request and retry.",
        ),
        **permission_denied_metadata(
            detail=(
                "The caller is not permitted to read the advisor review queue or "
                "requested a queue scope outside their entitlements."
            ),
            description=(
                "Caller lacks advisor queue read permission or requested scope is outside "
                "caller entitlements."
            ),
        ),
        **conflict_metadata(
            code="review_queue_snapshot_conflict",
            title="Review queue snapshot conflict",
            detail="Restart advisor queue paging from offset zero.",
            description="Queue state changed after the supplied snapshot token was issued.",
        ),
    },
}

ADVISOR_REVIEW_QUEUE_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/review-queues/advisor/readiness",
    "operation_id": "getAdvisorIdeaReviewQueueReadiness",
    "summary": "Get advisor review queue readiness",
    "description": (
        "Returns source-safe operator readiness for the deterministic advisor review "
        "queue projection. The diagnostic reports aggregate queue counts, exclusion "
        "counts, durable-storage posture, and certification blockers only; it does "
        "not expose candidate identifiers, access-scope identifiers, Workbench proof, "
        "data-product certification, PM/compliance queue support, or a supported feature. "
        "Repository-side pagination is certified only for the durable PostgreSQL "
        "repository provider."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReviewQueueReadinessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Advisor review queue readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "policyVersion": "idea-deterministic-ranking-v1",
                        "evaluatedAtUtc": "2026-06-21T10:10:00Z",
                        "queueProjectionAvailable": True,
                        "candidateSnapshotCount": 2,
                        "reviewableItemCount": 1,
                        "excludedCandidateCount": 1,
                        "exclusionCounts": {
                            "invalid_state": 0,
                            "access_scope_mismatch": 0,
                            "closed": 0,
                            "duplicate": 0,
                            "expired": 1,
                            "non_reviewable_status": 0,
                            "rejected": 0,
                            "snoozed": 0,
                            "suppressed": 0,
                            "unscored": 0,
                            "unsupported_evidence": 0,
                        },
                        "scoredCandidateCount": 2,
                        "unscoredCandidateCount": 0,
                        "durableStorageBacked": False,
                        "repositorySidePaginationCertified": False,
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "certificationBlockers": [
                            "durable_repository_not_configured",
                            "repository_side_queue_pagination_not_certified",
                            "workbench_product_proof_missing",
                            "data_product_certification_missing",
                            "certified_runtime_trust_telemetry_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the advisor review queue readiness request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to read advisor review queue readiness.",
            description="Caller lacks queue readiness read permission.",
        ),
    },
}


def register_review_queue_routes(app: FastAPI) -> None:
    app.get(
        path=ADVISOR_REVIEW_QUEUE_ROUTE["path"],
        operation_id=ADVISOR_REVIEW_QUEUE_ROUTE["operation_id"],
        summary=ADVISOR_REVIEW_QUEUE_ROUTE["summary"],
        description=ADVISOR_REVIEW_QUEUE_ROUTE["description"],
        status_code=ADVISOR_REVIEW_QUEUE_ROUTE["status_code"],
        response_model=ADVISOR_REVIEW_QUEUE_ROUTE["response_model"],
        tags=ADVISOR_REVIEW_QUEUE_ROUTE["tags"],
        responses=ADVISOR_REVIEW_QUEUE_ROUTE["responses"],
    )(get_advisor_review_queue)
    app.get(
        path=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["path"],
        operation_id=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["operation_id"],
        summary=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["summary"],
        description=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["description"],
        status_code=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["status_code"],
        response_model=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["response_model"],
        tags=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["tags"],
        responses=ADVISOR_REVIEW_QUEUE_READINESS_ROUTE["responses"],
    )(get_advisor_review_queue_readiness)
