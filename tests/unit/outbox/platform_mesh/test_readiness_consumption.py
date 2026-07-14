from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    build_outbox_platform_mesh_event_source_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.unit.test_implementation_proof_readiness import _write_platform_mesh_fixture

ROOT = Path(__file__).resolve().parents[4]
EVALUATED_AT_UTC = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
PROOF_REF = "output/outbox/platform-mesh/event-source-contract-proof.json"


def test_source_contract_adds_provenance_without_changing_readiness(tmp_path: Path) -> None:
    baseline = _snapshot()
    proof = bound_aggregate_proof(
        build_outbox_platform_mesh_event_source_contract_proof_payload(
            generated_at_utc=EVALUATED_AT_UTC,
            repository_root=ROOT,
            platform_root=_write_platform_mesh_fixture(tmp_path),
        ),
        PROOF_REF,
    )

    actual = _snapshot(proof=proof)

    assert actual.overall_blockers == baseline.overall_blockers
    assert actual.readiness_status == baseline.readiness_status
    assert actual.supportability_status == baseline.supportability_status
    assert actual.certification_ready is baseline.certification_ready
    assert actual.supported_feature_count == baseline.supported_feature_count
    assert actual.supported_features_promoted is baseline.supported_features_promoted
    before = _capability(baseline, "outbox-delivery")
    after = _capability(actual, "outbox-delivery")
    assert after.blockers == before.blockers
    assert after.readiness_status == before.readiness_status
    assert after.supportability_status == before.supportability_status
    assert after.certification_ready is before.certification_ready
    assert after.supported_feature_promoted is before.supported_feature_promoted
    assert after.evidence_refs == (*before.evidence_refs, PROOF_REF)
    assert "platform_mesh_event_publication_proof_missing" in actual.overall_blockers


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("evidenceClass", "runtime_execution"),
        ("aggregateBlockersCleared", ["platform_mesh_event_publication_proof_missing"]),
        ("runtimeExecutionObserved", True),
        ("platformMeshEventPublished", True),
        ("publicationReceiptObserved", True),
        ("deploymentObserved", True),
        ("productionCertificationGranted", True),
        ("supportedFeaturePromoted", True),
    ],
)
def test_forged_runtime_claim_is_not_consumed(
    field_name: str,
    forged_value: object,
    tmp_path: Path,
) -> None:
    payload = build_outbox_platform_mesh_event_source_contract_proof_payload(
        generated_at_utc=EVALUATED_AT_UTC,
        repository_root=ROOT,
        platform_root=_write_platform_mesh_fixture(tmp_path),
    )
    payload[field_name] = forged_value
    actual = _snapshot(proof=bound_aggregate_proof(payload, PROOF_REF))

    assert PROOF_REF not in _capability(actual, "outbox-delivery").evidence_refs
    assert "platform_mesh_event_publication_proof_missing" in actual.overall_blockers


def _snapshot(
    *,
    proof: dict[str, object] | None = None,
) -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT_UTC,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_platform_mesh_event_source_contract_proof=proof,
        outbox_platform_mesh_event_source_contract_proof_ref=PROOF_REF if proof else None,
    )


def _capability(
    snapshot: ImplementationProofReadinessSnapshot,
    capability_id: str,
) -> ImplementationProofCapabilityReadiness:
    return next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == capability_id
    )
