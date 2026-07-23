from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.outbox.consumer_runtime import (
    build_outbox_consumer_runtime_execution_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
    valid_manage_intake_runtime_execution,
    valid_report_materialization_runtime_execution,
)

EVALUATED_AT_UTC = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)
PROOF_REF = "output/outbox/consumer-runtime-execution-proof.json"


def test_consumer_runtime_proof_clears_only_downstream_consumer_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.proof_provenance.source_tree_dirty", lambda _: False)
    baseline = _snapshot()
    proof = bound_aggregate_proof(_valid_payload(), PROOF_REF)

    actual = _snapshot(proof=proof)

    before = _capability(baseline, "outbox-delivery")
    after = _capability(actual, "outbox-delivery")
    assert "downstream_consumer_runtime_proof_missing" in before.blockers
    assert "downstream_consumer_runtime_proof_missing" not in after.blockers
    assert PROOF_REF in after.evidence_refs
    assert "external_broker_runtime_proof_missing" in after.blockers
    assert "platform_mesh_event_publication_proof_missing" in after.blockers
    assert "gateway_workbench_proof_missing" in after.blockers
    assert "supported_feature_promotion_missing" in after.blockers
    assert "downstream_consumer_runtime_proof_missing" not in actual.overall_blockers
    assert "platform_mesh_event_publication_proof_missing" in actual.overall_blockers
    assert actual.readiness_status == baseline.readiness_status
    assert actual.supportability_status == baseline.supportability_status
    assert actual.supported_features_promoted is False


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("aggregateBlockersSatisfied", ["platform_mesh_event_publication_proof_missing"]),
        ("runtimeProofValid", False),
        ("evidenceClass", "source_contract"),
    ],
)
def test_forged_consumer_runtime_proof_is_not_consumed(
    field_name: str,
    forged_value: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.proof_provenance.source_tree_dirty", lambda _: False)
    payload = _valid_payload()
    payload[field_name] = forged_value
    actual = _snapshot(proof=bound_aggregate_proof(payload, PROOF_REF))

    outbox_delivery = _capability(actual, "outbox-delivery")
    assert PROOF_REF not in outbox_delivery.evidence_refs
    assert "downstream_consumer_runtime_proof_missing" in outbox_delivery.blockers


def _snapshot(
    *,
    proof: dict[str, object] | None = None,
) -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT_UTC,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_consumer_runtime_execution_proof=proof,
        outbox_consumer_runtime_execution_proof_ref=PROOF_REF if proof else None,
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


def _valid_payload() -> dict[str, object]:
    return build_outbox_consumer_runtime_execution_payload(
        generated_at_utc=EVALUATED_AT_UTC,
        advise_intake_runtime_execution_proof=valid_advise_intake_runtime_execution(),
        advise_intake_runtime_execution_proof_ref=(
            "output/downstream/advise-intake-runtime-execution-proof.json"
        ),
        manage_intake_runtime_execution_proof=valid_manage_intake_runtime_execution(),
        manage_intake_runtime_execution_proof_ref=(
            "output/downstream/manage-intake-runtime-execution-proof.json"
        ),
        report_materialization_runtime_execution_proof=(
            valid_report_materialization_runtime_execution()
        ),
        report_materialization_runtime_execution_proof_ref=(
            "output/report/materialization-runtime-execution-proof.json"
        ),
    )
