from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.conversion_governance import current_conversion_outcome
from app.domain.persistence_models import CandidatePersistenceRecord, IdeaRepositorySnapshot
from app.domain.presentation_receipts import CandidatePresentationReceipt
from app.domain.ranking_evaluation import (
    MAX_RANKING_PRESENTATION_FACTS,
    MINIMUM_READY_SNAPSHOT_COUNT,
    RANKING_EVALUATION_POLICY_VERSION,
    RankedOpportunityJudgment,
    RankingCutoffAggregate,
    RankingJudgmentSource,
    RankingPresentationFact,
    RankingRelevanceFact,
    RankingRelevanceGrade,
    RankingStabilityAggregate,
    aggregate_ranking_evaluations,
    derive_ranking_relevance,
    downstream_relevance_grade,
    evaluate_ranking_presentations,
    evaluate_ranking_stability,
    feedback_relevance_grade,
    review_relevance_grade,
)


class RankingQualityDataError(ValueError):
    pass


class RankingQualityBoundExceeded(ValueError):
    pass


def build_ranking_quality(
    facts: tuple[RankingPresentationFact, ...],
) -> tuple[tuple[RankingCutoffAggregate, ...], RankingStabilityAggregate]:
    try:
        evaluations = evaluate_ranking_presentations(facts)
        return aggregate_ranking_evaluations(evaluations), evaluate_ranking_stability(evaluations)
    except ValueError as exc:
        raise RankingQualityDataError(str(exc)) from exc


def build_ranking_presentation_facts(
    snapshot: IdeaRepositorySnapshot,
    *,
    records: tuple[CandidatePersistenceRecord, ...],
    evaluated_at_utc: datetime,
) -> tuple[RankingPresentationFact, ...]:
    records_by_candidate = {record.candidate.candidate_id: record for record in records}
    facts: list[RankingPresentationFact] = []
    for receipt in sorted(
        snapshot.presentation_receipts.values(),
        key=lambda item: (item.queue_snapshot_digest, item.rank_at_presentation, item.receipt_id),
    ):
        record = records_by_candidate.get(receipt.candidate_id)
        if record is None or receipt.accepted_at_utc > evaluated_at_utc:
            continue
        candidate = record.candidate
        if candidate.access_scope is None or receipt.tenant_id != candidate.access_scope.tenant_id:
            raise RankingQualityDataError(
                "presentation receipt tenant does not match its cohort candidate"
            )
        evidence_hash = presentation_evidence_hash(record, receipt)
        facts.append(
            RankingPresentationFact(
                queue_snapshot_digest=receipt.queue_snapshot_digest,
                tenant_id=receipt.tenant_id,
                presented_at_utc=receipt.presented_at_utc,
                visible_opportunity_count=receipt.visible_candidate_count,
                queue_policy_version=receipt.queue_policy_version,
                ranking_policy_version=receipt.ranking_policy_version,
                surface=receipt.surface,
                producer=receipt.producer,
                economic_identity_id=candidate.identity.business_identity_id,
                judgment=RankedOpportunityJudgment(
                    rank=receipt.rank_at_presentation,
                    relevance_grade=_ranking_relevance_grade(
                        record,
                        receipt=receipt,
                        evidence_hash=evidence_hash,
                        evaluated_at_utc=evaluated_at_utc,
                    ),
                ),
            )
        )
        if len(facts) > MAX_RANKING_PRESENTATION_FACTS:
            raise RankingQualityBoundExceeded(
                "opportunity effectiveness exceeds the "
                f"{MAX_RANKING_PRESENTATION_FACTS} ranking presentation fact bound"
            )
    return tuple(facts)


def presentation_evidence_hash(
    record: CandidatePersistenceRecord,
    receipt: CandidatePresentationReceipt,
) -> str:
    matching_versions = tuple(
        entry
        for entry in record.version_history
        if entry.material_version == receipt.candidate_material_version
        and entry.evidence_version == receipt.candidate_evidence_version
        and entry.recorded_at_utc <= receipt.accepted_at_utc
    )
    if len(matching_versions) > 1:
        raise RankingQualityDataError(
            "presentation receipt resolves to multiple candidate versions"
        )
    if matching_versions:
        return matching_versions[0].evidence_hash
    candidate = record.candidate
    if (
        candidate.identity.material_version == receipt.candidate_material_version
        and candidate.identity.evidence_version == receipt.candidate_evidence_version
        and candidate.updated_at_utc <= receipt.accepted_at_utc
    ):
        return candidate.evidence_packet.lineage_ref.content_hash
    raise RankingQualityDataError(
        "presentation receipt does not resolve to a durable candidate version"
    )


