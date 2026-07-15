from __future__ import annotations

from typing import Any

import pytest

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain import InMemoryIdeaRepository
from tests.support.high_volatility_runtime_evidence import GENERATED_AT, runtime_execution
from tests.support.proof_provenance import bound_aggregate_proof

PROOF_REF = "output/opportunity/high-volatility-live-proof.json"


def test_implementation_proof_readiness_retains_high_volatility_blocker_without_live_proof() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_risk_volatility_source_proof_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_live_risk_volatility_source_proof_missing" in (
        snapshot.overall_blockers
    )


def test_implementation_proof_readiness_uses_high_volatility_live_proof_without_promotion() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        high_volatility_live_proof=_valid_high_volatility_live_proof(),
        high_volatility_live_proof_ref=PROOF_REF,
    )

    assert "opportunity_archetype_live_risk_volatility_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_drawdown_source_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_risk_volatility_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_drawdown_source_proof_missing" in archetypes.blockers
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/high-volatility-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_provenance",
        "non_durable_execution",
        "wrong_evidence_class",
        "unknown_contract_field",
        "tampered_source_receipt",
        "tampered_persistence_receipt",
    ),
)
def test_implementation_proof_readiness_rejects_untrustworthy_high_volatility_evidence(
    mutation: str,
) -> None:
    proof = _valid_high_volatility_live_proof()
    _mutate_proof(proof, mutation)

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        high_volatility_live_proof=proof,
        high_volatility_live_proof_ref=PROOF_REF,
    )

    assert "opportunity_archetype_live_risk_volatility_source_proof_missing" in (
        snapshot.overall_blockers
    )
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert PROOF_REF not in archetypes.evidence_refs
    assert snapshot.supported_features_promoted is False


def _valid_high_volatility_live_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        runtime_execution(),
        PROOF_REF,
    )


def _mutate_proof(proof: dict[str, Any], mutation: str) -> None:
    if mutation == "missing_provenance":
        proof.pop(AGGREGATE_PROOF_PROVENANCE_KEY)
        return
    if mutation == "wrong_evidence_class":
        proof["evidenceClass"] = "source_contract"
        return
    if mutation == "unknown_contract_field":
        proof["untrustedClaim"] = True
        return

    execution = proof["execution"]
    assert isinstance(execution, dict)
    if mutation == "non_durable_execution":
        execution["durableStorageBacked"] = False
        return
    if mutation == "tampered_source_receipt":
        source_receipt = execution["sourceReceipt"]
        assert isinstance(source_receipt, dict)
        source_receipt["contentHash"] = "sha256:forged"
        return
    persistence_receipt = execution["persistenceReceipt"]
    assert isinstance(persistence_receipt, dict)
    persistence_receipt["decision"] = "accepted-without-write"
