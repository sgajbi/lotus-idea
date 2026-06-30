from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.missing_benchmark_live_proof import (
    build_missing_benchmark_live_proof_payload,
)
from app.application.missing_benchmark_performance_readiness_proof import (
    build_missing_benchmark_performance_readiness_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

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
    return bound_aggregate_proof(
        build_missing_benchmark_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
            live_core_source_attempted=True,
            evaluation_summary={
                "runStatus": "completed",
                "sourceAuthority": "lotus-core",
                "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
                "evaluationOutcome": "candidate_created",
                "benchmarkAssignmentRefPresent": True,
                "benchmarkIdentityResolved": False,
                "assignmentEffectiveForAsOfDate": False,
                "assignmentStatus": "active",
                "assignmentVersionPresent": True,
                "sourceEvidenceCurrent": True,
                "sourceDiagnosticCodes": ["core_benchmark_assignment_benchmark_identity_missing"],
                "reasonCodes": ["missing_benchmark", "review_required"],
                "unsupportedReasons": [],
            },
        ),
        LIVE_PROOF_REF,
    )


def _valid_missing_benchmark_performance_readiness_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        build_missing_benchmark_performance_readiness_proof_payload(
            generated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
            live_performance_source_attempted=True,
            performance_summary={
                "runStatus": "completed",
                "sourceAuthority": "lotus-performance",
                "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
                "sourceEvidenceCurrent": True,
                "performanceBenchmarkReadinessSourceRefPresent": True,
                "benchmarkContextAvailable": False,
                "benchmarkReadinessDiagnostic": "performance_benchmark_context_missing",
                "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
            },
        ),
        PERFORMANCE_PROOF_REF,
    )
