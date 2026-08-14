from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from app.application.implementation_proof_artifact_registry import (
    ProofArtifactEffect,
    proof_artifact_effect_matches_payload,
)
from app.application.implementation_proof_capability_updates import (
    apply_blocker_proof,
    build_capability_readiness,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
)
from app.application.outbox.broker.runtime_execution import (
    OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED,
    outbox_broker_runtime_execution_is_valid,
)
from app.application.outbox.broker.source_contract_proof import (
    outbox_broker_source_contract_proof_is_valid,
)
from app.application.outbox.consumer_contract_proof import (
    outbox_consumer_contract_proof_is_valid,
)
from app.application.outbox.consumer_runtime import (
    OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
    outbox_consumer_runtime_execution_is_valid,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    outbox_platform_mesh_event_source_contract_proof_is_valid,
)
from app.application.proof_provenance import aggregate_proof_artifact_is_current


_OUTBOX_DELIVERY_CAPABILITY_IDS = frozenset({"outbox-delivery"})
_BROKER_CAPABILITY_IDS = frozenset({"outbox-delivery", "operator-workflows-operations"})


@dataclass(frozen=True)
class _OutboxProofStep:
    payload_argument: str
    expected_effect: ProofArtifactEffect
    proof: Mapping[str, object] | None
    proof_ref: str | None
    proof_is_valid: Callable[[Mapping[str, Any]], bool]
    capability_ids: frozenset[str]
    blockers_cleared: tuple[str, ...] = ()


def apply_outbox_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    outbox_broker_source_contract_proof: Mapping[str, object] | None,
    outbox_broker_source_contract_proof_ref: str | None,
    outbox_broker_runtime_execution_proof: Mapping[str, object] | None,
    outbox_broker_runtime_execution_proof_ref: str | None,
    outbox_consumer_contract_proof: Mapping[str, object] | None,
    outbox_consumer_contract_proof_ref: str | None,
    outbox_consumer_runtime_execution_proof: Mapping[str, object] | None,
    outbox_consumer_runtime_execution_proof_ref: str | None,
    outbox_platform_mesh_event_source_contract_proof: Mapping[str, object] | None,
    outbox_platform_mesh_event_source_contract_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    for step in _outbox_proof_steps(
        outbox_broker_source_contract_proof=outbox_broker_source_contract_proof,
        outbox_broker_source_contract_proof_ref=outbox_broker_source_contract_proof_ref,
        outbox_broker_runtime_execution_proof=outbox_broker_runtime_execution_proof,
        outbox_broker_runtime_execution_proof_ref=outbox_broker_runtime_execution_proof_ref,
        outbox_consumer_contract_proof=outbox_consumer_contract_proof,
        outbox_consumer_contract_proof_ref=outbox_consumer_contract_proof_ref,
        outbox_consumer_runtime_execution_proof=outbox_consumer_runtime_execution_proof,
        outbox_consumer_runtime_execution_proof_ref=outbox_consumer_runtime_execution_proof_ref,
        outbox_platform_mesh_event_source_contract_proof=outbox_platform_mesh_event_source_contract_proof,
        outbox_platform_mesh_event_source_contract_proof_ref=outbox_platform_mesh_event_source_contract_proof_ref,
    ):
        capabilities = _apply_outbox_proof_step(
            capabilities,
            step,
            evaluated_at_utc=evaluated_at_utc,
        )
    return capabilities


