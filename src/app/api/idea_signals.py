from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.signal_api_support import (
    RouteMetadata,
    emit_signal_evaluation_event,
    operation_outcome_from_signal_evaluation,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_refs,
)
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashSignalCommand,
    evaluate_high_cash_signal_command,
)
from app.application.high_cash_signal import (
    evaluate_and_persist_high_cash_signal as evaluate_and_persist_high_cash_signal_command,
)
from app.application.mandate_restriction_signal import (
    EvaluateMandateRestrictionSignalCommand,
    evaluate_mandate_restriction_signal_command,
)
from app.domain import (
    CandidatePersistenceDecision,
    CandidatePersistenceRecord,
    EvidenceFreshness,
    IdeaCandidate,
    SignalEvaluationResult,
    SourceRef,
    SourceSystem,
)
from app.domain.access_scope import ReviewAccessScope
from app.errors import ProblemDetails, problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)

_PERSIST_HIGH_CASH_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.candidate.persist",
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


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


class SourceRefRequest(CamelModel):
    product_id: str = Field(
        ...,
        alias="productId",
        description="Governed source data-product identity.",
        examples=["lotus-core:PortfolioStateSnapshot:v1"],
    )
    source_system: SourceSystem = Field(
        ...,
        alias="sourceSystem",
        description="Source-owning Lotus service.",
        examples=[SourceSystem.LOTUS_CORE],
    )
    product_version: str = Field(
        ...,
        alias="productVersion",
        description="Source data-product version.",
        examples=["v1"],
    )
    route: str = Field(
        ...,
        description="Source-owned API or data-product route used to obtain the evidence.",
        examples=["/integration/portfolios/{portfolioRef}/core-snapshot"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date represented by the source evidence.",
        examples=["2026-06-21"],
    )
    generated_at_utc: datetime = Field(
        ...,
        alias="generatedAtUtc",
        description="UTC time when the source evidence was generated.",
        examples=["2026-06-21T10:00:00Z"],
    )
    content_hash: str = Field(
        ...,
        alias="contentHash",
        description="Source-owned content hash or lineage hash.",
        examples=["sha256:portfolio-state-snapshot-demo"],
    )
    data_quality_status: str = Field(
        ...,
        alias="dataQualityStatus",
        description="Source-owned data-quality posture.",
        examples=["complete"],
    )
    freshness: EvidenceFreshness = Field(
        ..., description="Freshness posture reported for the source evidence."
    )

    def to_domain(self) -> SourceRef:
        return SourceRef(
            product_id=self.product_id,
            source_system=self.source_system,
            product_version=self.product_version,
            route=self.route,
            as_of_date=self.as_of_date,
            generated_at_utc=self.generated_at_utc,
            content_hash=self.content_hash,
            data_quality_status=self.data_quality_status,
            freshness=self.freshness,
        )


class HighCashEvidenceRequest(CamelModel):
    portfolio_state_ref: SourceRefRequest | None = Field(
        default=None,
        alias="portfolioStateRef",
        description="Core portfolio-state source reference.",
    )
    holdings_ref: SourceRefRequest | None = Field(
        default=None,
        alias="holdingsRef",
        description="Core holdings or cash-balance source reference.",
    )
    cash_movement_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashMovementRef",
        description="Core cash-movement source reference.",
    )
    cashflow_projection_ref: SourceRefRequest | None = Field(
        default=None,
        alias="cashflowProjectionRef",
        description="Core cashflow-projection source reference.",
    )


class EvaluateHighCashSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    source_reported_cash_weight: Decimal | None = Field(
        default=None,
        alias="sourceReportedCashWeight",
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Cash weight reported by the source-owning service. lotus-idea does not calculate this value.",
        examples=["0.18"],
    )
    source_evidence: HighCashEvidenceRequest = Field(
        ...,
        alias="sourceEvidence",
        description="Source-owned evidence references needed for high-cash evaluation.",
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description=(
            "Optional advisor access scope carried onto created candidates so queue "
            "reads can filter by tenant, book, portfolio, and client before any "
            "Workbench product promotion."
        ),
    )
    entitlement_allowed: bool = Field(
        default=True,
        alias="entitlementAllowed",
        description="Whether upstream caller/source entitlement already allowed this evidence for evaluation.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_high_cash_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must be timezone-aware")
        return value

    def to_command(self) -> EvaluateHighCashSignalCommand:
        evidence = self.source_evidence
        return EvaluateHighCashSignalCommand(
            as_of_date=self.as_of_date,
            source_reported_cash_weight=self.source_reported_cash_weight,
            portfolio_state_ref=(
                evidence.portfolio_state_ref.to_domain()
                if evidence.portfolio_state_ref is not None
                else None
            ),
            holdings_ref=evidence.holdings_ref.to_domain()
            if evidence.holdings_ref is not None
            else None,
            cash_movement_ref=evidence.cash_movement_ref.to_domain()
            if evidence.cash_movement_ref is not None
            else None,
            cashflow_projection_ref=(
                evidence.cashflow_projection_ref.to_domain()
                if evidence.cashflow_projection_ref is not None
                else None
            ),
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateMandateRestrictionSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned restriction posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    restriction_ref: SourceRefRequest | None = Field(
        default=None,
        alias="restrictionRef",
        description="Source-owned mandate, restriction, or suitability-policy posture reference.",
    )
    restriction_status: str | None = Field(
        default=None,
        alias="restrictionStatus",
        description="Source-owned restriction posture such as REVIEW_REQUIRED, BLOCKED, BREACHED, or CLEAR.",
        examples=["REVIEW_REQUIRED"],
    )
    changed_since_last_review: bool | None = Field(
        default=None,
        alias="changedSinceLastReview",
        description="Whether the source-owning service reports a restriction or mandate change.",
    )
    actionability_blocked: bool | None = Field(
        default=None,
        alias="actionabilityBlocked",
        description="Whether the source-owning service reports actionability is blocked pending review.",
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description="Optional review access scope carried onto created candidates.",
    )
    entitlement_allowed: bool = Field(
        default=True,
        alias="entitlementAllowed",
        description="Whether upstream caller/source entitlement already allowed this evidence for evaluation.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_mandate_restriction_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must be timezone-aware")
        return value

    def to_command(self) -> EvaluateMandateRestrictionSignalCommand:
        return EvaluateMandateRestrictionSignalCommand(
            as_of_date=self.as_of_date,
            restriction_ref=(
                self.restriction_ref.to_domain() if self.restriction_ref is not None else None
            ),
            restriction_status=self.restriction_status,
            changed_since_last_review=self.changed_since_last_review,
            actionability_blocked=self.actionability_blocked,
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class SourceRefResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: date = Field(..., alias="asOfDate")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    freshness: EvidenceFreshness

    @classmethod
    def from_domain(cls, source_ref: SourceRef) -> "SourceRefResponse":
        return cls(
            productId=source_ref.product_id,
            sourceSystem=source_ref.source_system,
            productVersion=source_ref.product_version,
            asOfDate=source_ref.as_of_date,
            generatedAtUtc=source_ref.generated_at_utc,
            dataQualityStatus=source_ref.data_quality_status,
            freshness=source_ref.freshness,
        )


class IdeaCandidateSummaryResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    supportability: str
    score: str | None = None
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    source_refs: tuple[SourceRefResponse, ...] = Field(..., alias="sourceRefs")

    @classmethod
    def from_domain(cls, candidate: IdeaCandidate) -> "IdeaCandidateSummaryResponse":
        return cls(
            candidateId=candidate.candidate_id,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            supportability=candidate.evidence_packet.supportability.value,
            score=str(candidate.score.score) if candidate.score is not None else None,
            scorePolicyVersion=candidate.score.policy_version
            if candidate.score is not None
            else None,
            sourceSignalIds=candidate.source_signal_ids,
            sourceRefs=tuple(
                SourceRefResponse.from_domain(source_ref)
                for source_ref in candidate.evidence_packet.source_refs
            ),
        )


class EvaluateHighCashSignalResponse(CamelModel):
    outcome: str
    family: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    candidate: IdeaCandidateSummaryResponse | None
    source_authority: str = Field(
        "lotus-core",
        alias="sourceAuthority",
        description="Service that owns the cash-weight and source evidence facts.",
    )
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description="False until live source adapters, Gateway/Workbench proof, and supported-feature registration exist.",
    )

    @classmethod
    def from_domain(
        cls,
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> "EvaluateHighCashSignalResponse":
        return cls(
            outcome=result.outcome.value,
            family=result.family.value,
            reasonCodes=tuple(reason.value for reason in result.reason_codes),
            unsupportedReasons=tuple(reason.value for reason in result.unsupported_reasons),
            candidate=(
                IdeaCandidateSummaryResponse.from_domain(result.candidate)
                if result.candidate is not None
                else None
            ),
            sourceAuthority=source_authority,
            supportedFeaturePromoted=False,
        )


class EvaluateMandateRestrictionSignalResponse(CamelModel):
    outcome: str
    family: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    candidate: IdeaCandidateSummaryResponse | None
    source_authority: str = Field(..., alias="sourceAuthority")
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description="False until live source adapters, Gateway/Workbench proof, and supported-feature registration exist.",
    )

    @classmethod
    def from_domain(
        cls,
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> "EvaluateMandateRestrictionSignalResponse":
        return cls(
            outcome=result.outcome.value,
            family=result.family.value,
            reasonCodes=tuple(reason.value for reason in result.reason_codes),
            unsupportedReasons=tuple(reason.value for reason in result.unsupported_reasons),
            candidate=(
                IdeaCandidateSummaryResponse.from_domain(result.candidate)
                if result.candidate is not None
                else None
            ),
            sourceAuthority=source_authority,
            supportedFeaturePromoted=False,
        )


class CandidatePersistenceSummaryResponse(CamelModel):
    decision: CandidatePersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    evidence_hash: str | None = Field(default=None, alias="evidenceHash")
    persisted_at_utc: datetime | None = Field(default=None, alias="persistedAtUtc")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_record(
        cls,
        *,
        decision: CandidatePersistenceDecision,
        record: CandidatePersistenceRecord | None,
    ) -> "CandidatePersistenceSummaryResponse":
        audit_event = (
            record.audit_events[-1] if record is not None and record.audit_events else None
        )
        return cls(
            decision=decision,
            candidateId=record.candidate.candidate_id if record is not None else None,
            evidenceHash=record.evidence_hash if record is not None else None,
            persistedAtUtc=record.persisted_at_utc if record is not None else None,
            auditEventType=audit_event.event_type if audit_event is not None else None,
        )


class EvaluateAndPersistHighCashSignalResponse(CamelModel):
    evaluation: EvaluateHighCashSignalResponse
    persistence: CandidatePersistenceSummaryResponse | None
    durable_storage_backed: bool = Field(
        False,
        alias="durableStorageBacked",
        description=(
            "True only when the active repository provider is durable. Default local "
            "runtime remains process-local unless LOTUS_IDEA_DATABASE_URL is configured."
        ),
    )
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description="False until live source adapters, Gateway/Workbench proof, and supported-feature registration exist.",
    )


async def evaluate_high_cash_signal(
    request: EvaluateHighCashSignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateHighCashSignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    source_authority = _high_cash_source_authority(request)
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    result = evaluate_high_cash_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateHighCashSignalResponse.from_domain(result, source_authority=source_authority)


async def evaluate_mandate_restriction_signal(
    request: EvaluateMandateRestrictionSignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateMandateRestrictionSignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    source_authority = source_authority_from_refs((request.restriction_ref,))
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    result = evaluate_mandate_restriction_signal_command(request.to_command())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_foundation_operation_event,
    )
    return EvaluateMandateRestrictionSignalResponse.from_domain(
        result,
        source_authority=source_authority,
    )


async def evaluate_and_persist_high_cash_signal(
    request: EvaluateHighCashSignalRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateAndPersistHighCashSignalResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_capability(caller, _PERSIST_HIGH_CASH_POLICY)
    except PermissionDeniedError:
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.PERMISSION_DENIED,
            source_authority="lotus-core",
            error_code="permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to persist idea candidates.",
        )
    if not idempotency_key.strip():
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.INVALID_REQUEST,
            source_authority="lotus-core",
            error_code="invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Idempotency-Key is required.",
        )

    source_authority = _high_cash_source_authority(request)
    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    result = evaluate_and_persist_high_cash_signal_command(
        EvaluateAndPersistHighCashSignalCommand(
            evaluation=request.to_command(),
            idempotency_key=idempotency_key,
            actor_subject=caller.subject,
        ),
        repository=repository,
    )
    if (
        result.persistence is not None
        and result.persistence.decision is CandidatePersistenceDecision.CONFLICT
    ):
        emit_foundation_operation_event(
            IdeaOperation.CANDIDATE_PERSISTENCE,
            OperationOutcome.CONFLICT,
            source_authority="lotus-core",
            durable_storage_backed=durable_storage_backed,
            error_code="idempotency_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )

    emit_foundation_operation_event(
        IdeaOperation.CANDIDATE_PERSISTENCE,
        _operation_outcome_from_candidate_persistence(
            persistence_decision=(
                result.persistence.decision if result.persistence is not None else None
            ),
            evaluation=result.evaluation,
        ),
        source_authority=source_authority,
        durable_storage_backed=durable_storage_backed,
    )
    return EvaluateAndPersistHighCashSignalResponse(
        evaluation=EvaluateHighCashSignalResponse.from_domain(
            result.evaluation,
            source_authority=source_authority,
        ),
        persistence=(
            CandidatePersistenceSummaryResponse.from_record(
                decision=result.persistence.decision,
                record=result.persistence.record,
            )
            if result.persistence is not None
            else None
        ),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _operation_outcome_from_candidate_persistence(
    *,
    persistence_decision: CandidatePersistenceDecision | None,
    evaluation: SignalEvaluationResult,
) -> OperationOutcome:
    if persistence_decision is None:
        return operation_outcome_from_signal_evaluation(evaluation)
    if persistence_decision is CandidatePersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if persistence_decision is CandidatePersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if persistence_decision is CandidatePersistenceDecision.DUPLICATE_CANDIDATE:
        return OperationOutcome.DUPLICATE
    return OperationOutcome.CONFLICT


def _high_cash_source_authority(request: EvaluateHighCashSignalRequest) -> str:
    evidence = request.source_evidence
    return source_authority_from_refs(
        (
            evidence.portfolio_state_ref,
            evidence.holdings_ref,
            evidence.cash_movement_ref,
            evidence.cashflow_projection_ref,
        )
    )


HIGH_CASH_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-cash/evaluate",
    "operation_id": "evaluateHighCashIdeaSignal",
    "summary": "Evaluate a high-cash idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core evidence for the first high-cash "
        "opportunity family. The endpoint is a certified API foundation for RFC-0002 Slice 10; "
        "it does not fetch upstream sources, certify a data product, or promote a supported "
        "business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateHighCashSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "High-cash signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "high_cash",
                        "reasonCodes": [
                            "high_cash_ratio",
                            "cash_source_ready",
                            "review_required",
                        ],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "82",
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-core",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


MANDATE_RESTRICTION_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/mandate-restriction/evaluate",
    "operation_id": "evaluateMandateRestrictionIdeaSignal",
    "summary": "Evaluate a mandate or restriction idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core, Manage, or Advise evidence for "
        "mandate, restriction, or suitability-policy review posture. The endpoint is a "
        "bounded API foundation; it does not fetch upstream sources, approve suitability, "
        "change a mandate, clear a restriction, publish client communication, or promote a "
        "supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMandateRestrictionSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Mandate/restriction signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "mandate_restriction",
                        "reasonCodes": [
                            "mandate_restriction_review",
                            "review_required",
                        ],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_mandate_restriction_8d57adbf52f7f5a7",
                            "family": "mandate_restriction",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "compliance_review_required",
                            "evidencePacketId": "iep_mandate_restriction_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "66",
                            "scorePolicyVersion": "mandate-restriction-review-v1",
                            "sourceSignalIds": ["signal_mandate_restriction_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                                    "sourceSystem": "lotus-advise",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "quality_passed",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-advise",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/high-cash/evaluate-and-persist",
    "operation_id": "evaluateAndPersistHighCashIdeaSignal",
    "summary": "Evaluate and persist a high-cash idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Core evidence for the first high-cash "
        "opportunity family, then persists created candidates through the internal "
        "idempotency/audit repository foundation. The endpoint is an internal certified "
        "API foundation; persistence is process-local by default and PostgreSQL-backed "
        "only when LOTUS_IDEA_DATABASE_URL is configured. No supported business feature "
        "is promoted."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateAndPersistHighCashSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "High-cash signal evaluation completed and candidate persistence accepted, replayed, duplicated, or skipped for non-created candidates.",
            "content": {
                "application/json": {
                    "example": {
                        "evaluation": {
                            "outcome": "candidate_created",
                            "family": "high_cash",
                            "reasonCodes": [
                                "high_cash_ratio",
                                "cash_source_ready",
                                "review_required",
                            ],
                            "unsupportedReasons": [],
                            "candidate": {
                                "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                                "family": "high_cash",
                                "lifecycleStatus": "generated",
                                "reviewPosture": "advisor_review_required",
                                "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                                "supportability": "ready",
                                "score": "82",
                                "scorePolicyVersion": "idle-liquidity-v1",
                                "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                                "sourceRefs": [
                                    {
                                        "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                        "sourceSystem": "lotus-core",
                                        "productVersion": "v1",
                                        "asOfDate": "2026-06-21",
                                        "generatedAtUtc": "2026-06-21T10:00:00Z",
                                        "dataQualityStatus": "complete",
                                        "freshness": "current",
                                    }
                                ],
                            },
                            "sourceAuthority": "lotus-core",
                            "supportedFeaturePromoted": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidenceHash": "sha256:evidence-hash",
                            "persistedAtUtc": "2026-06-21T10:00:00Z",
                            "auditEventType": "idea.candidate.persisted",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        400: {
            "model": ProblemDetails,
            "description": "Request validation failed.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": 400,
                        "code": "invalid_request",
                        "title": "Invalid request",
                        "detail": "Request validation failed. Correct the request fields and retry.",
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks the required candidate-persistence capability.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": 403,
                        "code": "permission_denied",
                        "title": "Permission denied",
                        "detail": "The caller is not permitted to persist idea candidates.",
                    }
                }
            },
        },
        409: {
            "model": ProblemDetails,
            "description": "The idempotency key was already used with a different request payload.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": 409,
                        "code": "idempotency_conflict",
                        "title": "Idempotency conflict",
                        "detail": "The idempotency key was already used with a different request payload.",
                    }
                }
            },
        },
    },
}


def register_idea_signal_routes(app: FastAPI) -> None:
    app.post(
        path=HIGH_CASH_EVALUATE_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_ROUTE["responses"],
    )(evaluate_high_cash_signal)
    app.post(
        path=MANDATE_RESTRICTION_EVALUATE_ROUTE["path"],
        operation_id=MANDATE_RESTRICTION_EVALUATE_ROUTE["operation_id"],
        summary=MANDATE_RESTRICTION_EVALUATE_ROUTE["summary"],
        description=MANDATE_RESTRICTION_EVALUATE_ROUTE["description"],
        status_code=MANDATE_RESTRICTION_EVALUATE_ROUTE["status_code"],
        response_model=MANDATE_RESTRICTION_EVALUATE_ROUTE["response_model"],
        tags=MANDATE_RESTRICTION_EVALUATE_ROUTE["tags"],
        responses=MANDATE_RESTRICTION_EVALUATE_ROUTE["responses"],
    )(evaluate_mandate_restriction_signal)
    app.post(
        path=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["responses"],
    )(evaluate_and_persist_high_cash_signal)
