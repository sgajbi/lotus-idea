from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.missing_suitability_live_proof import (
    build_missing_suitability_live_proof_payload,
)
from app.domain import InMemoryIdeaRepository


def test_implementation_proof_readiness_retains_missing_suitability_blocker_without_proof() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_advise_policy_live_source_proof_missing" in (archetypes.blockers)
    assert "opportunity_archetype_advise_policy_live_source_proof_missing" in (
        snapshot.overall_blockers
    )


def test_implementation_proof_readiness_uses_missing_suitability_live_proof_without_promotion() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        missing_suitability_live_proof=_valid_missing_suitability_live_proof(),
        missing_suitability_live_proof_ref="output/opportunity/missing-suitability-live-proof.json",
    )

    assert "opportunity_archetype_advise_policy_live_source_proof_missing" not in (
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
    assert "opportunity_archetype_advise_policy_live_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_client_publication_not_ready" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/missing-suitability-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_missing_suitability_live_proof() -> dict[str, object]:
    return build_missing_suitability_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "clientReadyPublicationBlocked": True,
            "advisePolicyWorkflowReady": True,
            "sourceDiagnosticCodes": ["advise_policy_requirements_open"],
            "reasonCodes": ["suitability_context_missing", "review_required"],
            "unsupportedReasons": [],
        },
    )
