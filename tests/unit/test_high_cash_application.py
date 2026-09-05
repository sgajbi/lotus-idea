from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from dataclasses import dataclass, replace
from decimal import Decimal

import pytest

from app.application.candidate_evaluation_acceptance import accept_candidate_evaluation
from app.application.candidate_expiry import CandidateExpiryDecision
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashFromCoreCommand,
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashFromCoreCommand,
    EvaluateHighCashSignalCommand,
    evaluate_and_persist_high_cash_signal,
    evaluate_and_persist_high_cash_signal_from_core,
    evaluate_high_cash_signal_from_core,
    evaluate_high_cash_signal_command,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    IdeaLifecycleStatus,
    LifecyclePersistenceDecision,
    ReviewAccessScope,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
)
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
ACCESS_SCOPE = ReviewAccessScope(
    tenant_id="tenant-a",
    book_id="book-advisor-001",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-001",
)


def source_ref(
    product_id: str, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def command(
    *,
    cash_weight: Decimal | None = Decimal("0.18"),
    entitlement_allowed: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> EvaluateHighCashSignalCommand:
    return EvaluateHighCashSignalCommand(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", freshness),
        cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness),
        cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1", freshness),
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        access_scope=ACCESS_SCOPE,
    )


def test_application_evaluates_high_cash_command_with_default_policy() -> None:
    result = evaluate_high_cash_signal_command(command())

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.score is not None
    assert result.candidate.score.policy_version == "idle-liquidity-v2"


@pytest.mark.parametrize(
    "accepted_at_utc",
    (
        datetime(2026, 6, 21, 10, 5),
        datetime(2026, 6, 21, 11, 5, tzinfo=timezone(timedelta(hours=1))),
    ),
)
def test_candidate_acceptance_rejects_untrusted_non_utc_control_time(
    accepted_at_utc: datetime,
) -> None:
    evaluation = evaluate_high_cash_signal_command(command())

    with pytest.raises(ValueError, match="accepted_at_utc must"):
        accept_candidate_evaluation(evaluation, accepted_at_utc=accepted_at_utc)


def test_application_preserves_entitlement_denied_as_blocked_domain_posture() -> None:
    result = evaluate_high_cash_signal_command(command(entitlement_allowed=False))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_application_preserves_stale_source_as_blocked_domain_posture() -> None:
    result = evaluate_high_cash_signal_command(command(freshness=EvidenceFreshness.STALE))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence | None = None
    error: Exception | None = None
    seen_request: CoreHighCashEvidenceRequest | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        if self.evidence is None:
            raise AssertionError("evidence must be configured")
        return self.evidence


def from_core_command() -> EvaluateHighCashFromCoreCommand:
    return EvaluateHighCashFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-idea",
        trace_id="trace-idea",
    )


def current_core_evidence(*, cash_weight: Decimal | None = Decimal("0.18")) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def test_application_fetches_core_source_evidence_before_high_cash_evaluation() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence())

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert source.seen_request.tenant_id == "tenant-a"
    assert source.seen_request.correlation_id == "corr-idea"
    assert source.seen_request.trace_id == "trace-idea"
    assert result.candidate is not None
    assert result.candidate.access_scope is not None
    assert result.candidate.access_scope.tenant_id == "tenant-a"


def test_core_backed_high_cash_candidate_identity_is_isolated_by_tenant() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence())

    tenant_a = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)
    tenant_b = evaluate_high_cash_signal_from_core(
        replace(from_core_command(), tenant_id="tenant-b"),
        core_source=source,
    )

    assert tenant_a.candidate is not None
    assert tenant_b.candidate is not None
    assert tenant_a.candidate.candidate_id != tenant_b.candidate.candidate_id
    assert tenant_a.candidate.access_scope is not None
    assert tenant_b.candidate.access_scope is not None
    assert tenant_a.candidate.access_scope.tenant_id == "tenant-a"
    assert tenant_b.candidate.access_scope.tenant_id == "tenant-b"


