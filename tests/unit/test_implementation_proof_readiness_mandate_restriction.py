from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.mandate_restriction_source_product_proof import (
    build_mandate_restriction_source_product_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.support.advise_mandate_restriction_runtime_evidence import (
    valid_advise_mandate_restriction_runtime_evidence,
)

LIVE_PROOF_REF = "output/opportunity/mandate-restriction-live-proof.json"
SOURCE_PRODUCT_PROOF_REF = "output/opportunity/mandate-restriction-source-product-proof.json"


def test_implementation_proof_readiness_retains_mandate_restriction_blocker_without_proof() -> None:
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
    assert "opportunity_archetype_live_restriction_source_proof_missing" in archetypes.blockers
    assert "opportunity_archetype_typed_restriction_source_product_missing" in (archetypes.blockers)
    assert (
        "opportunity_archetype_live_restriction_source_proof_missing" in snapshot.overall_blockers
    )
    assert "opportunity_archetype_typed_restriction_source_product_missing" in (
        snapshot.overall_blockers
    )


def test_implementation_proof_readiness_uses_mandate_restriction_source_product_proof_only() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mandate_restriction_source_product_proof=(
            _valid_mandate_restriction_source_product_proof()
        ),
        mandate_restriction_source_product_proof_ref=SOURCE_PRODUCT_PROOF_REF,
    )

    assert "opportunity_archetype_typed_restriction_source_product_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_live_restriction_source_proof_missing" in (
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
    assert "opportunity_archetype_typed_restriction_source_product_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_live_restriction_source_proof_missing" in archetypes.blockers
    assert (
        "output/opportunity/mandate-restriction-source-product-proof.json"
        in archetypes.evidence_refs
    )
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_uses_mandate_restriction_live_proof_without_promotion() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mandate_restriction_live_proof=_valid_mandate_restriction_live_proof(),
        mandate_restriction_live_proof_ref=LIVE_PROOF_REF,
    )

    assert "opportunity_archetype_live_restriction_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_typed_restriction_source_product_missing" in (
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
    assert "opportunity_archetype_live_restriction_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_typed_restriction_source_product_missing" in (archetypes.blockers)
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_client_publication_not_ready" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/mandate-restriction-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_combines_mandate_restriction_source_proofs() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mandate_restriction_live_proof=_valid_mandate_restriction_live_proof(),
        mandate_restriction_live_proof_ref=LIVE_PROOF_REF,
        mandate_restriction_source_product_proof=(
            _valid_mandate_restriction_source_product_proof()
        ),
        mandate_restriction_source_product_proof_ref=SOURCE_PRODUCT_PROOF_REF,
    )

    assert "opportunity_archetype_live_restriction_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_typed_restriction_source_product_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_client_publication_not_ready" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert snapshot.supported_features_promoted is False


def _valid_mandate_restriction_live_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        valid_advise_mandate_restriction_runtime_evidence(
            evaluated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        ),
        LIVE_PROOF_REF,
    )


def _valid_mandate_restriction_source_product_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        build_mandate_restriction_source_product_proof_payload(
            generated_at_utc=datetime(2026, 6, 28, 0, 0, tzinfo=UTC),
        ),
        SOURCE_PRODUCT_PROOF_REF,
    )
