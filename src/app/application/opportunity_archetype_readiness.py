from __future__ import annotations

from pathlib import Path

from app.application.implementation_proof_models import ImplementationProofCapabilityReadiness
from app.application.opportunity_archetype_contracts import (
    OPPORTUNITY_ARCHETYPE_CONTRACT_PATH,
    OpportunityArchetypeContract,
    load_opportunity_archetype_contract,
)


def build_opportunity_archetype_scenario_readiness(
    *,
    repository_root: Path,
) -> ImplementationProofCapabilityReadiness:
    contract = load_opportunity_archetype_contract(repository_root=repository_root)
    return _opportunity_archetype_scenario_capability(contract)


def _opportunity_archetype_scenario_capability(
    contract: OpportunityArchetypeContract,
) -> ImplementationProofCapabilityReadiness:
    blockers = tuple(
        dict.fromkeys(
            (
                *(
                    ()
                    if contract.lifecycle_status == "foundation"
                    else ("opportunity_archetype_contract_not_foundation",)
                ),
                *(
                    ()
                    if contract.supportability_status == "not_certified"
                    else ("opportunity_archetype_contract_supportability_overclaimed",)
                ),
                *(() if not contract.demo_ready else ("opportunity_archetype_demo_overclaimed",)),
                *(
                    ()
                    if not contract.client_publication_ready
                    else ("opportunity_archetype_client_publication_overclaimed",)
                ),
                *(
                    ()
                    if not contract.data_mesh_certified
                    else ("opportunity_archetype_data_mesh_overclaimed",)
                ),
                *(
                    ()
                    if not contract.supported_feature_promoted
                    else ("opportunity_archetype_supported_feature_overclaimed",)
                ),
                *(
                    _opportunity_archetype_blocker(blocker)
                    for archetype in contract.archetypes
                    for blocker in archetype.blockers
                ),
                *(
                    _opportunity_archetype_blocker(blocker)
                    for archetype in contract.archetypes
                    for scenario in archetype.canonical_scenarios
                    for blocker in scenario.remaining_blockers
                ),
            )
        )
    )
    return ImplementationProofCapabilityReadiness(
        capability_id="opportunity-archetype-scenarios",
        name="Governed opportunity archetype scenario readiness",
        readiness_status=("ready" if not blockers else "blocked"),
        supportability_status=("not_certified" if blockers else contract.supportability_status),
        evidence_refs=_evidence_refs(contract),
        blockers=blockers,
        supported_feature_promoted=contract.supported_feature_promoted,
    )


def _evidence_refs(contract: OpportunityArchetypeContract) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                str(OPPORTUNITY_ARCHETYPE_CONTRACT_PATH.as_posix()),
                "src/app/application/opportunity_archetype_contracts.py",
                "scripts/opportunity_archetype_contract_gate.py",
                "make opportunity-archetype-contract-gate",
                *contract.source_of_truth.values(),
                *(
                    evidence_ref
                    for archetype in contract.archetypes
                    for evidence_ref in archetype.evidence_refs
                ),
            )
        )
    )


def _opportunity_archetype_blocker(blocker: str) -> str:
    return f"opportunity_archetype_{blocker}"