def _outbox_proof_steps(
    *,
    outbox_broker_source_contract_proof: Mapping[str, object] | None,
    outbox_broker_source_contract_proof_ref: str | None,
    outbox_broker_runtime_execution_proof: Mapping[str, object] | None,
    outbox_broker_runtime_execution_proof_ref: str | None,
    outbox_consumer_contract_proof: Mapping[str, object] | None,
    outbox_consumer_contract_proof_ref: str | None,
    outbox_consumer_runtime_execution_proof: Mapping[str, object] | None,
    outbox_consumer_runtime_execution_proof_ref: str | None,
    outbox_platform_mesh_event_source_contract_proof: Mapping[str, object] | None,
    outbox_platform_mesh_event_source_contract_proof_ref: str | None,
) -> tuple[_OutboxProofStep, ...]:
    return (
        _OutboxProofStep(
            payload_argument="outbox_broker_source_contract_proof",
            expected_effect=ProofArtifactEffect.SUPPORTING_EVIDENCE,
            proof=outbox_broker_source_contract_proof,
            proof_ref=outbox_broker_source_contract_proof_ref,
            proof_is_valid=outbox_broker_source_contract_proof_is_valid,
            capability_ids=_BROKER_CAPABILITY_IDS,
        ),
        _OutboxProofStep(
            payload_argument="outbox_broker_runtime_execution_proof",
            expected_effect=ProofArtifactEffect.BLOCKER_CLEARING,
            proof=outbox_broker_runtime_execution_proof,
            proof_ref=outbox_broker_runtime_execution_proof_ref,
            proof_is_valid=outbox_broker_runtime_execution_is_valid,
            capability_ids=_BROKER_CAPABILITY_IDS,
            blockers_cleared=OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED,
        ),
        _OutboxProofStep(
            payload_argument="outbox_consumer_contract_proof",
            expected_effect=ProofArtifactEffect.SUPPORTING_EVIDENCE,
            proof=outbox_consumer_contract_proof,
            proof_ref=outbox_consumer_contract_proof_ref,
            proof_is_valid=outbox_consumer_contract_proof_is_valid,
            capability_ids=_OUTBOX_DELIVERY_CAPABILITY_IDS,
        ),
        _OutboxProofStep(
            payload_argument="outbox_consumer_runtime_execution_proof",
            expected_effect=ProofArtifactEffect.BLOCKER_CLEARING,
            proof=outbox_consumer_runtime_execution_proof,
            proof_ref=outbox_consumer_runtime_execution_proof_ref,
            proof_is_valid=outbox_consumer_runtime_execution_is_valid,
            capability_ids=_OUTBOX_DELIVERY_CAPABILITY_IDS,
            blockers_cleared=OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
        ),
        _OutboxProofStep(
            payload_argument="outbox_platform_mesh_event_source_contract_proof",
            expected_effect=ProofArtifactEffect.SUPPORTING_EVIDENCE,
            proof=outbox_platform_mesh_event_source_contract_proof,
            proof_ref=outbox_platform_mesh_event_source_contract_proof_ref,
            proof_is_valid=outbox_platform_mesh_event_source_contract_proof_is_valid,
            capability_ids=_OUTBOX_DELIVERY_CAPABILITY_IDS,
        ),
    )


def _apply_outbox_proof_step(
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    step: _OutboxProofStep,
    *,
    evaluated_at_utc: datetime,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if not _registered_proof_is_valid_and_current(
        step.payload_argument,
        step.expected_effect,
        step.proof,
        step.proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=step.proof_is_valid,
    ):
        return capabilities
    if step.expected_effect is ProofArtifactEffect.BLOCKER_CLEARING:
        return tuple(_apply_outbox_runtime_step(capability, step) for capability in capabilities)
    return tuple(_add_outbox_supporting_ref(capability, step) for capability in capabilities)


def _registered_proof_is_valid_and_current(
    payload_argument: str,
    expected_effect: ProofArtifactEffect,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
    *,
    evaluated_at_utc: datetime,
    proof_is_valid: Any,
) -> bool:
    return bool(
        proof_artifact_effect_matches_payload(payload_argument, expected_effect)
        and proof
        and proof_is_valid(proof)
        and aggregate_proof_artifact_is_current(
            proof,
            evaluated_at_utc=evaluated_at_utc,
            proof_ref=proof_ref,
        )
    )


def _add_outbox_supporting_ref(
    capability: ImplementationProofCapabilityReadiness,
    step: _OutboxProofStep,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in step.capability_ids:
        return capability
    evidence_refs = (
        tuple(dict.fromkeys((*capability.evidence_refs, step.proof_ref)))
        if step.proof_ref
        else capability.evidence_refs
    )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_outbox_runtime_step(
    capability: ImplementationProofCapabilityReadiness,
    step: _OutboxProofStep,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in step.capability_ids:
        return capability
    return apply_blocker_proof(
        capability,
        blockers_cleared=step.blockers_cleared,
        proof_ref=step.proof_ref,
    )
