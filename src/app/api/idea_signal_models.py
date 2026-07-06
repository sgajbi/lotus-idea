from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.signal_models import (
    ReviewAccessScopeRequest,
    SignalEvaluationResponse,
    SourceRefRequest,
)
from app.api.temporal_validation import require_timezone_aware
from app.application.high_cash_signal import (
    EvaluateHighCashFromCoreCommand,
    EvaluateHighCashSignalCommand,
)
from app.application.mandate_restriction_signal import EvaluateMandateRestrictionSignalCommand
from app.application.mandate_restriction_signal import (
    EvaluateMandateRestrictionFromAdviseCommand,
)
from app.domain import CandidatePersistenceDecision, CandidatePersistenceRecord


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
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

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


class EvaluateHighCashFromSourceRequest(CamelModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        min_length=1,
        description="Portfolio identifier to request from Core source products.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for Core source evidence.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_high_cash_existing"],
    )

    @field_validator("portfolio_id")
    @classmethod
    def _portfolio_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("portfolioId is required")
        return cleaned

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(
        self,
        *,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> EvaluateHighCashFromCoreCommand:
        return EvaluateHighCashFromCoreCommand(
            portfolio_id=self.portfolio_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
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
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

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


class EvaluateMandateRestrictionFromSourceRequest(CamelModel):
    evaluation_id: str = Field(
        ...,
        alias="evaluationId",
        min_length=1,
        description="Lotus Advise policy-evaluation workflow identifier to fetch.",
        examples=["pev_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Advise mandate/restriction posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description="Optional review access scope checked against caller entitlement before source access.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_mandate_restriction_existing"],
    )

    @field_validator("evaluation_id")
    @classmethod
    def _evaluation_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("evaluationId is required")
        return cleaned

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(
        self,
        *,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> EvaluateMandateRestrictionFromAdviseCommand:
        return EvaluateMandateRestrictionFromAdviseCommand(
            evaluation_id=self.evaluation_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateHighCashSignalResponse(SignalEvaluationResponse):
    source_authority: str = Field(
        "lotus-core",
        alias="sourceAuthority",
        description="Service that owns the cash-weight and source evidence facts.",
    )


class EvaluateMandateRestrictionSignalResponse(SignalEvaluationResponse):
    pass


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


__all__ = [
    "CandidatePersistenceSummaryResponse",
    "EvaluateAndPersistHighCashSignalResponse",
    "EvaluateHighCashFromSourceRequest",
    "EvaluateHighCashSignalRequest",
    "EvaluateHighCashSignalResponse",
    "EvaluateMandateRestrictionFromSourceRequest",
    "EvaluateMandateRestrictionSignalRequest",
    "EvaluateMandateRestrictionSignalResponse",
    "HighCashEvidenceRequest",
]
