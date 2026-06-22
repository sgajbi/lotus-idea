from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.runtime_trust_telemetry import (
    build_runtime_trust_telemetry_preview,
    build_runtime_trust_telemetry_snapshot,
)
from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)
from scripts.generate_runtime_trust_telemetry_preview import (
    runtime_trust_telemetry_preview_payload,
)


AS_OF_DATE = date(2026, 6, 21)
OBSERVED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_runtime_trust_telemetry_preview_reports_empty_blocked_posture() -> None:
    snapshot = build_runtime_trust_telemetry_preview(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    )

    assert snapshot.repository == "lotus-idea"
    assert snapshot.product_id == "lotus-idea:IdeaCandidate:v1"
    assert snapshot.generated_at_utc == OBSERVED_AT
    assert snapshot.candidate_snapshot_count == 0
    assert snapshot.current_source_ref_count == 0
    assert snapshot.stale_or_unavailable_source_ref_count == 0
    assert snapshot.lineage_materialized is False
    assert snapshot.runtime_telemetry_backed is True
    assert snapshot.platform_certified is False
    assert snapshot.certification_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.certification_blockers[:2] == (
        "runtime_candidate_snapshot_missing",
        "durable_repository_not_configured",
    )


def test_runtime_trust_telemetry_preview_counts_source_safe_repository_state() -> None:
    repository = InMemoryIdeaRepository()
    first = _persist_high_cash_candidate(repository, suffix="first")
    second = _persist_high_cash_candidate(repository, suffix="second")

    snapshot = build_runtime_trust_telemetry_preview(
        repository=repository,
        durable_storage_backed=True,
        generated_at_utc=OBSERVED_AT,
    )

    assert first != second
    assert snapshot.candidate_snapshot_count == 2
    assert snapshot.current_source_ref_count == 8
    assert snapshot.stale_or_unavailable_source_ref_count == 0
    assert snapshot.source_authority_counts == {"lotus-core": 8}
    assert snapshot.freshness_counts == {"current": 8}
    assert snapshot.supportability_counts == {"ready": 2}
    assert snapshot.lifecycle_counts == {"generated": 2}
    assert snapshot.lineage_materialized is True
    assert "durable_repository_not_configured" not in snapshot.certification_blockers
    assert "platform_mesh_certification_missing" in snapshot.certification_blockers


def test_runtime_trust_telemetry_preview_rejects_naive_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_runtime_trust_telemetry_preview(
            repository=InMemoryIdeaRepository(),
            durable_storage_backed=False,
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
        )


def test_runtime_trust_telemetry_preview_payload_is_source_safe() -> None:
    snapshot = build_runtime_trust_telemetry_preview(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    )

    payload = runtime_trust_telemetry_preview_payload(snapshot)
    rendered = repr(payload)

    assert payload["generatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["certificationStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert "candidateId" not in rendered
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "route" not in rendered
    assert "contentHash" not in rendered


def test_runtime_trust_telemetry_snapshot_reports_empty_blocked_contract_posture() -> None:
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()

    assert snapshot["contract_id"] == "lotus-domain-product-trust-telemetry-snapshot"
    assert snapshot["product_id"] == "lotus-idea:IdeaCandidate:v1"
    assert snapshot["freshness"]["freshness_state"] == "unknown"
    assert snapshot["completeness_status"] == "unknown"
    assert snapshot["reconciliation_status"] == "unknown"
    assert snapshot["data_quality_status"] == "quality_unknown"
    assert snapshot["lineage"]["lineage_materialized"] is False
    assert snapshot["blocking"]["blocked"] is True
    assert "runtime_candidate_snapshot_missing" in snapshot["blocking"]["blocked_reason"]
    assert snapshot["observed_trust_metadata"] == {}


def test_runtime_trust_telemetry_snapshot_materializes_source_safe_runtime_evidence() -> None:
    repository = InMemoryIdeaRepository()
    _persist_high_cash_candidate(repository, suffix="first")

    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=repository,
        durable_storage_backed=True,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()
    observed_metadata = snapshot["observed_trust_metadata"]
    rendered = repr(snapshot)

    assert snapshot["freshness"]["freshness_state"] == "current"
    assert snapshot["freshness"]["age_seconds"] == 0
    assert snapshot["completeness_status"] == "partial"
    assert snapshot["reconciliation_status"] == "not_applicable"
    assert snapshot["data_quality_status"] == "quality_passed"
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert observed_metadata["product_name"] == "IdeaCandidate"
    assert observed_metadata["as_of_date"] == "2026-06-21"
    assert observed_metadata["source_batch_fingerprint"] == "source-safe-runtime-aggregate"
    assert "platform_mesh_certification_missing" in snapshot["blocking"]["blocked_reason"]
    assert "candidate_id" not in rendered
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "content_hash" not in rendered
    assert "/source-owned/" not in rendered


def _persist_high_cash_candidate(repository: InMemoryIdeaRepository, *, suffix: str) -> str:
    result = evaluate_high_cash_signal(_high_cash_input(suffix=suffix), _policy())
    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    repository.persist_candidate(
        result.candidate,
        idempotency_key=f"runtime-trust-telemetry-{suffix}",
        payload={"suffix": suffix},
        actor_subject="platform-operator",
        occurred_at_utc=OBSERVED_AT,
    )
    return result.candidate.candidate_id


def _policy() -> HighCashSignalPolicy:
    return HighCashSignalPolicy(
        policy_version="idle-liquidity-v1",
        cash_weight_threshold=Decimal("0.12"),
        candidate_score=Decimal("82"),
    )


def _high_cash_input(*, suffix: str) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref("lotus-core:PortfolioStateSnapshot:v1", suffix=suffix),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1", suffix=suffix),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            suffix=suffix,
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            suffix=suffix,
        ),
        evaluated_at_utc=OBSERVED_AT,
    )


def _source_ref(product_id: str, *, suffix: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/source-owned/{reference}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=OBSERVED_AT,
        content_hash=f"sha256:{product_id}:{suffix}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
