from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.opportunity_archetype_evidence_pack import (
    build_canonical_opportunity_archetype_evidence_pack,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
PROOF_REF = "output/opportunity/canonical-archetype-evidence-pack.json"
ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_readiness_consumes_archetype_evidence_pack_as_supporting_evidence() -> (
    None
):
    proof = bound_aggregate_proof(
        build_canonical_opportunity_archetype_evidence_pack(
            generated_at_utc=GENERATED_AT,
            repository_root=ROOT,
        ),
        PROOF_REF,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        opportunity_archetype_evidence_pack_proof=proof,
        opportunity_archetype_evidence_pack_proof_ref=PROOF_REF,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert PROOF_REF in archetypes.evidence_refs
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"


def test_implementation_proof_readiness_rejects_unproven_archetype_evidence_pack() -> None:
    proof = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )
    proof[AGGREGATE_PROOF_PROVENANCE_KEY] = {
        "repository": "lotus-idea",
        "proofRef": "wrong-ref",
    }

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        opportunity_archetype_evidence_pack_proof=proof,
        opportunity_archetype_evidence_pack_proof_ref=PROOF_REF,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert PROOF_REF not in archetypes.evidence_refs
