from __future__ import annotations

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
    if _registered_proof_is_valid_and_current(
        "outbox_broker_source_contract_proof",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
        outbox_broker_source_contract_proof,
        outbox_broker_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_broker_source_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _add_outbox_supporting_ref(
                capability,
                proof_ref=outbox_broker_source_contract_proof_ref,
                capability_ids={"outbox-delivery", "operator-workflows-operations"},
            )
            for capability in capabilities
        )
    if _registered_proof_is_valid_and_current(
        "outbox_broker_runtime_execution_proof",
        ProofArtifactEffect.BLOCKER_CLEARING,
        outbox_broker_runtime_execution_proof,
        outbox_broker_runtime_execution_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_broker_runtime_execution_is_valid,
    ):
        capabilities = tuple(
            _apply_outbox_broker_runtime_execution(
                capability,
                outbox_broker_runtime_execution_proof_ref,
            )
            for capability in capabilities
        )
    if _registered_proof_is_valid_and_current(
        "outbox_consumer_contract_proof",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
        outbox_consumer_contract_proof,
        outbox_consumer_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_consumer_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _add_outbox_supporting_ref(
                capability,
                proof_ref=outbox_consumer_contract_proof_ref,
                capability_ids={"outbox-delivery"},
            )
            for capability in capabilities
        )
    if _registered_proof_is_valid_and_current(
        "outbox_consumer_runtime_execution_proof",
        ProofArtifactEffect.BLOCKER_CLEARING,
        outbox_consumer_runtime_execution_proof,
        outbox_consumer_runtime_execution_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_consumer_runtime_execution_is_valid,
    ):
        capabilities = tuple(
            _apply_outbox_consumer_runtime_execution(
                capability,
                outbox_consumer_runtime_execution_proof_ref,
            )
            for capability in capabilities
        )
    if _registered_proof_is_valid_and_current(
        "outbox_platform_mesh_event_source_contract_proof",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
        outbox_platform_mesh_event_source_contract_proof,
        outbox_platform_mesh_event_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_platform_mesh_event_source_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _add_outbox_supporting_ref(
                capability,
                proof_ref=outbox_platform_mesh_event_source_contract_proof_ref,
                capability_ids={"outbox-delivery"},
            )
            for capability in capabilities
        )
    return capabilities


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
    proof_ref: str | None,
    capability_ids: set[str],
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in capability_ids:
        return capability
    evidence_refs = (
        tuple(dict.fromkeys((*capability.evidence_refs, proof_ref)))
        if proof_ref
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


def _apply_outbox_broker_runtime_execution(
    capability: ImplementationProofCapabilityReadiness,
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in {"outbox-delivery", "operator-workflows-operations"}:
        return capability
    return apply_blocker_proof(
        capability,
        blockers_cleared=OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED,
        proof_ref=proof_ref,
    )


def _apply_outbox_consumer_runtime_execution(
    capability: ImplementationProofCapabilityReadiness,
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "outbox-delivery":
        return capability
    return apply_blocker_proof(
        capability,
        blockers_cleared=OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
        proof_ref=proof_ref,
    )
