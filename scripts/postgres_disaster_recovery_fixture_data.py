# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.domain import (
    CandidateEvidenceIdentity,
    CandidatePresentationReceipt,
    CandidateScorePolicyVersion,
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    FeedbackCommand,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackOutcome,
    FeedbackReason,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    ReasonCode,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewChannel,
    ReviewDecisionCommand,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)

FIXTURE_TIME = datetime(2026, 7, 11, 5, 0, tzinfo=UTC)
FIXTURE_CANDIDATE_PREFIX = "idea_dr_fixture"


def high_cash_candidate(*, portfolio_id: str = "portfolio-dr-fixture") -> IdeaCandidate:
    refs = _source_refs()
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=date(2026, 7, 11),
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=FIXTURE_TIME,
            access_scope=_access_scope(portfolio_id),
        ),
        HighCashSignalPolicy(
            policy_version=CandidateScorePolicyVersion.HIGH_CASH.value,
            cash_weight_threshold=Decimal("0.12"),
        ),
    )
    if result.candidate is None:
        raise RuntimeError("fixture signal did not create a candidate")
    return result.candidate


def review_command(
    candidate: IdeaCandidate | None = None,
    *,
    review_id: str = "dr-fixture-review-001",
) -> ReviewDecisionCommand:
    source_candidate = candidate or high_cash_candidate()
    assert source_candidate.access_scope is not None
    return ReviewDecisionCommand(
        review_id=review_id,
        action=ReviewAction.APPROVE_FOR_CONVERSION,
        actor=_actor(portfolio_id=source_candidate.access_scope.portfolio_id),
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        decided_at_utc=FIXTURE_TIME + timedelta(minutes=2),
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(source_candidate),
        review_channel=ReviewChannel.WORKBENCH,
        presentation_receipt_id=f"dr-fixture-presentation-{source_candidate.candidate_id}",
    )


def feedback_command() -> FeedbackCommand:
    return FeedbackCommand(
        feedback_id="dr-fixture-feedback-001",
        actor=_actor(),
        outcome=FeedbackOutcome.USEFUL,
        reason=FeedbackReason.RELEVANT,
        taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
        recorded_at_utc=FIXTURE_TIME + timedelta(minutes=3),
    )


def conversion_command(
    candidate: IdeaCandidate | None = None,
    *,
    expected_review_id: str = "dr-fixture-review-001",
) -> ConversionIntentCommand:
    source_candidate = candidate or high_cash_candidate()
    return ConversionIntentCommand(
        conversion_intent_id="dr-fixture-conversion-intent-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        actor_subject="dr-fixture-advisor",
        idempotency_key="dr-fixture-conversion-intent",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=FIXTURE_TIME + timedelta(minutes=4),
        expected_review_id=expected_review_id,
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(source_candidate),
    )


def presentation_receipt(candidate: IdeaCandidate) -> CandidatePresentationReceipt:
    assert candidate.access_scope is not None
    assert candidate.score is not None
    return CandidatePresentationReceipt(
        receipt_id=f"dr-fixture-presentation-{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        tenant_id=candidate.access_scope.tenant_id,
        presented_at_utc=FIXTURE_TIME + timedelta(minutes=1),
        rank_at_presentation=1,
        visible_candidate_count=1,
        queue_snapshot_digest="sha256:" + "a" * 64,
        queue_policy_version="idea-review-queue-v1",
        ranking_policy_version=candidate.score.policy_version,
        candidate_material_version=candidate.identity.material_version,
        candidate_evidence_version=candidate.identity.evidence_version,
        accepted_at_utc=FIXTURE_TIME + timedelta(minutes=1),
    )


def conversion_outcome_command() -> ConversionOutcomeCommand:
    return ConversionOutcomeCommand(
        conversion_outcome_id="dr-fixture-conversion-outcome-001",
        status=ConversionOutcomeStatus.ACCEPTED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=1,
        recorded_at_utc=FIXTURE_TIME + timedelta(minutes=5),
        downstream_reference="dr-fixture-report-pack-001",
        actor_subject="lotus-report",
    )


def report_pack_command() -> ReportEvidencePackCommand:
    return ReportEvidencePackCommand(
        report_evidence_pack_id="dr-fixture-report-pack-001",
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject="dr-fixture-advisor",
        idempotency_key="dr-fixture-report-pack",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=FIXTURE_TIME + timedelta(minutes=6),
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
    )


def _source_refs() -> tuple[SourceRef, ...]:
    products = (
        "lotus-core:PortfolioStateSnapshot:v1",
        "lotus-core:HoldingsAsOf:v1",
        "lotus-core:PortfolioCashMovementSummary:v1",
        "lotus-core:PortfolioCashflowProjection:v1",
    )
    return tuple(
        SourceRef(
            product_id=product,
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route=f"/dr-fixture/{index}",
            as_of_date=date(2026, 7, 11),
            generated_at_utc=FIXTURE_TIME,
            content_hash=f"sha256:dr-fixture-source-{index}",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )
        for index, product in enumerate(products, start=1)
    )


def _access_scope(portfolio_id: str) -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-dr-fixture",
        book_id="book-dr-fixture",
        portfolio_id=portfolio_id,
        client_id="client-dr-fixture",
    )


def _actor(*, portfolio_id: str = "portfolio-dr-fixture") -> ReviewActorContext:
    return ReviewActorContext(
        actor_subject="dr-fixture-advisor",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-dr-fixture"}),
        book_ids=frozenset({"book-dr-fixture"}),
        portfolio_ids=frozenset({portfolio_id}),
        client_ids=frozenset({"client-dr-fixture"}),
    )
