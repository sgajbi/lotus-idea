from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.outbox.broker.source_contract_proof import (
    build_outbox_broker_source_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

ROOT = Path(__file__).resolve().parents[4]
EVALUATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
PROOF_REF = "output/outbox/broker/source-contract-proof.json"


def test_source_contract_adds_provenance_without_changing_readiness() -> None:
    baseline = _snapshot()
    proof = bound_aggregate_proof(
        build_outbox_broker_source_contract_proof_payload(
            generated_at_utc=EVALUATED_AT_UTC,
            repository_root=ROOT,
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
    for capability_id in ("outbox-delivery", "operator-workflows-operations"):
        before = _capability(baseline, capability_id)
        after = _capability(actual, capability_id)
        assert after.blockers == before.blockers
        assert after.readiness_status == before.readiness_status
        assert after.supportability_status == before.supportability_status
        assert after.certification_ready is before.certification_ready
        assert after.supported_feature_promoted is before.supported_feature_promoted
        assert after.evidence_refs == (*before.evidence_refs, PROOF_REF)
    assert "outbox_broker_not_configured" in actual.overall_blockers
    assert "external_broker_runtime_proof_missing" in actual.overall_blockers


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("evidenceClass", "runtime_execution"),
        ("aggregateBlockersCleared", ["external_broker_runtime_proof_missing"]),
        ("externalBrokerConfigured", True),
        ("externalBrokerPublicationObserved", True),
        ("runtimeExecutionObserved", True),
        ("deploymentObserved", True),
        ("productionCertificationGranted", True),
        ("supportedFeaturePromoted", True),
    ],
)
def test_forged_runtime_claim_is_not_consumed(
    field_name: str,
    forged_value: object,
) -> None:
    payload = build_outbox_broker_source_contract_proof_payload(
        generated_at_utc=EVALUATED_AT_UTC,
        repository_root=ROOT,
    )
    payload[field_name] = forged_value
    proof = bound_aggregate_proof(payload, PROOF_REF)

    actual = _snapshot(proof=proof)

    assert PROOF_REF not in _capability(actual, "outbox-delivery").evidence_refs
    assert (
        PROOF_REF
        not in _capability(
            actual,
            "operator-workflows-operations",
        ).evidence_refs
    )
    assert "outbox_broker_not_configured" in actual.overall_blockers
    assert "external_broker_runtime_proof_missing" in actual.overall_blockers


def _snapshot(
    *,
    proof: dict[str, object] | None = None,
) -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT_UTC,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_broker_source_contract_proof=proof,
        outbox_broker_source_contract_proof_ref=PROOF_REF if proof else None,
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
