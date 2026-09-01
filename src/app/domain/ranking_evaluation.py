from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
from enum import IntEnum, StrEnum
from typing import Iterable

from app.domain.presentation_receipts import MAX_PRESENTED_CANDIDATE_COUNT
from app.domain.feedback_taxonomy import FeedbackOutcome
from app.domain.ideas import ConversionOutcomeStatus
from app.domain.review_governance import ReviewAction


RANKING_EVALUATION_POLICY_VERSION = "idea-ranking-evaluation-v1"
APPROVED_RANKING_CUTOFFS = (1, 3, 5, 10)
MINIMUM_READY_SNAPSHOT_COUNT = 30
MAX_RANKING_PRESENTATION_FACTS = 10_000
_RATE_QUANTUM = Decimal("0.000001")


class RankingRelevanceGrade(IntEnum):
    NOT_USEFUL = 0
    USEFUL = 1
    APPROVED_FOR_CONVERSION = 2
    DOWNSTREAM_ACCEPTED = 3


class RankingCutoffStatus(StrEnum):
    READY = "ready"
    INCOMPLETE_PRESENTATION = "incomplete_presentation"
    INCOMPLETE_JUDGMENTS = "incomplete_judgments"


class RankingMetricSupportStatus(StrEnum):
    UNAVAILABLE = "unavailable"
    INSUFFICIENT_SUPPORT = "insufficient_support"
    READY = "ready"


class RankingJudgmentSource(StrEnum):
    ADVISER_REVIEW = "adviser_review"
    ADVISER_FEEDBACK = "adviser_feedback"
    DOWNSTREAM_OUTCOME = "downstream_outcome"


@dataclass(frozen=True)
class RankedOpportunityJudgment:
    rank: int
    relevance_grade: RankingRelevanceGrade | None

    def __post_init__(self) -> None:
        if not _is_integer(self.rank) or self.rank <= 0:
            raise ValueError("rank must be a positive integer")
        if self.relevance_grade is not None and not isinstance(
            self.relevance_grade, RankingRelevanceGrade
        ):
            raise ValueError("relevance_grade must use the governed ranking vocabulary")


@dataclass(frozen=True)
class RankingRelevanceFact:
    occurred_at_utc: datetime
    source: RankingJudgmentSource
    relevance_grade: RankingRelevanceGrade

    def __post_init__(self) -> None:
        if self.occurred_at_utc.tzinfo is None or self.occurred_at_utc.utcoffset() is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        if not isinstance(self.source, RankingJudgmentSource):
            raise ValueError("source must use the governed ranking judgment vocabulary")
        if not isinstance(self.relevance_grade, RankingRelevanceGrade):
            raise ValueError("relevance_grade must use the governed ranking vocabulary")


