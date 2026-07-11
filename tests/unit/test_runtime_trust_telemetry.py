from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
import json
from pathlib import Path

import pytest

from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryPreview,
    RuntimeTrustTelemetryProductPosture,
    build_runtime_trust_telemetry_preview,
    build_runtime_trust_telemetry_snapshot,
)
from app.ports.idea_repository import RuntimeTrustTelemetryRepositorySummary
from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    InMemoryIdeaRepository,
    IdeaRepositorySnapshot,
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
    assert {posture.product_id for posture in snapshot.product_postures} == (
        _declared_product_ids()
    )
    assert (
        _product_posture(
            snapshot,
            "lotus-idea:OpportunitySignalCandidate:v1",
        ).coverage_status
        == "blocked_not_runtime_backed"
    )
    assert (
        _product_posture(
            snapshot,
            "lotus-idea:IdeaTrustTelemetry:v1",
        ).coverage_status
        == "runtime_backed"
    )
    assert snapshot.candidate_snapshot_count == 0
    assert snapshot.data_lifecycle_state_counts == {}
    assert snapshot.lifecycle_control_missing_count == 0
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
    assert snapshot.data_lifecycle_state_counts == {"process_local_uncontrolled": 2}
    assert snapshot.lifecycle_control_missing_count == 2
    assert snapshot.lineage_materialized is True
    assert (
        _product_posture(
            snapshot,
            "lotus-idea:IdeaCandidate:v1",
        ).observed_record_count
        == 2
    )
    assert (
        _product_posture(
            snapshot,
            "lotus-idea:IdeaEvidencePacket:v1",
        ).source_batch_evidence_available
        is True
    )
    assert "durable_repository_not_configured" not in snapshot.certification_blockers
    assert "data_lifecycle_controls_missing" in snapshot.certification_blockers
    assert "platform_mesh_certification_missing" in snapshot.certification_blockers


def test_runtime_trust_telemetry_uses_repository_projection_without_snapshot() -> None:
    repository = _ProjectionOnlyRuntimeTrustTelemetryRepository()

    preview = build_runtime_trust_telemetry_preview(
        repository=repository,
        durable_storage_backed=True,
        generated_at_utc=OBSERVED_AT,
    )
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=repository,
        durable_storage_backed=True,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()

    assert repository.summary_call_count == 3
    assert preview.candidate_snapshot_count == 2
    assert preview.current_source_ref_count == 7
    assert preview.stale_or_unavailable_source_ref_count == 1
    assert preview.source_authority_counts == {"lotus-core": 7, "lotus-risk": 1}
    assert preview.freshness_counts == {"current": 7, "stale": 1}
    assert preview.supportability_counts == {"ready": 2}
    assert preview.lifecycle_counts == {"generated": 2}
    assert preview.data_lifecycle_state_counts == {"active": 1, "held": 1}
    assert preview.retention_expired_count == 1
    assert preview.lifecycle_control_missing_count == 0
    assert preview.review_decision_count == 1
    assert preview.feedback_event_count == 1
    assert preview.conversion_intent_count == 2
    assert preview.conversion_outcome_count == 1
    assert preview.report_evidence_pack_count == 3
    assert preview.lineage_materialized is True
    assert snapshot["freshness"]["freshness_state"] == "stale"
    assert snapshot["freshness"]["age_seconds"] == 600
    assert snapshot["data_quality_status"] == "quality_warning"
    assert snapshot["data_lifecycle"] == {
        "state_counts": {"active": 1, "held": 1},
        "retention_expired_count": 1,
        "lifecycle_control_missing_count": 0,
        "certification_status": "not_certified",
        "supported_feature_promoted": False,
    }
    assert snapshot["observed_trust_metadata"]["as_of_date"] == "2026-06-21"


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
    assert {posture["product_id"] for posture in snapshot["product_coverage"]} == (
        _declared_product_ids()
    )
    assert (
        _snapshot_product_posture(
            snapshot,
            "lotus-idea:OpportunitySignalCandidate:v1",
        )["coverage_status"]
        == "blocked_not_runtime_backed"
    )
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
    assert (
        _snapshot_product_posture(
            snapshot,
            "lotus-idea:IdeaCandidate:v1",
        )["coverage_status"]
        == "runtime_backed"
    )
    assert observed_metadata["product_name"] == "IdeaCandidate"
    assert observed_metadata["as_of_date"] == "2026-06-21"
    assert observed_metadata["source_batch_fingerprint"] == "source-safe-runtime-aggregate"
    assert "platform_mesh_certification_missing" in snapshot["blocking"]["blocked_reason"]
    assert "candidate_id" not in rendered
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "content_hash" not in rendered
    assert "/source-owned/" not in rendered


def test_runtime_trust_telemetry_snapshot_reports_stale_source_evidence() -> None:
    repository = InMemoryIdeaRepository()
    _persist_high_cash_candidate(
        repository,
        suffix="stale",
        freshness=EvidenceFreshness.STALE,
        data_quality_status="stale",
    )

    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=repository,
        durable_storage_backed=True,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()

    assert snapshot["freshness"]["freshness_state"] == "stale"
    assert snapshot["completeness_status"] == "stale"
    assert snapshot["reconciliation_status"] == "partial"
    assert snapshot["data_quality_status"] == "quality_warning"
    assert "stale_or_unavailable_source_refs_present" in snapshot["blocking"]["blocked_reason"]