def test_application_blocks_source_backed_flow_when_core_denies_entitlement() -> None:
    source = RecordingCoreSource(error=CoreSourceEntitlementDenied())

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)
    assert result.candidate is None


def test_application_blocks_source_backed_flow_when_core_is_unavailable() -> None:
    source = RecordingCoreSource(error=CoreSourceUnavailable(code="upstream_timeout"))

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,)
    assert result.candidate is None


def test_application_does_not_infer_cash_weight_when_core_omits_source_reported_value() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence(cash_weight=None))

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert result.candidate is None


def persist_command(
    *,
    evaluation: EvaluateHighCashSignalCommand | None = None,
    idempotency_key: str = "signal-ingestion:high-cash:pb-001:2026-06-21",
    accepted_at_utc: datetime = EVALUATED_AT,
) -> EvaluateAndPersistHighCashSignalCommand:
    return EvaluateAndPersistHighCashSignalCommand(
        evaluation=evaluation or command(),
        idempotency_key=idempotency_key,
        actor_subject="signal-ingestion-worker",
        accepted_at_utc=accepted_at_utc,
    )


def test_application_persists_created_high_cash_candidate_with_audit_event() -> None:
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert result.persistence.record is not None
    assert result.persistence.record.audit_events[0].event_type == "idea.candidate.persisted"


def test_persisted_evaluation_separates_source_observation_from_server_acceptance() -> None:
    repository = InMemoryIdeaRepository()
    accepted_at = EVALUATED_AT + datetime.resolution

    result = evaluate_and_persist_high_cash_signal(
        persist_command(accepted_at_utc=accepted_at),
        repository=repository,
    )

    assert result.evaluation.signal is not None
    assert result.evaluation.signal.detected_at_utc == EVALUATED_AT
    assert result.evaluation.candidate is not None
    assert result.evaluation.candidate.created_at_utc == accepted_at
    assert result.evaluation.candidate.updated_at_utc == accepted_at
    assert result.evaluation.candidate.evidence_packet.created_at_utc == accepted_at
    assert result.persistence is not None
    assert result.persistence.record is not None
    assert result.persistence.record.persisted_at_utc == accepted_at
    assert result.persistence.audit_event is not None
    assert result.persistence.audit_event.occurred_at_utc == accepted_at


def test_application_replays_same_high_cash_idempotency_payload() -> None:
    repository = InMemoryIdeaRepository()
    first = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )

    replayed = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )

    assert first.persistence is not None
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert replayed.persistence.record == first.persistence.record


def test_candidate_persistence_replay_retains_original_acceptance_time() -> None:
    repository = InMemoryIdeaRepository()
    first_accepted_at = EVALUATED_AT + datetime.resolution
    first = evaluate_and_persist_high_cash_signal(
        persist_command(accepted_at_utc=first_accepted_at),
        repository=repository,
    )

    replayed = evaluate_and_persist_high_cash_signal(
        persist_command(accepted_at_utc=first_accepted_at + datetime.resolution),
        repository=repository,
    )

    assert first.persistence is not None
    assert first.persistence.record is not None
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert replayed.persistence.record == first.persistence.record
    assert replayed.persistence.record is not None
    assert replayed.persistence.record.persisted_at_utc == first_accepted_at


def test_application_detects_high_cash_idempotency_payload_conflict() -> None:
    repository = InMemoryIdeaRepository()
    evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )

    conflict = evaluate_and_persist_high_cash_signal(
        persist_command(evaluation=command(cash_weight=Decimal("0.20"))),
        repository=repository,
    )

    assert conflict.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert conflict.persistence is not None
    assert conflict.persistence.decision is CandidatePersistenceDecision.CONFLICT
    assert conflict.persistence.audit_event is None


