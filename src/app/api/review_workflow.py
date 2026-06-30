from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_context_from_headers
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    not_found_metadata,
    permission_denied_metadata,
    permission_denied_problem,
)
from app.api.route_metadata import RouteMetadata
from app.api.temporal_validation import require_timezone_aware
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.review_workflow import (
    ApplyReviewActionToRepositoryCommand,
    RecordFeedbackToRepositoryCommand,
    apply_review_action_to_repository,
    record_feedback_to_repository,
)
from app.domain import (
    FeedbackCommand,
    FeedbackOutcome,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    InvalidReviewAction,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewEntitlementDenied,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
    SuppressionReason,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import CallerContext, PermissionDeniedError

_REVIEW_ACTION_CAPABILITY = "idea.review.record"
_FEEDBACK_CAPABILITY = "idea.feedback.record"


class ReviewAccessScopeRequest(CamelModel):
    tenant_id: str = Field(..., alias="tenantId")
    book_id: str = Field(..., alias="bookId")
    portfolio_id: str = Field(..., alias="portfolioId")
    client_id: str = Field(..., alias="clientId")

    @field_validator("tenant_id", "book_id", "portfolio_id", "client_id")
    @classmethod
    def _scope_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scope fields cannot be blank")
        return value

    def to_domain(self) -> ReviewAccessScope:
        return ReviewAccessScope(
            tenant_id=self.tenant_id,
            book_id=self.book_id,
            portfolio_id=self.portfolio_id,
            client_id=self.client_id,
        )


class ReviewActorScopeRequest(CamelModel):
    tenant_ids: tuple[str, ...] = Field(..., alias="tenantIds")
    book_ids: tuple[str, ...] = Field(..., alias="bookIds")
    portfolio_ids: tuple[str, ...] = Field(..., alias="portfolioIds")
    client_ids: tuple[str, ...] = Field(..., alias="clientIds")

    @field_validator("tenant_ids", "book_ids", "portfolio_ids", "client_ids")
    @classmethod
    def _scope_set_must_not_be_empty_or_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("authorized scope fields cannot be empty")
        if any(not item.strip() for item in value):
            raise ValueError("authorized scope fields cannot contain blank values")
        return tuple(value)

    def to_actor_context(
        self,
        *,
        caller: CallerContext,
        role: ReviewActorRole,
    ) -> ReviewActorContext:
        return ReviewActorContext(
            actor_subject=caller.subject,
            role=role,
            tenant_ids=frozenset(self.tenant_ids),
            book_ids=frozenset(self.book_ids),
            portfolio_ids=frozenset(self.portfolio_ids),
            client_ids=frozenset(self.client_ids),
        )


class ReviewActionRequest(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    action: ReviewAction
    access_scope: ReviewAccessScopeRequest = Field(..., alias="accessScope")
    authorized_scope: ReviewActorScopeRequest = Field(..., alias="authorizedScope")
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")

    @field_validator("review_id")
    @classmethod
    def _review_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewId is required")
        return value

    @field_validator("decided_at_utc", "snoozed_until_utc")
    @classmethod
    def _datetime_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_timezone_aware(
            value,
            field_name="datetime",
            message="datetime fields must be timezone-aware",
        )

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        role: ReviewActorRole,
        idempotency_key: str,
    ) -> ApplyReviewActionToRepositoryCommand:
        return ApplyReviewActionToRepositoryCommand(
            candidate_id=candidate_id,
            review=ReviewDecisionCommand(
                review_id=self.review_id,
                action=self.action,
                actor=self.authorized_scope.to_actor_context(caller=caller, role=role),
                access_scope=self.access_scope.to_domain(),
                reason_codes=self.reason_codes,
                decided_at_utc=self.decided_at_utc,
                suppression_reason=self.suppression_reason,
                snoozed_until_utc=self.snoozed_until_utc,
            ),
            idempotency_key=idempotency_key,
        )


class FeedbackRequest(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    access_scope: ReviewAccessScopeRequest = Field(..., alias="accessScope")
    authorized_scope: ReviewActorScopeRequest = Field(..., alias="authorizedScope")
    outcome: FeedbackOutcome
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @field_validator("feedback_id")
    @classmethod
    def _feedback_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("feedbackId is required")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def _recorded_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="recordedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        role: ReviewActorRole,
        idempotency_key: str,
    ) -> RecordFeedbackToRepositoryCommand:
        return RecordFeedbackToRepositoryCommand(
            candidate_id=candidate_id,
            feedback=FeedbackCommand(
                feedback_id=self.feedback_id,
                actor=self.authorized_scope.to_actor_context(caller=caller, role=role),
                access_scope=self.access_scope.to_domain(),
                outcome=self.outcome,
                reason_codes=self.reason_codes,
                recorded_at_utc=self.recorded_at_utc,
            ),
            idempotency_key=idempotency_key,
        )


class ReviewDecisionResponse(CamelModel):
    review_id: str = Field(..., alias="reviewId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    action: ReviewAction
    resulting_posture: str = Field(..., alias="resultingPosture")
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    decided_at_utc: datetime = Field(..., alias="decidedAtUtc")
    suppression_reason: SuppressionReason | None = Field(default=None, alias="suppressionReason")
    snoozed_until_utc: datetime | None = Field(default=None, alias="snoozedUntilUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, decision: GovernedReviewDecision) -> "ReviewDecisionResponse":
        return cls(
            reviewId=decision.review_id,
            candidateId=decision.candidate_id,
            evidencePacketId=decision.evidence_packet_id,
            action=decision.action,
            resultingPosture=decision.resulting_posture.value,
            actorRole=decision.actor_role,
            reasonCodes=tuple(reason.value for reason in decision.reason_codes),
            decidedAtUtc=decision.decided_at_utc,
            suppressionReason=decision.suppression_reason,
            snoozedUntilUtc=decision.snoozed_until_utc,
            grantsDownstreamAuthority=decision.grants_downstream_authority,
        )


class FeedbackEventResponse(CamelModel):
    feedback_id: str = Field(..., alias="feedbackId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    outcome: FeedbackOutcome
    actor_role: ReviewActorRole = Field(..., alias="actorRole")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @classmethod
    def from_domain(cls, event: GovernedFeedbackEvent) -> "FeedbackEventResponse":
        return cls(
            feedbackId=event.feedback.feedback_id,
            candidateId=event.candidate_id,
            evidencePacketId=event.evidence_packet_id,
            outcome=event.feedback.outcome,
            actorRole=event.actor_role,
            reasonCodes=tuple(reason.value for reason in event.feedback.reason_codes),
            recordedAtUtc=event.feedback.recorded_at_utc,
        )


class ReviewPersistenceSummaryResponse(CamelModel):
    decision: ReviewPersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    review_posture: str | None = Field(default=None, alias="reviewPosture")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: ReviewPersistenceResult,
    ) -> "ReviewPersistenceSummaryResponse":
        record = result.record
        audit_event = result.audit_event or (
            record.audit_events[-1] if record is not None and record.audit_events else None
        )
        return cls(
            decision=result.decision,
            candidateId=record.candidate.candidate_id if record is not None else None,
            lifecycleStatus=record.candidate.lifecycle_status.value if record is not None else None,
            reviewPosture=record.candidate.review_posture.value if record is not None else None,
            auditEventType=audit_event.event_type if audit_event is not None else None,
        )


class ReviewActionResponse(CamelModel):
    review_decision: ReviewDecisionResponse | None = Field(default=None, alias="reviewDecision")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class FeedbackResponse(CamelModel):
    feedback_event: FeedbackEventResponse | None = Field(default=None, alias="feedbackEvent")
    persistence: ReviewPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def record_review_action(
    request: ReviewActionRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> ReviewActionResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        role = _require_mutating_caller(
            caller,
            capability=_REVIEW_ACTION_CAPABILITY,
        )
        validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        result = apply_review_action_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=caller,
                role=role,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea reviews.")
    except ReviewEntitlementDenied:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to review this idea candidate.")
    except InvalidReviewAction:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.INVALID_STATE,
            "review_action_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="review_action_conflict",
            title="Review action conflict",
            detail="The review action is not valid for the current idea candidate state.",
        )
    except ValueError:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the review request and retry.",
        )

    problem = _problem_for_review_persistence(result.persistence)
    if problem is not None:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            _operation_outcome_from_review_decision(result.persistence.decision),
            _error_code_from_review_decision(result.persistence.decision),
            durable_storage_backed,
        )
        return problem
    _emit_review_operation_event(
        IdeaOperation.REVIEW_ACTION,
        _operation_outcome_from_review_decision(result.persistence.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return ReviewActionResponse(
        reviewDecision=(
            ReviewDecisionResponse.from_domain(result.review_result.decision)
            if result.review_result is not None
            else None
        ),
        persistence=ReviewPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


async def record_feedback(
    request: FeedbackRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> FeedbackResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        role = _require_mutating_caller(
            caller,
            capability=_FEEDBACK_CAPABILITY,
        )
        validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        result = record_feedback_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=caller,
                role=role,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea feedback.")
    except ReviewEntitlementDenied:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied(
            "The caller is not permitted to record feedback for this idea candidate."
        )
    except ValueError:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the feedback request and retry.",
        )

    problem = _problem_for_review_persistence(result.persistence)
    if problem is not None:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            _operation_outcome_from_review_decision(result.persistence.decision),
            _error_code_from_review_decision(result.persistence.decision),
            durable_storage_backed,
        )
        return problem
    _emit_review_operation_event(
        IdeaOperation.FEEDBACK_RECORD,
        _operation_outcome_from_review_decision(result.persistence.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return FeedbackResponse(
        feedbackEvent=(
            FeedbackEventResponse.from_domain(result.feedback_result.feedback_event)
            if result.feedback_result is not None
            else None
        ),
        persistence=ReviewPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _require_mutating_caller(
    caller: CallerContext,
    *,
    capability: str,
) -> ReviewActorRole:
    if not caller.has_capability(capability):
        raise PermissionDeniedError(capability)
    matching_roles = [role for role in ReviewActorRole if caller.has_role(role.value)]
    if len(matching_roles) != 1:
        raise PermissionDeniedError("idea.review.actor_role")
    return matching_roles[0]


def _problem_for_review_persistence(
    result: ReviewPersistenceResult,
) -> JSONResponse | None:
    if result.decision is ReviewPersistenceDecision.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    if result.decision is ReviewPersistenceDecision.CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    return None


def _permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def _emit_review_operation_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        operation,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


def _operation_outcome_from_review_decision(
    decision: ReviewPersistenceDecision,
) -> OperationOutcome:
    if decision is ReviewPersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is ReviewPersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is ReviewPersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def _error_code_from_review_decision(
    decision: ReviewPersistenceDecision,
) -> str | None:
    if decision is ReviewPersistenceDecision.NOT_FOUND:
        return "candidate_not_found"
    if decision is ReviewPersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    return None


REVIEW_ACTION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
    "operation_id": "recordIdeaCandidateReviewAction",
    "summary": "Record an idea candidate review action",
    "description": (
        "Records an internal advisor review action for a persisted idea candidate through "
        "the RFC-0002 Slice 08 review workflow foundation. The route requires a mutating "
        "review capability, caller role, upstream-authorized scope, and Idempotency-Key. "
        "It does not approve suitability, compliance, mandate, execution, or client "
        "communication, and it does not promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReviewActionResponse,
    "tags": ["Idea Review"],
    "responses": {
        200: {
            "description": "Review action accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "reviewDecision": {
                            "reviewId": "review-suppress-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "action": "suppress",
                            "resultingPosture": "suppressed",
                            "actorRole": "advisor",
                            "reasonCodes": ["review_suppressed", "review_required"],
                            "decidedAtUtc": "2026-06-21T10:05:00Z",
                            "suppressionReason": "manual_suppression",
                            "snoozedUntilUtc": None,
                            "grantsDownstreamAuthority": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "suppressed",
                            "auditEventType": "idea.review.decision_recorded",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the review request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea reviews.",
            description="Caller lacks review permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="review_action_conflict",
            title="Review action conflict",
            detail="The review action is not valid for the current idea candidate state.",
            description="Idempotency conflict or invalid review state transition.",
        ),
    },
}


FEEDBACK_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/feedback",
    "operation_id": "recordIdeaCandidateFeedback",
    "summary": "Record idea candidate feedback",
    "description": (
        "Records internal advisor feedback for a persisted idea candidate through the "
        "RFC-0002 Slice 08 feedback foundation. The route requires a mutating feedback "
        "capability, caller role, upstream-authorized scope, and Idempotency-Key. "
        "Feedback is source-provenanced and audited, but remains an internal foundation. "
        "Storage is process-local by default and PostgreSQL-backed only when "
        "LOTUS_IDEA_DATABASE_URL is configured; data-product certification, Gateway, "
        "and Workbench proof remain separate future promotion gates."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": FeedbackResponse,
    "tags": ["Idea Review"],
    "responses": {
        200: {
            "description": "Feedback accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "feedbackEvent": {
                            "feedbackId": "feedback-useful-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "outcome": "useful",
                            "actorRole": "advisor",
                            "reasonCodes": ["feedback_recorded", "review_required"],
                            "recordedAtUtc": "2026-06-21T10:06:00Z",
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "auditEventType": "idea.feedback.recorded",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the feedback request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea feedback.",
            description="Caller lacks feedback permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
            description="Idempotency conflict.",
        ),
    },
}


def register_review_workflow_routes(app: FastAPI) -> None:
    app.post(
        path=REVIEW_ACTION_ROUTE["path"],
        operation_id=REVIEW_ACTION_ROUTE["operation_id"],
        summary=REVIEW_ACTION_ROUTE["summary"],
        description=REVIEW_ACTION_ROUTE["description"],
        status_code=REVIEW_ACTION_ROUTE["status_code"],
        response_model=REVIEW_ACTION_ROUTE["response_model"],
        tags=REVIEW_ACTION_ROUTE["tags"],
        responses=REVIEW_ACTION_ROUTE["responses"],
    )(record_review_action)
    app.post(
        path=FEEDBACK_ROUTE["path"],
        operation_id=FEEDBACK_ROUTE["operation_id"],
        summary=FEEDBACK_ROUTE["summary"],
        description=FEEDBACK_ROUTE["description"],
        status_code=FEEDBACK_ROUTE["status_code"],
        response_model=FEEDBACK_ROUTE["response_model"],
        tags=FEEDBACK_ROUTE["tags"],
        responses=FEEDBACK_ROUTE["responses"],
    )(record_feedback)
