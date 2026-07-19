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
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    FeedbackCommand,
    FeedbackOutcome,
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
    ReviewDecisionCommand,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)

FIXTURE_TIME = datetime(2026, 7, 11, 5, 0, tzinfo=UTC)
FIXTURE_CANDIDATE_PREFIX = "idea_dr_fixture"


def high_cash_candidate() -> IdeaCandidate:
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
            access_scope=_access_scope(),
        ),
        HighCashSignalPolicy(
            policy_version="dr-fixture-idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    if result.candidate is None:
        raise RuntimeError("fixture signal did not create a candidate")
    return result.candidate


def review_command() -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id="dr-fixture-review-001",
        action=ReviewAction.APPROVE_FOR_CONVERSION,
        actor=_actor(),
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        decided_at_utc=FIXTURE_TIME + timedelta(minutes=2),
    )


def feedback_command() -> FeedbackCommand:
    return FeedbackCommand(
        feedback_id="dr-fixture-feedback-001",
        actor=_actor(),
        outcome=FeedbackOutcome.USEFUL,
        reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
        recorded_at_utc=FIXTURE_TIME + timedelta(minutes=3),
    )


def conversion_command() -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id="dr-fixture-conversion-intent-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        actor_subject="dr-fixture-advisor",
        idempotency_key="dr-fixture-conversion-intent",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=FIXTURE_TIME + timedelta(minutes=4),
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


def _access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-dr-fixture",
        book_id="book-dr-fixture",
        portfolio_id="portfolio-dr-fixture",
        client_id="client-dr-fixture",
    )


def _actor() -> ReviewActorContext:
    return ReviewActorContext(
        actor_subject="dr-fixture-advisor",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-dr-fixture"}),
        book_ids=frozenset({"book-dr-fixture"}),
        portfolio_ids=frozenset({"portfolio-dr-fixture"}),
        client_ids=frozenset({"client-dr-fixture"}),
    )
