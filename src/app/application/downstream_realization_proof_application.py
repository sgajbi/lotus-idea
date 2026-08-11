from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping

from app.application.implementation_proof_artifact_registry import (
    ProofArtifactEffect,
    proof_artifact_effect_matches_payload,
)
from app.application.proof_provenance import aggregate_proof_artifact_is_current


@dataclass(frozen=True)
class DownstreamProofInputs:
    advise_proposal_route_proof: Mapping[str, object] | None
    advise_proposal_route_proof_ref: str | None
    advise_intake_runtime_execution_proof: Mapping[str, object] | None
    advise_intake_runtime_execution_proof_ref: str | None
    manage_intake_runtime_execution_proof: Mapping[str, object] | None
    manage_intake_runtime_execution_proof_ref: str | None
    manage_action_route_proof: Mapping[str, object] | None
    manage_action_route_proof_ref: str | None
    report_intake_route_source_contract_proof: Mapping[str, object] | None
    report_intake_route_source_contract_proof_ref: str | None
    report_intake_runtime_execution_proof: Mapping[str, object] | None
    report_intake_runtime_execution_proof_ref: str | None
    report_materialization_source_contract_proof: Mapping[str, object] | None
    report_materialization_source_contract_proof_ref: str | None
    report_materialization_runtime_execution_proof: Mapping[str, object] | None
    report_materialization_runtime_execution_proof_ref: str | None


def supporting_source_contract_proof_is_valid(
    *,
    registry_key: str,
    proof: Mapping[str, object] | None,
    validator: Callable[[Mapping[str, object]], bool],
) -> bool:
    return (
        proof_artifact_effect_matches_payload(
            registry_key,
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        )
        and proof is not None
        and validator(proof)
    )


def current_blocker_clearing_proof_is_valid(
    *,
    registry_key: str,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
    evaluated_at_utc: datetime,
    validator: Callable[[Mapping[str, object]], bool],
) -> bool:
    return (
        proof_artifact_effect_matches_payload(
            registry_key,
            ProofArtifactEffect.BLOCKER_CLEARING,
        )
        and proof is not None
        and validator(proof)
        and aggregate_proof_artifact_is_current(
            proof,
            evaluated_at_utc=evaluated_at_utc,
            proof_ref=proof_ref,
        )
    )