def ranking_quality_payload(
    quality: tuple[RankingCutoffAggregate, ...],
    stability: RankingStabilityAggregate,
) -> dict[str, Any]:
    return {
        "policyVersion": RANKING_EVALUATION_POLICY_VERSION,
        "minimumReadySnapshotCount": MINIMUM_READY_SNAPSHOT_COUNT,
        "recallStatus": "unavailable_incomplete_relevant_set",
        "cutoffs": [_cutoff_payload(item) for item in quality],
        "stability": {
            "comparableSnapshotPairCount": stability.comparable_snapshot_pair_count,
            "meanNormalizedStability": _decimal_payload(stability.mean_normalized_stability),
        },
    }


def _cutoff_payload(item: RankingCutoffAggregate) -> dict[str, Any]:
    return {
        "cutoff": item.cutoff,
        "snapshotCount": item.snapshot_count,
        "readySnapshotCount": item.ready_snapshot_count,
        "incompletePresentationSnapshotCount": item.incomplete_presentation_snapshot_count,
        "incompleteJudgmentSnapshotCount": item.incomplete_judgment_snapshot_count,
        "judgedOpportunityCount": item.judged_opportunity_count,
        "evaluatedOpportunityCount": item.evaluated_opportunity_count,
        "judgmentCoverage": _decimal_payload(item.judgment_coverage),
        "supportStatus": item.support_status.value,
        "meanPrecisionAtK": _decimal_payload(item.mean_precision_at_k),
        "meanNdcgAtK": _decimal_payload(item.mean_ndcg_at_k),
        "recallAtK": None,
    }


def _ranking_relevance_grade(
    record: CandidatePersistenceRecord,
    *,
    receipt: CandidatePresentationReceipt,
    evidence_hash: str,
    evaluated_at_utc: datetime,
) -> RankingRelevanceGrade | None:
    valid_until = _presentation_version_valid_until(record, receipt)
    relevance_facts: list[RankingRelevanceFact] = []
    matching_intents = tuple(
        intent
        for intent in record.conversion_intents
        if intent.evidence_content_hash == evidence_hash
        and receipt.accepted_at_utc <= intent.accepted_at_utc <= evaluated_at_utc
        and (valid_until is None or intent.accepted_at_utc < valid_until)
    )
    matching_intent_ids = {intent.intent.conversion_intent_id for intent in matching_intents}
    for intent_id in matching_intent_ids:
        outcomes = tuple(
            outcome
            for outcome in record.conversion_outcomes
            if outcome.conversion_intent_id == intent_id
            and receipt.accepted_at_utc <= outcome.accepted_at_utc <= evaluated_at_utc
        )
        current = current_conversion_outcome(outcomes)
        if current is not None and (grade := downstream_relevance_grade(current.outcome.status)):
            relevance_facts.append(
                RankingRelevanceFact(
                    occurred_at_utc=current.accepted_at_utc,
                    source=RankingJudgmentSource.DOWNSTREAM_OUTCOME,
                    relevance_grade=grade,
                )
            )
    for decision in record.review_decisions:
        if decision.evidence_content_hash != evidence_hash:
            continue
        grade = review_relevance_grade(decision.action)
        if grade is not None:
            relevance_facts.append(
                RankingRelevanceFact(
                    occurred_at_utc=decision.accepted_at_utc,
                    source=RankingJudgmentSource.ADVISER_REVIEW,
                    relevance_grade=grade,
                )
            )
    for event in record.feedback_events:
        if event.evidence_content_hash == evidence_hash:
            relevance_facts.append(
                RankingRelevanceFact(
                    occurred_at_utc=event.accepted_at_utc,
                    source=RankingJudgmentSource.ADVISER_FEEDBACK,
                    relevance_grade=feedback_relevance_grade(event.feedback.outcome),
                )
            )
    try:
        return derive_ranking_relevance(
            relevance_facts,
            presented_at_utc=receipt.presented_at_utc,
            evaluated_at_utc=evaluated_at_utc,
            valid_until_utc=valid_until,
        )
    except ValueError as exc:
        raise RankingQualityDataError(str(exc)) from exc


def _presentation_version_valid_until(
    record: CandidatePersistenceRecord,
    receipt: CandidatePresentationReceipt,
) -> datetime | None:
    next_version_times = [
        entry.recorded_at_utc
        for entry in record.version_history
        if entry.recorded_at_utc > receipt.accepted_at_utc
        and (
            entry.material_version != receipt.candidate_material_version
            or entry.evidence_version != receipt.candidate_evidence_version
        )
    ]
    candidate = record.candidate
    if candidate.updated_at_utc > receipt.accepted_at_utc and (
        candidate.identity.material_version != receipt.candidate_material_version
        or candidate.identity.evidence_version != receipt.candidate_evidence_version
    ):
        next_version_times.append(candidate.updated_at_utc)
    return min(next_version_times) if next_version_times else None


def _decimal_payload(value: Decimal | None) -> str | None:
    return format(value.normalize(), "f") if value is not None else None


__all__ = [
    "RankingQualityBoundExceeded",
    "RankingQualityDataError",
    "build_ranking_presentation_facts",
    "build_ranking_quality",
    "presentation_evidence_hash",
    "ranking_quality_payload",
]
