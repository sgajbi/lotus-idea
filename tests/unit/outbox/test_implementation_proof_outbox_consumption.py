from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.implementation_proof_capability_updates import (
    build_capability_readiness,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
)
from app.application.implementation_proof_outbox_consumption import apply_outbox_proofs
from app.application.outbox.consumer_runtime import (
    OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
)

EVALUATED_AT_UTC = datetime(2026, 8, 14, 9, 30, tzinfo=UTC)
PROOF_REF = "output/outbox/consumer-runtime-execution-proof.json"
SOURCE_CONTRACT_REF = "output/outbox/broker/source-contract-proof.json"


def test_outbox_runtime_step_clears_only_its_declared_capability_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_registered_proofs(monkeypatch)

    actual = apply_outbox_proofs(
        capabilities=_capabilities(),
        evaluated_at_utc=EVALUATED_AT_UTC,
        outbox_broker_source_contract_proof=None,
        outbox_broker_source_contract_proof_ref=None,
        outbox_broker_runtime_execution_proof=None,
        outbox_broker_runtime_execution_proof_ref=None,
        outbox_consumer_contract_proof=None,
        outbox_consumer_contract_proof_ref=None,
        outbox_consumer_runtime_execution_proof={"proofType": "test"},
        outbox_consumer_runtime_execution_proof_ref=PROOF_REF,
        outbox_platform_mesh_event_source_contract_proof=None,
        outbox_platform_mesh_event_source_contract_proof_ref=None,
    )

    outbox_delivery = _capability(actual, "outbox-delivery")
    operator_workflows = _capability(actual, "operator-workflows-operations")

    assert not set(OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED).intersection(
        outbox_delivery.blockers
    )
    assert "external_broker_runtime_proof_missing" in outbox_delivery.blockers
    assert PROOF_REF in outbox_delivery.evidence_refs
    assert operator_workflows.evidence_refs == ("existing-ref",)
    assert operator_workflows.blockers == ("external_broker_runtime_proof_missing",)
    assert _capability(actual, "data-mesh-readiness") == _capability(
        _capabilities(), "data-mesh-readiness"
    )


def test_outbox_source_contract_step_adds_deduplicated_supporting_refs_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_registered_proofs(monkeypatch)

    actual = apply_outbox_proofs(
        capabilities=_capabilities(),
        evaluated_at_utc=EVALUATED_AT_UTC,
        outbox_broker_source_contract_proof={"proofType": "test"},
        outbox_broker_source_contract_proof_ref=SOURCE_CONTRACT_REF,
        outbox_broker_runtime_execution_proof=None,
        outbox_broker_runtime_execution_proof_ref=None,
        outbox_consumer_contract_proof=None,
        outbox_consumer_contract_proof_ref=None,
        outbox_consumer_runtime_execution_proof=None,
        outbox_consumer_runtime_execution_proof_ref=None,
        outbox_platform_mesh_event_source_contract_proof=None,
        outbox_platform_mesh_event_source_contract_proof_ref=None,
    )

    for capability_id in ("outbox-delivery", "operator-workflows-operations"):
        capability = _capability(actual, capability_id)
        assert capability.evidence_refs == ("existing-ref", SOURCE_CONTRACT_REF)
        assert "external_broker_runtime_proof_missing" in capability.blockers
    assert _capability(actual, "data-mesh-readiness").evidence_refs == ("existing-ref",)


def test_outbox_proof_step_is_noop_when_registered_effect_or_validator_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_registered_proofs(monkeypatch)
    monkeypatch.setattr(
        "app.application.implementation_proof_outbox_consumption."
        "outbox_consumer_runtime_execution_is_valid",
        lambda _: False,
    )

    actual = apply_outbox_proofs(
        capabilities=_capabilities(),
        evaluated_at_utc=EVALUATED_AT_UTC,
        outbox_broker_source_contract_proof=None,
        outbox_broker_source_contract_proof_ref=None,
        outbox_broker_runtime_execution_proof=None,
        outbox_broker_runtime_execution_proof_ref=None,
        outbox_consumer_contract_proof=None,
        outbox_consumer_contract_proof_ref=None,
        outbox_consumer_runtime_execution_proof={"proofType": "test"},
        outbox_consumer_runtime_execution_proof_ref=PROOF_REF,
        outbox_platform_mesh_event_source_contract_proof=None,
        outbox_platform_mesh_event_source_contract_proof_ref=None,
    )

    assert actual == _capabilities()


def _accept_registered_proofs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.implementation_proof_outbox_consumption."
        "aggregate_proof_artifact_is_current",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "app.application.implementation_proof_outbox_consumption."
        "outbox_broker_source_contract_proof_is_valid",
        lambda _: True,
    )
    monkeypatch.setattr(
        "app.application.implementation_proof_outbox_consumption."
        "outbox_consumer_runtime_execution_is_valid",
        lambda _: True,
    )


def _capabilities() -> tuple[ImplementationProofCapabilityReadiness, ...]:
    return (
        _capability_readiness(
            "outbox-delivery",
            blockers=(
                "external_broker_runtime_proof_missing",
                "downstream_consumer_runtime_proof_missing",
                "platform_mesh_event_publication_proof_missing",
            ),
        ),
        _capability_readiness(
            "operator-workflows-operations",
            blockers=("external_broker_runtime_proof_missing",),
        ),
        _capability_readiness(
            "data-mesh-readiness",
            blockers=("mesh_policy_source_contract_missing",),
        ),
    )


def _capability_readiness(
    capability_id: str,
    *,
    blockers: tuple[str, ...],
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        capability_id,
        capability_id.replace("-", " ").title(),
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-ref",),
        blockers=blockers,
        supported_feature_promoted=False,
    )


def _capability(
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    capability_id: str,
) -> ImplementationProofCapabilityReadiness:
    return next(
        capability for capability in capabilities if capability.capability_id == capability_id
    )
