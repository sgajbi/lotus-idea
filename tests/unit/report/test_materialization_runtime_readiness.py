from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.unit.downstream_realization.fixtures import (
    valid_report_materialization_runtime_execution,
)


def test_report_materialization_runtime_execution_clears_live_materialization_blocker_only() -> (
    None
):
    proof_ref = "output/report/materialization-runtime-execution-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_materialization_runtime_execution_proof=bound_aggregate_proof(
            valid_report_materialization_runtime_execution(),
            proof_ref,
        ),
        report_materialization_runtime_execution_proof_ref=proof_ref,
    )

    assert "report_evidence_pack_live_materialization_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "lotus_report_live_intake_route_proof_missing" in snapshot.overall_blockers
    assert "rendered_output_creation_missing" in snapshot.overall_blockers
    assert "archive_record_creation_missing" in snapshot.overall_blockers
    assert "client_publication_authority_blocked" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "report_evidence_pack_live_materialization_proof_missing" not in (downstream.blockers)
    assert "rendered_output_creation_missing" in downstream.blockers
    assert "archive_record_creation_missing" in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert proof_ref in downstream.evidence_refs