def test_application_does_not_persist_blocked_high_cash_evaluation() -> None:
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_high_cash_signal(
        persist_command(evaluation=command(cash_weight=None)),
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_authoritative_non_eligible_reevaluation_expires_existing_candidate_once() -> None:
    repository = InMemoryIdeaRepository()
    created = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )
    assert created.persistence is not None
    assert created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    reevaluated_at = EVALUATED_AT + timedelta(hours=1)
    non_eligible = replace(
        command(cash_weight=Decimal("0.10")),
        evaluated_at_utc=reevaluated_at,
    )

    expired = evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=non_eligible,
            idempotency_key="signal-ingestion:high-cash:pb-001:below-threshold",
        ),
        repository=repository,
    )
    repeated = evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=non_eligible,
            idempotency_key="signal-ingestion:high-cash:pb-001:below-threshold-repeat",
        ),
        repository=repository,
    )

    assert expired.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert expired.persistence is None
    assert expired.expiry is not None
    assert expired.expiry.decision is CandidateExpiryDecision.EXPIRED
    assert expired.expiry.persistence is not None
    assert expired.expiry.persistence.decision is LifecyclePersistenceDecision.ACCEPTED
    assert expired.expiry.persistence.record is not None
    record = expired.expiry.persistence.record
    assert record.candidate.candidate_id == candidate_id
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
    assert record.audit_events[-1].event_type == "idea.lifecycle.transitioned"
    assert record.audit_events[-1].attributes["reason_codes"] == (
        "opportunity_no_longer_eligible,below_materiality"
    )
    assert repeated.expiry is not None
    assert repeated.expiry.decision is CandidateExpiryDecision.ALREADY_EXPIRED
    snapshot = repository.snapshot()
    assert len(snapshot.candidate_records[candidate_id].lifecycle_history) == 1
    assert f"candidate-expiry:{candidate_id}:material-version:1" in snapshot.idempotency_records


def test_non_eligible_evaluation_without_candidate_is_non_mutating() -> None:
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_high_cash_signal(
        persist_command(evaluation=command(cash_weight=Decimal("0.10"))),
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.expiry is not None
    assert result.expiry.decision is CandidateExpiryDecision.NOT_FOUND
    assert repository.snapshot().candidate_records == {}


def test_authoritative_non_eligible_reevaluation_preserves_closed_candidate() -> None:
    repository = InMemoryIdeaRepository()
    created = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )
    assert created.persistence is not None
    assert created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    repository.transition_candidate(
        candidate_id,
        IdeaLifecycleStatus.CLOSED,
        actor_subject="candidate-closure-test",
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=30),
    )

    result = evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=replace(
                command(cash_weight=Decimal("0.10")),
                evaluated_at_utc=EVALUATED_AT + timedelta(hours=1),
            ),
            idempotency_key="signal-ingestion:high-cash:pb-001:closed",
        ),
        repository=repository,
    )

    assert result.expiry is not None
    assert result.expiry.decision is CandidateExpiryDecision.TERMINAL_STATE_PRESERVED
    record = repository.snapshot().candidate_records[candidate_id]
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.CLOSED
    assert len(record.lifecycle_history) == 1


def test_blocked_reevaluation_does_not_expire_existing_candidate() -> None:
    repository = InMemoryIdeaRepository()
    created = evaluate_and_persist_high_cash_signal(
        persist_command(),
        repository=repository,
    )
    assert created.persistence is not None
    assert created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id

    blocked = evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=replace(
                command(freshness=EvidenceFreshness.STALE),
                evaluated_at_utc=EVALUATED_AT + timedelta(hours=1),
            ),
            idempotency_key="signal-ingestion:high-cash:pb-001:stale",
        ),
        repository=repository,
    )

    assert blocked.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert blocked.expiry is None
    record = repository.snapshot().candidate_records[candidate_id]
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert record.lifecycle_history == ()