@dataclass(frozen=True)
class RankingPresentationFact:
    """One privacy-safe, exact-version judgment for an immutable queue presentation."""

    queue_snapshot_digest: str
    tenant_id: str
    presented_at_utc: datetime
    visible_opportunity_count: int
    queue_policy_version: str
    ranking_policy_version: str
    surface: str
    producer: str
    judgment: RankedOpportunityJudgment

    def __post_init__(self) -> None:
        for field_name in (
            "queue_snapshot_digest",
            "tenant_id",
            "queue_policy_version",
            "ranking_policy_version",
            "surface",
            "producer",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required")
        if self.presented_at_utc.tzinfo is None or self.presented_at_utc.utcoffset() is None:
            raise ValueError("presented_at_utc must be timezone-aware")
        _validate_visible_opportunity_count(self.visible_opportunity_count)
        if not isinstance(self.judgment, RankedOpportunityJudgment):
            raise ValueError("judgment must use RankedOpportunityJudgment")


@dataclass(frozen=True)
class RankingQueueSnapshotEvaluation:
    queue_snapshot_digest: str
    tenant_id: str
    presented_at_utc: datetime
    queue_policy_version: str
    ranking_policy_version: str
    surface: str
    producer: str
    evaluation: RankingSnapshotEvaluation


@dataclass(frozen=True)
class RankingCutoffAggregate:
    cutoff: int
    snapshot_count: int
    ready_snapshot_count: int
    incomplete_presentation_snapshot_count: int
    incomplete_judgment_snapshot_count: int
    judged_opportunity_count: int
    evaluated_opportunity_count: int
    judgment_coverage: Decimal | None
    support_status: RankingMetricSupportStatus
    mean_precision_at_k: Decimal | None
    mean_ndcg_at_k: Decimal | None


@dataclass(frozen=True)
class RankingCutoffEvaluation:
    cutoff: int
    evaluated_depth: int
    status: RankingCutoffStatus
    observed_opportunity_count: int
    judged_opportunity_count: int
    unjudged_opportunity_count: int
    judgment_coverage: Decimal
    precision_at_k: Decimal | None
    ndcg_at_k: Decimal | None


@dataclass(frozen=True)
class RankingSnapshotEvaluation:
    policy_version: str
    visible_opportunity_count: int
    cutoff_evaluations: tuple[RankingCutoffEvaluation, ...]


@dataclass(frozen=True)
class _CutoffPopulation:
    cutoff: int
    evaluated_depth: int
    observed_opportunity_count: int
    judged_opportunity_count: int
    unjudged_opportunity_count: int
    judgment_coverage: Decimal


def evaluate_ranking_snapshot(
    judgments: Iterable[RankedOpportunityJudgment],
    *,
    visible_opportunity_count: int,
    cutoffs: tuple[int, ...] = APPROVED_RANKING_CUTOFFS,
) -> RankingSnapshotEvaluation:
    """Evaluate one immutable queue presentation without treating unjudged work as irrelevant."""

    _validate_visible_opportunity_count(visible_opportunity_count)
    normalized_cutoffs = _validate_cutoffs(cutoffs)
    by_rank = _validate_judgments(
        tuple(judgments),
        visible_opportunity_count=visible_opportunity_count,
    )
    return RankingSnapshotEvaluation(
        policy_version=RANKING_EVALUATION_POLICY_VERSION,
        visible_opportunity_count=visible_opportunity_count,
        cutoff_evaluations=tuple(
            _evaluate_cutoff(
                by_rank,
                cutoff=cutoff,
                visible_opportunity_count=visible_opportunity_count,
            )
            for cutoff in normalized_cutoffs
        ),
    )


def review_relevance_grade(action: ReviewAction) -> RankingRelevanceGrade | None:
    return {
        ReviewAction.APPROVE_FOR_CONVERSION: RankingRelevanceGrade.APPROVED_FOR_CONVERSION,
        ReviewAction.REJECT: RankingRelevanceGrade.NOT_USEFUL,
        ReviewAction.SUPPRESS: RankingRelevanceGrade.NOT_USEFUL,
    }.get(action)


def feedback_relevance_grade(outcome: FeedbackOutcome) -> RankingRelevanceGrade:
    return (
        RankingRelevanceGrade.USEFUL
        if outcome is FeedbackOutcome.USEFUL
        else RankingRelevanceGrade.NOT_USEFUL
    )


def downstream_relevance_grade(
    status: ConversionOutcomeStatus,
) -> RankingRelevanceGrade | None:
    if status in {ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED}:
        return RankingRelevanceGrade.DOWNSTREAM_ACCEPTED
    return None


def derive_ranking_relevance(
    facts: Iterable[RankingRelevanceFact],
    *,
    presented_at_utc: datetime,
    evaluated_at_utc: datetime,
    valid_until_utc: datetime | None,
) -> RankingRelevanceGrade | None:
    """Resolve source precedence and chronology for one exact candidate presentation version."""

    eligible = tuple(
        fact
        for fact in facts
        if presented_at_utc <= fact.occurred_at_utc <= evaluated_at_utc
        and (valid_until_utc is None or fact.occurred_at_utc < valid_until_utc)
    )
    if any(
        fact.source is RankingJudgmentSource.DOWNSTREAM_OUTCOME
        and fact.relevance_grade is RankingRelevanceGrade.DOWNSTREAM_ACCEPTED
        for fact in eligible
    ):
        return RankingRelevanceGrade.DOWNSTREAM_ACCEPTED
    human = tuple(
        fact for fact in eligible if fact.source is not RankingJudgmentSource.DOWNSTREAM_OUTCOME
    )
    if not human:
        return None
    latest_at = max(fact.occurred_at_utc for fact in human)
    latest_grades = {fact.relevance_grade for fact in human if fact.occurred_at_utc == latest_at}
    if len(latest_grades) != 1:
        raise ValueError(
            "ranking relevance contains conflicting human judgments at the same instant"
        )
    return next(iter(latest_grades))


def evaluate_ranking_presentations(
    facts: Iterable[RankingPresentationFact],
    *,
    cutoffs: tuple[int, ...] = APPROVED_RANKING_CUTOFFS,
) -> tuple[RankingQueueSnapshotEvaluation, ...]:
    """Evaluate immutable queue snapshots after validating receipt-set consistency."""

    grouped: dict[str, list[RankingPresentationFact]] = {}
    for fact in facts:
        if not isinstance(fact, RankingPresentationFact):
            raise ValueError("facts must use RankingPresentationFact")
        grouped.setdefault(fact.queue_snapshot_digest, []).append(fact)

    evaluations: list[RankingQueueSnapshotEvaluation] = []
    for snapshot_digest in sorted(grouped):
        snapshot_facts = tuple(grouped[snapshot_digest])
        authority = snapshot_facts[0]
        _validate_snapshot_consistency(snapshot_facts, authority=authority)
        evaluations.append(
            RankingQueueSnapshotEvaluation(
                queue_snapshot_digest=snapshot_digest,
                tenant_id=authority.tenant_id,
                presented_at_utc=authority.presented_at_utc,
                queue_policy_version=authority.queue_policy_version,
                ranking_policy_version=authority.ranking_policy_version,
                surface=authority.surface,
                producer=authority.producer,
                evaluation=evaluate_ranking_snapshot(
                    (fact.judgment for fact in snapshot_facts),
                    visible_opportunity_count=authority.visible_opportunity_count,
                    cutoffs=cutoffs,
                ),
            )
        )
    return tuple(evaluations)


def aggregate_ranking_evaluations(
    evaluations: Iterable[RankingQueueSnapshotEvaluation],
    *,
    minimum_ready_snapshot_count: int = MINIMUM_READY_SNAPSHOT_COUNT,
) -> tuple[RankingCutoffAggregate, ...]:
    """Build privacy-safe macro averages while retaining evidence-completeness posture."""

    if not _is_integer(minimum_ready_snapshot_count) or minimum_ready_snapshot_count <= 0:
        raise ValueError("minimum_ready_snapshot_count must be a positive integer")
    evaluation_tuple = tuple(evaluations)
    cutoff_values = sorted(
        {
            cutoff.cutoff
            for snapshot in evaluation_tuple
            for cutoff in snapshot.evaluation.cutoff_evaluations
        }
    )
    aggregates: list[RankingCutoffAggregate] = []
    for cutoff_value in cutoff_values:
        cutoff_evaluations = tuple(
            cutoff
            for snapshot in evaluation_tuple
            for cutoff in snapshot.evaluation.cutoff_evaluations
            if cutoff.cutoff == cutoff_value
        )
        ready = tuple(
            cutoff for cutoff in cutoff_evaluations if cutoff.status is RankingCutoffStatus.READY
        )
        ready_count = len(ready)
        support_status = (
            RankingMetricSupportStatus.UNAVAILABLE
            if ready_count == 0
            else RankingMetricSupportStatus.INSUFFICIENT_SUPPORT
            if ready_count < minimum_ready_snapshot_count
            else RankingMetricSupportStatus.READY
        )
        evaluated_count = sum(item.evaluated_depth for item in cutoff_evaluations)
        judged_count = sum(item.judged_opportunity_count for item in cutoff_evaluations)
        aggregates.append(
            RankingCutoffAggregate(
                cutoff=cutoff_value,
                snapshot_count=len(cutoff_evaluations),
                ready_snapshot_count=ready_count,
                incomplete_presentation_snapshot_count=sum(
                    item.status is RankingCutoffStatus.INCOMPLETE_PRESENTATION
                    for item in cutoff_evaluations
                ),
                incomplete_judgment_snapshot_count=sum(
                    item.status is RankingCutoffStatus.INCOMPLETE_JUDGMENTS
                    for item in cutoff_evaluations
                ),
                judged_opportunity_count=judged_count,
                evaluated_opportunity_count=evaluated_count,
                judgment_coverage=(
                    _ratio(judged_count, evaluated_count) if evaluated_count else None
                ),
                support_status=support_status,
                mean_precision_at_k=_mean_ready_metric(ready, metric="precision"),
                mean_ndcg_at_k=_mean_ready_metric(ready, metric="ndcg"),
            )
        )
    return tuple(aggregates)


def _mean_ready_metric(
    evaluations: tuple[RankingCutoffEvaluation, ...],
    *,
    metric: str,
) -> Decimal | None:
    values = tuple(
        item.precision_at_k if metric == "precision" else item.ndcg_at_k for item in evaluations
    )
    if not values:
        return None
    if any(value is None for value in values):
        raise ValueError("ready ranking evaluations must carry quality values")
    return _quantize(
        sum((value for value in values if value is not None), Decimal(0)) / len(values)
    )


def _validate_snapshot_consistency(
    facts: tuple[RankingPresentationFact, ...],
    *,
    authority: RankingPresentationFact,
) -> None:
    authority_values = (
        authority.tenant_id,
        authority.presented_at_utc,
        authority.visible_opportunity_count,
        authority.queue_policy_version,
        authority.ranking_policy_version,
        authority.surface,
        authority.producer,
    )
    for fact in facts[1:]:
        fact_values = (
            fact.tenant_id,
            fact.presented_at_utc,
            fact.visible_opportunity_count,
            fact.queue_policy_version,
            fact.ranking_policy_version,
            fact.surface,
            fact.producer,
        )
        if fact_values != authority_values:
            raise ValueError("queue snapshot presentation facts are internally inconsistent")


def _evaluate_cutoff(
    by_rank: dict[int, RankedOpportunityJudgment],
    *,
    cutoff: int,
    visible_opportunity_count: int,
) -> RankingCutoffEvaluation:
    evaluated_depth = min(cutoff, visible_opportunity_count)
    ranked = tuple(by_rank.get(rank) for rank in range(1, evaluated_depth + 1))
    observed = tuple(judgment for judgment in ranked if judgment is not None)
    judged = tuple(judgment for judgment in observed if judgment.relevance_grade is not None)
    coverage = _ratio(len(judged), evaluated_depth)
    population = _CutoffPopulation(
        cutoff=cutoff,
        evaluated_depth=evaluated_depth,
        observed_opportunity_count=len(observed),
        judged_opportunity_count=len(judged),
        unjudged_opportunity_count=evaluated_depth - len(judged),
        judgment_coverage=coverage,
    )
    if len(observed) != evaluated_depth:
        return _cutoff_evaluation(
            population,
            status=RankingCutoffStatus.INCOMPLETE_PRESENTATION,
            precision_at_k=None,
            ndcg_at_k=None,
        )
    if len(judged) != evaluated_depth:
        return _cutoff_evaluation(
            population,
            status=RankingCutoffStatus.INCOMPLETE_JUDGMENTS,
            precision_at_k=None,
            ndcg_at_k=None,
        )
    relevance = tuple(
        judgment.relevance_grade for judgment in judged if judgment.relevance_grade is not None
    )
    return _cutoff_evaluation(
        population,
        status=RankingCutoffStatus.READY,
        precision_at_k=_precision_at_k(relevance),
        ndcg_at_k=_ndcg_at_k(relevance),
    )


def _cutoff_evaluation(
    population: _CutoffPopulation,
    *,
    status: RankingCutoffStatus,
    precision_at_k: Decimal | None,
    ndcg_at_k: Decimal | None,
) -> RankingCutoffEvaluation:
    return RankingCutoffEvaluation(
        cutoff=population.cutoff,
        evaluated_depth=population.evaluated_depth,
        status=status,
        observed_opportunity_count=population.observed_opportunity_count,
        judged_opportunity_count=population.judged_opportunity_count,
        unjudged_opportunity_count=population.unjudged_opportunity_count,
        judgment_coverage=population.judgment_coverage,
        precision_at_k=precision_at_k,
        ndcg_at_k=ndcg_at_k,
    )


def _precision_at_k(relevance: tuple[RankingRelevanceGrade, ...]) -> Decimal:
    relevant_count = sum(grade >= RankingRelevanceGrade.USEFUL for grade in relevance)
    return _ratio(relevant_count, len(relevance))


def _ndcg_at_k(relevance: tuple[RankingRelevanceGrade, ...]) -> Decimal:
    actual = _discounted_cumulative_gain(relevance)
    ideal = _discounted_cumulative_gain(tuple(sorted(relevance, reverse=True)))
    if ideal == 0:
        return Decimal("0.000000")
    return _quantize(actual / ideal)


def _discounted_cumulative_gain(
    relevance: tuple[RankingRelevanceGrade, ...],
) -> Decimal:
    with localcontext() as context:
        context.prec = 40
        natural_log_two = Decimal(2).ln()
        return sum(
            (
                ((Decimal(2) ** int(grade)) - Decimal(1))
                / (Decimal(rank + 1).ln() / natural_log_two)
                for rank, grade in enumerate(relevance, start=1)
            ),
            start=Decimal(0),
        )


def _validate_cutoffs(cutoffs: tuple[int, ...]) -> tuple[int, ...]:
    if not cutoffs:
        raise ValueError("cutoffs is required")
    if any(not _is_integer(cutoff) or cutoff <= 0 for cutoff in cutoffs):
        raise ValueError("cutoffs must contain positive integers")
    if tuple(sorted(set(cutoffs))) != cutoffs:
        raise ValueError("cutoffs must be unique and sorted")
    unsupported = tuple(cutoff for cutoff in cutoffs if cutoff not in APPROVED_RANKING_CUTOFFS)
    if unsupported:
        raise ValueError(f"unsupported ranking cutoffs: {unsupported}")
    return cutoffs


def _validate_judgments(
    judgments: tuple[RankedOpportunityJudgment, ...],
    *,
    visible_opportunity_count: int,
) -> dict[int, RankedOpportunityJudgment]:
    by_rank: dict[int, RankedOpportunityJudgment] = {}
    for judgment in judgments:
        if not isinstance(judgment, RankedOpportunityJudgment):
            raise ValueError("judgments must use RankedOpportunityJudgment")
        if judgment.rank > visible_opportunity_count:
            raise ValueError("judgment rank exceeds visible_opportunity_count")
        if judgment.rank in by_rank:
            raise ValueError("judgment ranks must be unique")
        by_rank[judgment.rank] = judgment
    return by_rank


def _validate_visible_opportunity_count(value: int) -> None:
    if not _is_integer(value) or not 1 <= value <= MAX_PRESENTED_CANDIDATE_COUNT:
        raise ValueError(
            f"visible_opportunity_count must be between 1 and {MAX_PRESENTED_CANDIDATE_COUNT}"
        )


def _ratio(numerator: int, denominator: int) -> Decimal:
    return _quantize(Decimal(numerator) / Decimal(denominator))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


__all__ = [
    "APPROVED_RANKING_CUTOFFS",
    "MINIMUM_READY_SNAPSHOT_COUNT",
    "MAX_RANKING_PRESENTATION_FACTS",
    "RANKING_EVALUATION_POLICY_VERSION",
    "RankedOpportunityJudgment",
    "RankingCutoffAggregate",
    "RankingCutoffEvaluation",
    "RankingCutoffStatus",
    "RankingJudgmentSource",
    "RankingMetricSupportStatus",
    "RankingPresentationFact",
    "RankingQueueSnapshotEvaluation",
    "RankingRelevanceGrade",
    "RankingRelevanceFact",
    "RankingSnapshotEvaluation",
    "aggregate_ranking_evaluations",
    "derive_ranking_relevance",
    "downstream_relevance_grade",
    "evaluate_ranking_presentations",
    "evaluate_ranking_snapshot",
    "feedback_relevance_grade",
    "review_relevance_grade",
]