def _persist_high_cash_candidate(
    repository: InMemoryIdeaRepository,
    *,
    suffix: str,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    data_quality_status: str = "complete",
) -> str:
    result = evaluate_high_cash_signal(
        _high_cash_input(suffix=suffix),
        _policy(),
    )
    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    candidate = result.candidate
    if freshness is not EvidenceFreshness.CURRENT or data_quality_status != "complete":
        source_refs = tuple(
            _source_ref(
                product_id,
                suffix=suffix,
                freshness=freshness,
                data_quality_status=data_quality_status,
            )
            for product_id in (
                "lotus-core:PortfolioStateSnapshot:v1",
                "lotus-core:HoldingsAsOf:v1",
                "lotus-core:PortfolioCashMovementSummary:v1",
                "lotus-core:PortfolioCashflowProjection:v1",
            )
        )
        lineage_ref = replace(candidate.evidence_packet.lineage_ref, source_refs=source_refs)
        evidence_packet = replace(
            candidate.evidence_packet,
            source_refs=source_refs,
            lineage_ref=lineage_ref,
        )
        candidate = replace(candidate, evidence_packet=evidence_packet)
    repository.persist_candidate(
        candidate,
        idempotency_key=f"runtime-trust-telemetry-{suffix}",
        payload={"suffix": suffix},
        actor_subject="platform-operator",
        occurred_at_utc=OBSERVED_AT,
    )
    return result.candidate.candidate_id


def _product_posture(
    snapshot: RuntimeTrustTelemetryPreview,
    product_id: str,
) -> RuntimeTrustTelemetryProductPosture:
    return next(
        posture for posture in snapshot.product_postures if posture.product_id == product_id
    )


def _snapshot_product_posture(snapshot: dict[str, object], product_id: str) -> dict[str, object]:
    coverage = snapshot["product_coverage"]
    assert isinstance(coverage, list)
    return next(
        posture
        for posture in coverage
        if isinstance(posture, dict) and posture["product_id"] == product_id
    )


def _declared_product_ids() -> set[str]:
    contract = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "contracts/domain-data-products/lotus-idea-products.v1.json"
        ).read_text(encoding="utf-8")
    )
    products = contract["products"]
    assert isinstance(products, list)
    return {
        f"lotus-idea:{product['product_name']}:{product['product_version']}"
        for product in products
        if isinstance(product, dict)
    }


def _policy() -> HighCashSignalPolicy:
    return HighCashSignalPolicy(
        policy_version="idle-liquidity-v1",
        cash_weight_threshold=Decimal("0.12"),
        candidate_score=Decimal("82"),
    )


def _high_cash_input(
    *,
    suffix: str,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    data_quality_status: str = "complete",
) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref(
            "lotus-core:PortfolioStateSnapshot:v1",
            suffix=suffix,
            freshness=freshness,
            data_quality_status=data_quality_status,
        ),
        holdings_ref=_source_ref(
            "lotus-core:HoldingsAsOf:v1",
            suffix=suffix,
            freshness=freshness,
            data_quality_status=data_quality_status,
        ),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            suffix=suffix,
            freshness=freshness,
            data_quality_status=data_quality_status,
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            suffix=suffix,
            freshness=freshness,
            data_quality_status=data_quality_status,
        ),
        evaluated_at_utc=OBSERVED_AT,
    )


def _source_ref(
    product_id: str,
    *,
    suffix: str,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    data_quality_status: str = "complete",
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/source-owned/{reference}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=OBSERVED_AT,
        content_hash=f"sha256:{product_id}:{suffix}",
        data_quality_status=data_quality_status,
        freshness=freshness,
    )


class _ProjectionOnlyRuntimeTrustTelemetryRepository:
    def __init__(self) -> None:
        self.summary_call_count = 0

    def runtime_trust_telemetry_summary(self) -> RuntimeTrustTelemetryRepositorySummary:
        self.summary_call_count += 1
        return RuntimeTrustTelemetryRepositorySummary(
            candidate_snapshot_count=2,
            current_source_ref_count=7,
            stale_or_unavailable_source_ref_count=1,
            source_authority_counts={"lotus-core": 7, "lotus-risk": 1},
            freshness_counts={"current": 7, "stale": 1},
            supportability_counts={"ready": 2},
            lifecycle_counts={"generated": 2},
            review_decision_count=1,
            feedback_event_count=1,
            conversion_intent_count=2,
            conversion_outcome_count=1,
            report_evidence_pack_count=3,
            lineage_materialized=True,
            source_batch_evidence_available=True,
            data_quality_status="quality_warning",
            latest_source_generated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            source_as_of_dates=("2026-06-21",),
            data_lifecycle_state_counts={"active": 1, "held": 1},
            retention_expired_count=1,
            lifecycle_control_missing_count=0,
        )

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("runtime trust telemetry should use repository projection")
