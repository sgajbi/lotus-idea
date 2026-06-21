from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.high_cash_signal import (
    EvaluateHighCashSignalCommand,
    evaluate_high_cash_signal_command,
)
from app.domain import (
    EvidenceFreshness,
    IdeaCandidate,
    SignalEvaluationResult,
    SourceRef,
    SourceSystem,
)
from app.errors import ProblemDetails, problem_response
from app.security.caller_context import (
    CallerContext,
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


def _caller_from_headers(
    *,
    subject: str | None,
    roles: str | None,
    capabilities: str | None,
) -> CallerContext:
    return CallerContext.from_iterables(
        subject=subject or "anonymous",
        roles=(role.strip() for role in (roles or "").split(",")),
        capabilities=(capability.strip() for capability in (capabilities or "").split(",")),
    )


async def evaluate_high_cash_signal(
    request: EvaluateHighCashSignalRequest,
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> EvaluateHighCashSignalResponse | JSONResponse:
    caller = _caller_from_headers(
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
