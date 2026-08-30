from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from typing import Any

from app.domain.feedback_taxonomy import FeedbackOutcome, FeedbackReason
from app.domain.conversion_governance import GovernedConversionOutcome
from app.domain.ideas import EvidenceSupportability, OpportunityFamily
from app.domain.persistence_models import CandidatePersistenceRecord, IdeaRepositorySnapshot
from app.domain.review_governance import GovernedFeedbackEvent, ReviewAction
from app.domain.review_queue import QueuePriorityBucket


OFFLINE_FEEDBACK_EVALUATION_POLICY_VERSION = "idea-feedback-offline-evaluation-v1"
OFFLINE_FEEDBACK_EVALUATION_SCHEMA_VERSION = "lotus-idea.feedback-evaluation.v1"
MAX_OFFLINE_FEEDBACK_OBSERVATIONS = 10_000


class FeedbackEvaluationScopeError(ValueError):
    pass


class FeedbackEvaluationBoundExceeded(ValueError):
    pass


class FeedbackRankContext(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"
    WATCHLIST = "watchlist"
    UNRANKED = "unranked"


FeedbackCohortKey = tuple[
    OpportunityFamily,
    str,
    str | None,
    Decimal | None,
    str,
    FeedbackRankContext,
    EvidenceSupportability,
    ReviewAction | None,
    str,
    FeedbackOutcome,
    FeedbackReason,
    str | None,
    str | None,
    str | None,
]


@dataclass(frozen=True)
class FeedbackEvaluationCohort:
    opportunity_family: OpportunityFamily
    candidate_identity_policy_version: str
    score_policy_version: str | None
    score: Decimal | None
    ranking_policy_version: str
    rank_context: FeedbackRankContext
    evidence_supportability: EvidenceSupportability
    review_action: ReviewAction | None
    feedback_taxonomy_version: str
    feedback_outcome: FeedbackOutcome
    feedback_reason: FeedbackReason
    downstream_target: str | None
    downstream_status: str | None
    downstream_source_system: str | None
    observation_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "opportunityFamily": self.opportunity_family.value,
            "candidateIdentityPolicyVersion": self.candidate_identity_policy_version,
            "scorePolicyVersion": self.score_policy_version,
            "score": str(self.score) if self.score is not None else None,
            "rankingPolicyVersion": self.ranking_policy_version,
            "rankContext": self.rank_context.value,
            "evidenceSupportability": self.evidence_supportability.value,
            "reviewAction": self.review_action.value if self.review_action is not None else None,
            "feedbackTaxonomyVersion": self.feedback_taxonomy_version,
            "feedbackOutcome": self.feedback_outcome.value,
            "feedbackReason": self.feedback_reason.value,
            "downstreamTarget": self.downstream_target,
            "downstreamStatus": self.downstream_status,
            "downstreamSourceSystem": self.downstream_source_system,
            "observationCount": self.observation_count,
        }


@dataclass(frozen=True)
class FeedbackEvaluationSnapshot:
    evaluated_at_utc: datetime
    source_observation_count: int
    cohorts: tuple[FeedbackEvaluationCohort, ...]
    snapshot_digest: str

    def to_payload(self) -> dict[str, Any]:
        return {
            **_snapshot_payload_without_digest(
                evaluated_at_utc=self.evaluated_at_utc,
                source_observation_count=self.source_observation_count,
                cohorts=self.cohorts,
            ),
            "snapshotDigest": self.snapshot_digest,
        }


def build_offline_feedback_evaluation(
    snapshot: IdeaRepositorySnapshot,
    *,
    tenant_id: str,
    evaluated_at_utc: datetime,
    max_observations: int = MAX_OFFLINE_FEEDBACK_OBSERVATIONS,
) -> FeedbackEvaluationSnapshot:
    if not tenant_id.strip():
        raise FeedbackEvaluationScopeError("tenant_id is required")
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")
    if max_observations < 1 or max_observations > MAX_OFFLINE_FEEDBACK_OBSERVATIONS:
        raise ValueError(
            f"max_observations must be between 1 and {MAX_OFFLINE_FEEDBACK_OBSERVATIONS}"
        )

    observations: list[FeedbackCohortKey] = []
    for record in sorted(
        snapshot.candidate_records.values(),
        key=lambda item: item.candidate.candidate_id,
    ):
        if not record.feedback_events:
            continue
        access_scope = record.candidate.access_scope
        if access_scope is None:
            raise FeedbackEvaluationScopeError(
                "feedback evaluation requires access scope on every feedback-bearing candidate"
            )
        if access_scope.tenant_id != tenant_id:
            continue
        for feedback_event in sorted(
            record.feedback_events,
            key=lambda item: (
                item.feedback.recorded_at_utc,
                item.feedback.feedback_id,
            ),
        ):
            if feedback_event.feedback.recorded_at_utc > evaluated_at_utc:
                continue
            observations.append(
                _cohort_key(
                    record,
                    feedback_event,
                    evaluated_at_utc=evaluated_at_utc,
                )
            )
            if len(observations) > max_observations:
                raise FeedbackEvaluationBoundExceeded(
                    f"feedback evaluation exceeds the {max_observations} observation bound"
                )

    counts = Counter(observations)
    cohorts = tuple(
        _feedback_evaluation_cohort(key, count)
        for key, count in sorted(counts.items(), key=lambda item: _sortable_key(item[0]))
    )
    payload = _snapshot_payload_without_digest(
        evaluated_at_utc=evaluated_at_utc,
        source_observation_count=len(observations),
        cohorts=cohorts,
    )
    digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return FeedbackEvaluationSnapshot(
        evaluated_at_utc=evaluated_at_utc,
        source_observation_count=len(observations),
        cohorts=cohorts,
        snapshot_digest=digest,
    )


