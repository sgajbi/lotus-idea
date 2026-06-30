from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_access_scope_filter, caller_context_from_headers
from app.api.problem_details import invalid_request_metadata, permission_denied_metadata
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
    ReviewQueuePage,
    ReviewQueueReadinessSnapshot,
    build_review_queue_from_repository,
    build_review_queue_readiness_snapshot,
)
from app.domain import QueueExclusion, ReviewQueueItem
from app.domain.access_scope import QueueAccessScopeFilter
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
    require_capability,
    require_role_and_capability,
)

_READ_ADVISOR_QUEUE_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.review.queue.read",
    allowed_roles=("advisor",),
)

_READ_QUEUE_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.review.queue.readiness.read",
    allowed_roles=("operator",),
)


class ReviewQueueCandidateResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    score: str
    score_policy_version: str = Field(..., alias="scorePolicyVersion")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")

    @classmethod
    def from_item(cls, item: ReviewQueueItem) -> "ReviewQueueCandidateResponse":
        candidate = item.candidate
        assert candidate.score is not None
        return cls(
            candidateId=candidate.candidate_id,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            score=str(candidate.score.score),
            scorePolicyVersion=candidate.score.policy_version,
            sourceSignalIds=candidate.source_signal_ids,
        )


class ReviewQueueItemResponse(CamelModel):
    rank: int
    candidate: ReviewQueueCandidateResponse
    score: str
    priority_bucket: str = Field(..., alias="priorityBucket")
    policy_version: str = Field(..., alias="policyVersion")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")

    @classmethod
    def from_domain(cls, item: ReviewQueueItem) -> "ReviewQueueItemResponse":
        return cls(
            rank=item.rank,
            candidate=ReviewQueueCandidateResponse.from_item(item),
            score=str(item.score),
            priorityBucket=item.priority_bucket.value,
            policyVersion=item.policy_version,
            reasonCodes=tuple(reason.value for reason in item.reason_codes),
        )


class ReviewQueueExclusionResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    reason: str
    detail: str

    @classmethod
    def from_domain(cls, exclusion: QueueExclusion) -> "ReviewQueueExclusionResponse":
        return cls(
            candidateId=exclusion.candidate_id,
            reason=exclusion.reason.value,
            detail=exclusion.detail,
        )


class ReviewQueuePageResponse(CamelModel):
    limit: int
    offset: int
    returned_item_count: int = Field(..., alias="returnedItemCount")
    total_reviewable_item_count: int = Field(..., alias="totalReviewableItemCount")
    returned_exclusion_count: int = Field(..., alias="returnedExclusionCount")
    total_excluded_candidate_count: int = Field(..., alias="totalExcludedCandidateCount")
    next_offset: int | None = Field(None, alias="nextOffset")
    has_next_page: bool = Field(..., alias="hasNextPage")

    @classmethod
    def from_domain(cls, queue_page: ReviewQueuePage) -> "ReviewQueuePageResponse":
        page = queue_page.page
        return cls(
            limit=page.limit,
            offset=page.offset,
            returnedItemCount=page.returned_item_count,
            totalReviewableItemCount=page.total_reviewable_item_count,
            returnedExclusionCount=page.returned_exclusion_count,
            totalExcludedCandidateCount=page.total_excluded_candidate_count,
            nextOffset=page.next_offset,
            hasNextPage=page.has_next_page,
        )


class AdvisorReviewQueueResponse(CamelModel):
    policy_version: str = Field(..., alias="policyVersion")
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    items: tuple[ReviewQueueItemResponse, ...]
    exclusions: tuple[ReviewQueueExclusionResponse, ...]
    page: ReviewQueuePageResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        queue: ReviewQueuePage,
        *,
        durable_storage_backed: bool = False,
    ) -> "AdvisorReviewQueueResponse":
        return cls(
            policyVersion=queue.projection.policy_version,
            evaluatedAtUtc=queue.projection.evaluated_at_utc,
            items=tuple(
                ReviewQueueItemResponse.from_domain(item) for item in queue.projection.items
            ),
            exclusions=tuple(
                ReviewQueueExclusionResponse.from_domain(exclusion)
                for exclusion in queue.projection.exclusions
            ),
            page=ReviewQueuePageResponse.from_domain(queue),
            durableStorageBacked=durable_storage_backed,
            supportedFeaturePromoted=False,
        )


class ReviewQueueReadinessResponse(CamelModel):
    repository: str
    policy_version: str = Field(..., alias="policyVersion")
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    queue_projection_available: bool = Field(..., alias="queueProjectionAvailable")
    candidate_snapshot_count: int = Field(..., alias="candidateSnapshotCount")
    reviewable_item_count: int = Field(..., alias="reviewableItemCount")
    excluded_candidate_count: int = Field(..., alias="excludedCandidateCount")
    exclusion_counts: dict[str, int] = Field(..., alias="exclusionCounts")
    scored_candidate_count: int = Field(..., alias="scoredCandidateCount")
    unscored_candidate_count: int = Field(..., alias="unscoredCandidateCount")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    repository_side_pagination_certified: bool = Field(
        ...,
        alias="repositorySidePaginationCertified",
    )
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: ReviewQueueReadinessSnapshot,
    ) -> "ReviewQueueReadinessResponse":
        return cls(
            repository=snapshot.repository,
            policyVersion=snapshot.policy_version,
            evaluatedAtUtc=snapshot.evaluated_at_utc,
            queueProjectionAvailable=snapshot.queue_projection_available,
            candidateSnapshotCount=snapshot.candidate_snapshot_count,
            reviewableItemCount=snapshot.reviewable_item_count,
            excludedCandidateCount=snapshot.excluded_candidate_count,
            exclusionCounts=dict(snapshot.exclusion_counts),
            scoredCandidateCount=snapshot.scored_candidate_count,
            unscoredCandidateCount=snapshot.unscored_candidate_count,
            durableStorageBacked=snapshot.durable_storage_backed,
            repositorySidePaginationCertified=snapshot.repository_side_pagination_certified,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


async def get_advisor_review_queue(
    evaluated_at_utc: datetime = Query(..., alias="evaluatedAtUtc"),
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
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
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
            detail="Caller entitlement scope headers cannot contain blank values.",
        )
    try:
        require_capability(caller, _READ_ADVISOR_QUEUE_POLICY)
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
    if not is_timezone_aware(evaluated_at_utc):
        _emit_review_queue_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="evaluatedAtUtc must be timezone-aware.",
        )
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
    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=evaluated_at_utc,
            limit=limit,
            offset=offset,
            access_scope_filter=(
                None if effective_scope_filter.is_empty else effective_scope_filter
            ),
        ),
        repository=repository,
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
) -> ReviewQueueReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
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
        f"limit and offset page the ranked items and exclusions with a default "
        f"limit of {DEFAULT_REVIEW_QUEUE_PAGE_LIMIT} and maximum limit of "
        f"{MAX_REVIEW_QUEUE_PAGE_LIMIT}. "
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
