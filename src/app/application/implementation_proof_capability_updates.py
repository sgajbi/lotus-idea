from __future__ import annotations

from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
)


def apply_blocker_proof(
    capability: ImplementationProofCapabilityReadiness,
    *,
    capability_ids: tuple[str, ...] | None = None,
    blockers_cleared: tuple[str, ...],
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability_ids is not None and capability.capability_id not in capability_ids:
        return capability
    blockers_to_clear = set(blockers_cleared)
    if not blockers_to_clear.intersection(capability.blockers):
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def build_capability_readiness(
    capability_id: str,
    name: str,
    *,
    readiness_status: str,
    supportability_status: str,
    evidence_refs: tuple[str, ...],
    blockers: tuple[str, ...],
    supported_feature_promoted: bool = False,
) -> ImplementationProofCapabilityReadiness:
    normalized_readiness_status = readiness_status
    normalized_supportability_status = supportability_status
    if not blockers:
        normalized_readiness_status = "ready"
        normalized_supportability_status = "supported"
    return ImplementationProofCapabilityReadiness(
        capability_id=capability_id,
        name=name,
        readiness_status=normalized_readiness_status,
        supportability_status=normalized_supportability_status,
        evidence_refs=evidence_refs,
        blockers=blockers,
        supported_feature_promoted=supported_feature_promoted,
    )