def _cohort_key(
    record: CandidatePersistenceRecord,
    feedback_event: GovernedFeedbackEvent,
    *,
    evaluated_at_utc: datetime,
) -> FeedbackCohortKey:
    review_action = _review_action_before_feedback(record, feedback_event)
    downstream = _downstream_outcome_after_feedback(
        record,
        feedback_event,
        evaluated_at_utc=evaluated_at_utc,
    )
    return (
        feedback_event.candidate_family,
        feedback_event.candidate_identity_policy_version,
        feedback_event.score_policy_version,
        feedback_event.score,
        feedback_event.ranking_policy_version,
        _rank_context(feedback_event.queue_priority_bucket),
        feedback_event.evidence_supportability,
        review_action,
        feedback_event.feedback.taxonomy_version,
        feedback_event.feedback.outcome,
        feedback_event.feedback.reason,
        downstream.target.value if downstream is not None else None,
        downstream.outcome.status.value if downstream is not None else None,
        downstream.source_system.value if downstream is not None else None,
    )


def _feedback_evaluation_cohort(
    key: FeedbackCohortKey,
    observation_count: int,
) -> FeedbackEvaluationCohort:
    (
        opportunity_family,
        candidate_identity_policy_version,
        score_policy_version,
        score,
        ranking_policy_version,
        rank_context,
        evidence_supportability,
        review_action,
        feedback_taxonomy_version,
        feedback_outcome,
        feedback_reason,
        downstream_target,
        downstream_status,
        downstream_source_system,
    ) = key
    return FeedbackEvaluationCohort(
        opportunity_family=opportunity_family,
        candidate_identity_policy_version=candidate_identity_policy_version,
        score_policy_version=score_policy_version,
        score=score,
        ranking_policy_version=ranking_policy_version,
        rank_context=rank_context,
        evidence_supportability=evidence_supportability,
        review_action=review_action,
        feedback_taxonomy_version=feedback_taxonomy_version,
        feedback_outcome=feedback_outcome,
        feedback_reason=feedback_reason,
        downstream_target=downstream_target,
        downstream_status=downstream_status,
        downstream_source_system=downstream_source_system,
        observation_count=observation_count,
    )


def _review_action_before_feedback(
    record: CandidatePersistenceRecord,
    feedback_event: GovernedFeedbackEvent,
) -> ReviewAction | None:
    eligible = tuple(
        decision
        for decision in record.review_decisions
        if decision.decided_at_utc <= feedback_event.feedback.recorded_at_utc
    )
    if not eligible:
        return None
    return max(eligible, key=lambda item: (item.decided_at_utc, item.review_id)).action


def _downstream_outcome_after_feedback(
    record: CandidatePersistenceRecord,
    feedback_event: GovernedFeedbackEvent,
    *,
    evaluated_at_utc: datetime,
) -> GovernedConversionOutcome | None:
    eligible = tuple(
        outcome
        for outcome in record.conversion_outcomes
        if feedback_event.feedback.recorded_at_utc
        <= outcome.outcome.recorded_at_utc
        <= evaluated_at_utc
    )
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda item: (
            item.outcome.recorded_at_utc,
            item.source_event_version,
            item.outcome.conversion_outcome_id,
        ),
    )


def _rank_context(priority: QueuePriorityBucket | None) -> FeedbackRankContext:
    if priority is None:
        return FeedbackRankContext.UNRANKED
    return FeedbackRankContext(priority.value)


def _sortable_key(values: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(
        "" if value is None else value.value if isinstance(value, StrEnum) else str(value)
        for value in values
    )


def _snapshot_payload_without_digest(
    *,
    evaluated_at_utc: datetime,
    source_observation_count: int,
    cohorts: tuple[FeedbackEvaluationCohort, ...],
) -> dict[str, Any]:
    return {
        "schemaVersion": OFFLINE_FEEDBACK_EVALUATION_SCHEMA_VERSION,
        "evaluationPolicyVersion": OFFLINE_FEEDBACK_EVALUATION_POLICY_VERSION,
        "evaluatedAtUtc": evaluated_at_utc.isoformat(),
        "scope": "single_tenant",
        "sourceObservationCount": source_observation_count,
        "cohorts": [cohort.to_payload() for cohort in cohorts],
        "privacyBoundary": {
            "containsRawTenantIdentifier": False,
            "containsRawClientIdentifier": False,
            "containsRawPortfolioIdentifier": False,
            "containsActorSubject": False,
            "containsFreeText": False,
            "containsPromptOrModelContent": False,
            "containsDownstreamReference": False,
        },
        "productionMutationAuthority": "none_read_only_offline_evidence",
    }


__all__ = [
    "MAX_OFFLINE_FEEDBACK_OBSERVATIONS",
    "OFFLINE_FEEDBACK_EVALUATION_POLICY_VERSION",
    "OFFLINE_FEEDBACK_EVALUATION_SCHEMA_VERSION",
    "FeedbackEvaluationBoundExceeded",
    "FeedbackEvaluationCohort",
    "FeedbackEvaluationScopeError",
    "FeedbackEvaluationSnapshot",
    "FeedbackRankContext",
    "build_offline_feedback_evaluation",
]
