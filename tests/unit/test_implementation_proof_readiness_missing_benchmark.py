from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.core_missing_benchmark_runtime_evidence import (
    EvaluateCoreMissingBenchmark,
    build_core_missing_benchmark_runtime_execution,
    evaluate_core_missing_benchmark,
)
from app.application.performance_benchmark_readiness import (
    evaluate_performance_benchmark_readiness,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (
    build_performance_benchmark_readiness_runtime_execution,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.support.core_missing_benchmark_runtime_evidence import (
    AuthoritativeCoreMissingBenchmarkSource,
)
from tests.support.performance_benchmark_readiness_runtime_evidence import (
    AuthoritativePerformanceBenchmarkReadinessSource,
    performance_benchmark_readiness_command,
    performance_benchmark_readiness_evidence,
)

LIVE_PROOF_REF = "output/opportunity/missing-benchmark-live-proof.json"
PERFORMANCE_PROOF_REF = "output/opportunity/missing-benchmark-performance-readiness-proof.json"


def test_implementation_proof_readiness_retains_missing_benchmark_blocker_without_proof() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" in (
        snapshot.overall_blockers
    )


def test_implementation_proof_readiness_uses_missing_benchmark_live_proof_without_promotion() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        missing_benchmark_live_proof=_valid_missing_benchmark_live_proof(),
        missing_benchmark_live_proof_ref=LIVE_PROOF_REF,
    )

    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_performance_benchmark_readiness_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_client_publication_not_ready" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_performance_benchmark_readiness_source_ref_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_client_publication_not_ready" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/missing-benchmark-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_uses_missing_benchmark_performance_readiness_proof() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        missing_benchmark_performance_readiness_proof=(
            _valid_missing_benchmark_performance_readiness_proof()
        ),
        missing_benchmark_performance_readiness_proof_ref=PERFORMANCE_PROOF_REF,
    )

    assert "opportunity_archetype_performance_benchmark_readiness_source_ref_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_client_publication_not_ready" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_performance_benchmark_readiness_source_ref_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_missing_benchmark_live_core_source_proof_missing" in (
        archetypes.blockers
    )
    assert (
        "output/opportunity/missing-benchmark-performance-readiness-proof.json"
        in archetypes.evidence_refs
    )
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_missing_benchmark_live_proof() -> dict[str, object]:
    evaluated_at = datetime(2026, 6, 28, 0, 0, tzinfo=UTC)
    result = evaluate_core_missing_benchmark(
        EvaluateCoreMissingBenchmark(
            tenant_id="tenant-a",
            book_id="book-a",
            portfolio_id="portfolio-a",
            client_id="client-a",
            evaluation_id="evaluation-a",
            as_of_date=evaluated_at.date(),
            evaluated_at_utc=evaluated_at,
            reporting_currency="USD",
            correlation_id="corr-core",
            trace_id="trace-core",
        ),
        core_source=AuthoritativeCoreMissingBenchmarkSource(),
    )
    return bound_aggregate_proof(
        build_core_missing_benchmark_runtime_execution(
            generated_at_utc=evaluated_at,
            result=result,
        ),
        LIVE_PROOF_REF,
    )


def _valid_missing_benchmark_performance_readiness_proof() -> dict[str, object]:
    evaluated_at = datetime(2026, 6, 28, 0, 0, tzinfo=UTC)
    command = replace(
        performance_benchmark_readiness_command(),
        as_of_date=evaluated_at.date(),
        evaluated_at_utc=evaluated_at,
    )
    return bound_aggregate_proof(
        build_performance_benchmark_readiness_runtime_execution(
            generated_at_utc=evaluated_at,
            result=evaluate_performance_benchmark_readiness(
                command,
                performance_source=AuthoritativePerformanceBenchmarkReadinessSource(
                    evidence=performance_benchmark_readiness_evidence(
                        as_of_date=evaluated_at.date(),
                        generated_at_utc=evaluated_at,
                    )
                ),
            ),
        ),
        PERFORMANCE_PROOF_REF,
    )
