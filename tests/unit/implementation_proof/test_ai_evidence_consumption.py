from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.ai_lineage_store_proof import build_ai_lineage_store_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof


ROOT = Path(__file__).resolve().parents[3]


def test_source_only_ai_lineage_proof_cannot_clear_aggregate_certification() -> None:
    proof_ref = "output/ai/source-only-lineage-proof.json"
    proof = bound_aggregate_proof(
        build_ai_lineage_store_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_lineage_store_proof=proof,
        ai_lineage_store_proof_ref=proof_ref,
    )

    ai_explanation = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
    assert "certified_ai_lineage_store_missing" in ai_explanation.blockers
    assert proof_ref not in ai_explanation.evidence_refs
    assert snapshot.supported_features_promoted is False
