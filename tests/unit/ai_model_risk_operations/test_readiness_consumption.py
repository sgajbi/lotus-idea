from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.ai_model_risk_operations.source_contract_proof import (
    build_ai_model_risk_operations_proof_payload,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

ROOT = Path(__file__).resolve().parents[3]
PROOF_REF = "output/ai/ai-model-risk-operations-source-contract-proof.json"


def test_source_contract_proof_adds_evidence_without_clearing_runtime_blockers() -> None:
    proof = bound_aggregate_proof(
        build_ai_model_risk_operations_proof_payload(
            generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        PROOF_REF,
    )

    snapshot = _readiness_snapshot(proof)

    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    ai_explanation = _ai_explanation(snapshot)
    assert PROOF_REF in ai_explanation.evidence_refs
    assert "model_risk_dashboard_runtime_proof_missing" in ai_explanation.blockers
    assert "model_risk_alert_rules_runtime_proof_missing" in ai_explanation.blockers
    assert "lotus_ai_runtime_execution_missing" in ai_explanation.blockers
    assert "certified_runtime_trust_telemetry_missing" in ai_explanation.blockers
    assert "workbench_product_proof_missing" in ai_explanation.blockers


def test_source_contract_proof_rejects_runtime_claim_inflation() -> None:
    proof = build_ai_model_risk_operations_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof["evidenceClass"] = "runtime_execution"
    proof["runtimeExecutionObserved"] = True

    snapshot = _readiness_snapshot(bound_aggregate_proof(proof, PROOF_REF))

    ai_explanation = _ai_explanation(snapshot)
    assert PROOF_REF not in ai_explanation.evidence_refs
    assert "model_risk_dashboard_runtime_proof_missing" in ai_explanation.blockers
    assert "model_risk_alert_rules_runtime_proof_missing" in ai_explanation.blockers


def _readiness_snapshot(proof: dict[str, object]) -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_model_risk_operations_proof=proof,
        ai_model_risk_operations_proof_ref=PROOF_REF,
    )


def _ai_explanation(
    snapshot: ImplementationProofReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
