from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.repository_state import get_idea_repository
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashSignalCommand,
    evaluate_and_persist_high_cash_signal as evaluate_and_persist_high_cash_signal_command,
    evaluate_high_cash_signal_command,
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
from app.errors import ProblemDetails, problem_response
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


_EVALUATE_HIGH_CASH_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.signal.evaluate",
    allowed_roles=("advisor",),
)
_PERSIST_HIGH_CASH_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.candidate.persist",
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


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
    def from_domain(cls, result: SignalEvaluationResult) -> "EvaluateHighCashSignalResponse":
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
            sourceAuthority="lotus-core",
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
        description="False until database-backed persistence, migrations, and recovery evidence exist.",
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
    try:
        require_capability(caller, _EVALUATE_HIGH_CASH_POLICY)
    except PermissionDeniedError:
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea signals.",
        )

    result = evaluate_high_cash_signal_command(request.to_command())
    return EvaluateHighCashSignalResponse.from_domain(result)


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
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to persist idea candidates.",
        )
    if not idempotency_key.strip():
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Idempotency-Key is required.",
        )

    result = evaluate_and_persist_high_cash_signal_command(
        EvaluateAndPersistHighCashSignalCommand(
            evaluation=request.to_command(),
            idempotency_key=idempotency_key,
            actor_subject=caller.subject,
        ),
        repository=get_idea_repository(),
    )
    if (
        result.persistence is not None
        and result.persistence.decision is CandidatePersistenceDecision.CONFLICT
    ):
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )

    return EvaluateAndPersistHighCashSignalResponse(
        evaluation=EvaluateHighCashSignalResponse.from_domain(result.evaluation),
        persistence=(
            CandidatePersistenceSummaryResponse.from_record(
                decision=result.persistence.decision,
                record=result.persistence.record,
            )
            if result.persistence is not None
            else None
        ),
        durableStorageBacked=False,
        supportedFeaturePromoted=False,
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
            "description": "Caller lacks the required signal-evaluation capability.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": 403,
                        "code": "permission_denied",
                        "title": "Permission denied",
                        "detail": "The caller is not permitted to evaluate idea signals.",
                    }
                }
            },
        },
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
        "API foundation; persistence is not durable database-backed and no supported "
        "business feature is promoted."
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
        path=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["path"],
        operation_id=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["operation_id"],
        summary=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["summary"],
        description=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["description"],
        status_code=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["status_code"],
        response_model=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["response_model"],
        tags=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["tags"],
        responses=HIGH_CASH_EVALUATE_AND_PERSIST_ROUTE["responses"],
    )(evaluate_and_persist_high_cash_signal)
