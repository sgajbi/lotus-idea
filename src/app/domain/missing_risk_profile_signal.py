from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.access_scope import ReviewAccessScope
from app.domain.ideas import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    OpportunitySignal,
    ReasonCode,
    ReviewPosture,
    ScoreComponent,
    SourceRef,
    UnsupportedEvidenceReason,
)
from app.domain.opportunity_identity import OpportunityIdentity, build_opportunity_identity
from app.domain.scoring import IdeaScoringInput, IdeaScoringPolicy, score_inputs
from app.domain.signal_evaluation import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    temporal_blocked_signal_result,
)


_CURRENT_RISK_PROFILE_STATUSES = {"CURRENT", "COMPLETE", "ACTIVE"}
_MISSING_RISK_PROFILE_STATUSES = {"MISSING", "STALE", "EXPIRED", "BLOCKED", "PENDING_REVIEW"}


class RiskProfilePosture(StrEnum):
    MISSING = "MISSING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REVIEW_DUE = "REVIEW_DUE"
    CURRENT = "CURRENT"


def risk_profile_posture_from_advise_diagnostic(
    advise_diagnostic: str | None,
) -> RiskProfilePosture | None:
    if advise_diagnostic is None:
        return None
    normalized_codes = {
        code.strip().lower()
        for token in advise_diagnostic.replace(";", ",").replace("|", ",").split(",")
        for code in token.split()
        if code.strip()
    }
    posture_by_code = {
        "risk_profile_missing": RiskProfilePosture.MISSING,
        "client_risk_profile_missing": RiskProfilePosture.MISSING,
        "advise_risk_profile_missing": RiskProfilePosture.MISSING,
        "risk_profile_stale": RiskProfilePosture.STALE,
        "client_risk_profile_stale": RiskProfilePosture.STALE,
        "risk_profile_expired": RiskProfilePosture.EXPIRED,
        "client_risk_profile_expired": RiskProfilePosture.EXPIRED,
        "risk_profile_review_due": RiskProfilePosture.REVIEW_DUE,
        "client_risk_profile_review_due": RiskProfilePosture.REVIEW_DUE,
        "risk_profile_current": RiskProfilePosture.CURRENT,
        "client_risk_profile_current": RiskProfilePosture.CURRENT,
    }
    postures = {posture_by_code[code] for code in normalized_codes if code in posture_by_code}
    return next(iter(postures)) if len(postures) == 1 else None


def missing_risk_profile_review_required_from_diagnostic(
    advise_diagnostic: str | None,
) -> bool | None:
    posture = risk_profile_posture_from_advise_diagnostic(advise_diagnostic)
    if posture is None:
        return None
    return posture is not RiskProfilePosture.CURRENT


@dataclass(frozen=True)
class MissingRiskProfileSignalPolicy:
    policy_version: str

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")


@dataclass(frozen=True)
class MissingRiskProfileSignalInput:
    as_of_date: date
    risk_profile_ref: SourceRef | None
    risk_profile_status: str | None
    risk_profile_effective_for_as_of_date: bool | None
    risk_profile_review_due: bool | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None


def evaluate_missing_risk_profile_signal(
    source_input: MissingRiskProfileSignalInput,
    policy: MissingRiskProfileSignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=((source_input.risk_profile_ref,) if source_input.risk_profile_ref else ()),
    )
    if temporal_block is not None:
        return temporal_block

    blocked = _blocking_result(source_input)
    if blocked is not None:
        return blocked
    if _risk_profile_is_current(source_input):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MISSING_RISK_PROFILE,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    if not _risk_profile_gap_is_reviewable(source_input):
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )

    return _candidate_result(source_input, policy)


def _blocking_result(
    source_input: MissingRiskProfileSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return _blocked(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.risk_profile_ref is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.risk_profile_ref.freshness is not EvidenceFreshness.CURRENT:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if (
        source_input.risk_profile_status is None
        or source_input.risk_profile_effective_for_as_of_date is None
        or source_input.risk_profile_review_due is None
    ):
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _risk_profile_is_current(source_input: MissingRiskProfileSignalInput) -> bool:
    assert source_input.risk_profile_status is not None
    assert source_input.risk_profile_effective_for_as_of_date is not None
    assert source_input.risk_profile_review_due is not None
    return (
        source_input.risk_profile_status.upper() in _CURRENT_RISK_PROFILE_STATUSES
        and source_input.risk_profile_effective_for_as_of_date
        and not source_input.risk_profile_review_due
    )


def _risk_profile_gap_is_reviewable(source_input: MissingRiskProfileSignalInput) -> bool:
    assert source_input.risk_profile_status is not None
    assert source_input.risk_profile_effective_for_as_of_date is not None
    assert source_input.risk_profile_review_due is not None
    return (
        source_input.risk_profile_status.upper() in _MISSING_RISK_PROFILE_STATUSES
        or not source_input.risk_profile_effective_for_as_of_date
        or source_input.risk_profile_review_due
    )


def _candidate_result(
    source_input: MissingRiskProfileSignalInput,
    policy: MissingRiskProfileSignalPolicy,
) -> SignalEvaluationResult:
    assert source_input.risk_profile_ref is not None
    source_refs = (source_input.risk_profile_ref,)
    identity = _stable_missing_risk_profile_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        source_refs=source_refs,
        reason_codes=(ReasonCode.MISSING_RISK_PROFILE,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=identity.candidate_id,
        identity=identity.initial_candidate_identity(),
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=_missing_risk_profile_score(source_input, policy),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _missing_risk_profile_score(
    source_input: MissingRiskProfileSignalInput,
    policy: MissingRiskProfileSignalPolicy,
) -> IdeaScore:
    status = (source_input.risk_profile_status or "").strip().upper()
    relevance_by_status = {
        "MISSING": Decimal("100"),
        "EXPIRED": Decimal("100"),
        "BLOCKED": Decimal("95"),
        "STALE": Decimal("90"),
        "PENDING_REVIEW": Decimal("75"),
    }
    relevance = relevance_by_status.get(status, Decimal("70"))
    if source_input.risk_profile_effective_for_as_of_date is False:
        relevance = max(relevance, Decimal("90"))
    if source_input.risk_profile_review_due:
        relevance = max(relevance, Decimal("70"))
    return score_inputs(
        (
            IdeaScoringInput(ScoreComponent.RELEVANCE, relevance, Decimal("0.70")),
            IdeaScoringInput(ScoreComponent.EVIDENCE_QUALITY, Decimal("100"), Decimal("0.15")),
            IdeaScoringInput(ScoreComponent.FRESHNESS, Decimal("100"), Decimal("0.15")),
        ),
        policy=IdeaScoringPolicy(policy_version=policy.policy_version),
        reason_codes=(ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED),
    )


def _blocked(
    *,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _stable_missing_risk_profile_identity(
    source_input: MissingRiskProfileSignalInput,
    policy: MissingRiskProfileSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.MISSING_RISK_PROFILE,
        opportunity_kind="missing_risk_profile",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "policy_version": policy.policy_version,
            "risk_profile_effective_for_as_of_date": (
                source_input.risk_profile_effective_for_as_of_date
            ),
            "risk_profile_review_due": source_input.risk_profile_review_due,
            "risk_profile_status": (source_input.risk_profile_status or "").strip().upper(),
        },
        source_refs=source_refs,
    )