def test_materially_changed_condition_reopens_after_automatic_expiry() -> None:
    repository = InMemoryIdeaRepository()
    evaluate_and_persist_high_cash_signal(persist_command(), repository=repository)
    evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=command(cash_weight=Decimal("0.10")),
            idempotency_key="signal-ingestion:high-cash:pb-001:expire",
        ),
        repository=repository,
    )

    reopened = evaluate_and_persist_high_cash_signal(
        persist_command(
            evaluation=command(cash_weight=Decimal("0.20")),
            idempotency_key="signal-ingestion:high-cash:pb-001:recur",
        ),
        repository=repository,
    )

    assert reopened.persistence is not None
    assert (
        reopened.persistence.decision is CandidatePersistenceDecision.RECURRENT_CONDITION_REOPENED
    )
    assert reopened.persistence.record is not None
    assert reopened.persistence.record.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert reopened.persistence.record.candidate.identity.material_version == 2


def test_application_persists_core_backed_high_cash_candidate() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence())
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_high_cash_signal_from_core(
        EvaluateAndPersistHighCashFromCoreCommand(
            evaluation=from_core_command(),
            idempotency_key="signal-ingestion:high-cash:core:pb-001:2026-06-21",
            actor_subject="signal-ingestion-worker",
            accepted_at_utc=EVALUATED_AT,
        ),
        core_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_core_ingestion_retires_candidate_when_source_condition_is_no_longer_eligible() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=current_core_evidence())
    initial_command = EvaluateAndPersistHighCashFromCoreCommand(
        evaluation=from_core_command(),
        idempotency_key="signal-ingestion:high-cash:core:pb-001:initial",
        actor_subject="signal-ingestion-worker",
        accepted_at_utc=EVALUATED_AT,
    )
    created = evaluate_and_persist_high_cash_signal_from_core(
        initial_command,
        core_source=source,
        repository=repository,
    )
    assert created.persistence is not None
    assert created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    source.evidence = current_core_evidence(cash_weight=Decimal("0.10"))

    retired = evaluate_and_persist_high_cash_signal_from_core(
        replace(
            initial_command,
            evaluation=replace(
                from_core_command(),
                evaluated_at_utc=EVALUATED_AT + timedelta(hours=1),
            ),
            idempotency_key="signal-ingestion:high-cash:core:pb-001:not-eligible",
        ),
        core_source=source,
        repository=repository,
    )

    assert retired.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert retired.expiry is not None
    assert retired.expiry.decision is CandidateExpiryDecision.EXPIRED
    assert (
        repository.snapshot().candidate_records[candidate_id].candidate.lifecycle_status
        is IdeaLifecycleStatus.EXPIRED
    )


def test_core_source_failure_does_not_retire_existing_candidate() -> None:
    repository = InMemoryIdeaRepository()
    source = RecordingCoreSource(evidence=current_core_evidence())
    initial_command = EvaluateAndPersistHighCashFromCoreCommand(
        evaluation=from_core_command(),
        idempotency_key="signal-ingestion:high-cash:core:pb-001:initial",
        actor_subject="signal-ingestion-worker",
        accepted_at_utc=EVALUATED_AT,
    )
    created = evaluate_and_persist_high_cash_signal_from_core(
        initial_command,
        core_source=source,
        repository=repository,
    )
    assert created.persistence is not None
    assert created.persistence.record is not None
    candidate_id = created.persistence.record.candidate.candidate_id
    source.error = CoreSourceUnavailable(code="upstream_timeout")

    blocked = evaluate_and_persist_high_cash_signal_from_core(
        replace(
            initial_command,
            idempotency_key="signal-ingestion:high-cash:core:pb-001:blocked",
        ),
        core_source=source,
        repository=repository,
    )

    assert blocked.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert blocked.expiry is None
    assert (
        repository.snapshot().candidate_records[candidate_id].candidate.lifecycle_status
        is IdeaLifecycleStatus.GENERATED
    )


def test_application_validates_persistence_command_identity() -> None:
    repository = InMemoryIdeaRepository()

    try:
        evaluate_and_persist_high_cash_signal(
            persist_command(idempotency_key=" "),
            repository=repository,
        )
    except ValueError as exc:
        assert str(exc) == "idempotency_key is required"
    else:
        raise AssertionError("expected blank idempotency key to fail")
