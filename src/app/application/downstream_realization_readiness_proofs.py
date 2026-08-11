from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.application.downstream_realization.route_source_contract import (
    ADVISE_PROPOSAL_ROUTE,
    MANAGE_ACTION_ROUTE,
    advise_route_source_contract_is_valid,
    manage_route_source_contract_is_valid,
)
from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    advise_intake_runtime_execution_is_valid,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    manage_intake_runtime_execution_is_valid,
)
from app.application.downstream_realization_proof_application import (
    DownstreamProofInputs,
    current_blocker_clearing_proof_is_valid,
    supporting_source_contract_proof_is_valid,
)
from app.application.downstream_realization_readiness_models import (
    DownstreamReadinessComponents,
    DownstreamRealizationCapabilityReadiness,
    DownstreamRealizationContractReadiness,
    build_downstream_capability_readiness,
)
from app.application.report.intake_route_source_contract import (
    report_intake_route_source_contract_proof_is_valid,
)
from app.application.report.intake_runtime_execution import (
    REPORT_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    report_intake_runtime_execution_is_valid,
)
from app.application.report.materialization_source_contract import (
    REPORT_MATERIALIZATION_ROUTE,
    report_materialization_source_contract_is_valid,
)
from app.application.report.materialization_runtime_execution import (
    REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED,
    report_materialization_runtime_execution_is_valid,
)


def apply_available_downstream_proofs(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proofs: DownstreamProofInputs,
) -> DownstreamReadinessComponents:
    capabilities, downstream_contracts = _apply_source_contract_proofs_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        proofs=proofs,
    )
    return _apply_runtime_execution_proofs_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc,
        proofs=proofs,
    )


def _apply_source_contract_proofs_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    proofs: DownstreamProofInputs,
) -> DownstreamReadinessComponents:
    if supporting_source_contract_proof_is_valid(
        registry_key="advise_proposal_route_proof",
        proof=proofs.advise_proposal_route_proof,
        validator=advise_route_source_contract_is_valid,
    ):
        capabilities, downstream_contracts = _apply_route_source_contract(
            capabilities=capabilities,
            downstream_contracts=downstream_contracts,
            capability_id="advise-proposal-realization",
            contract_id="lotus-idea-to-lotus-advise-proposal-intake:v1",
            proof_ref=proofs.advise_proposal_route_proof_ref,
            target_route=ADVISE_PROPOSAL_ROUTE,
        )
    if supporting_source_contract_proof_is_valid(
        registry_key="manage_action_route_proof",
        proof=proofs.manage_action_route_proof,
        validator=manage_route_source_contract_is_valid,
    ):
        capabilities, downstream_contracts = _apply_route_source_contract(
            capabilities=capabilities,
            downstream_contracts=downstream_contracts,
            capability_id="manage-action-realization",
            contract_id="lotus-idea-to-lotus-manage-action-intake:v1",
            proof_ref=proofs.manage_action_route_proof_ref,
            target_route=MANAGE_ACTION_ROUTE,
        )
    return _apply_report_source_contract_proofs_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        report_intake_route_source_contract_proof=(
            proofs.report_intake_route_source_contract_proof
        ),
        report_intake_route_source_contract_proof_ref=(
            proofs.report_intake_route_source_contract_proof_ref
        ),
        report_materialization_source_contract_proof=(
            proofs.report_materialization_source_contract_proof
        ),
        report_materialization_source_contract_proof_ref=(
            proofs.report_materialization_source_contract_proof_ref
        ),
    )


def _apply_runtime_execution_proofs_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proofs: DownstreamProofInputs,
) -> DownstreamReadinessComponents:
    capabilities, downstream_contracts = _apply_advise_intake_proof_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc,
        proof=proofs.advise_intake_runtime_execution_proof,
        proof_ref=proofs.advise_intake_runtime_execution_proof_ref,
    )
    capabilities, downstream_contracts = _apply_manage_intake_proof_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc,
        proof=proofs.manage_intake_runtime_execution_proof,
        proof_ref=proofs.manage_intake_runtime_execution_proof_ref,
    )
    capabilities, downstream_contracts = _apply_report_intake_runtime_proof_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc,
        proof=proofs.report_intake_runtime_execution_proof,
        proof_ref=proofs.report_intake_runtime_execution_proof_ref,
    )
    return _apply_report_materialization_runtime_proof_if_valid(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc,
        proof=proofs.report_materialization_runtime_execution_proof,
        proof_ref=proofs.report_materialization_runtime_execution_proof_ref,
    )


def _apply_report_source_contract_proofs_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    report_intake_route_source_contract_proof: Mapping[str, object] | None,
    report_intake_route_source_contract_proof_ref: str | None,
    report_materialization_source_contract_proof: Mapping[str, object] | None,
    report_materialization_source_contract_proof_ref: str | None,
) -> DownstreamReadinessComponents:
    if _report_intake_route_source_contract_proof_is_registered_and_valid(
        report_intake_route_source_contract_proof
    ):
        capabilities = tuple(
            _apply_report_intake_route_source_contract_proof_to_capability(
                capability,
                report_intake_route_source_contract_proof_ref,
            )
            for capability in capabilities
        )
        downstream_contracts = tuple(
            _apply_report_intake_route_source_contract_proof_to_contract(
                contract,
                report_intake_route_source_contract_proof_ref,
            )
            for contract in downstream_contracts
        )
    if _report_materialization_source_contract_proof_is_registered_and_valid(
        report_materialization_source_contract_proof
    ):
        capabilities = tuple(
            _apply_report_materialization_source_contract_to_capability(
                capability,
                report_materialization_source_contract_proof_ref,
            )
            for capability in capabilities
        )
        downstream_contracts = tuple(
            _apply_report_materialization_source_contract_to_contract(
                contract,
                report_materialization_source_contract_proof_ref,
            )
            for contract in downstream_contracts
        )
    return capabilities, downstream_contracts


def _report_intake_route_source_contract_proof_is_registered_and_valid(
    proof: Mapping[str, object] | None,
) -> bool:
    return supporting_source_contract_proof_is_valid(
        registry_key="report_intake_route_source_contract_proof",
        proof=proof,
        validator=report_intake_route_source_contract_proof_is_valid,
    )


def _report_materialization_source_contract_proof_is_registered_and_valid(
    proof: Mapping[str, object] | None,
) -> bool:
    return supporting_source_contract_proof_is_valid(
        registry_key="report_materialization_source_contract_proof",
        proof=proof,
        validator=report_materialization_source_contract_is_valid,
    )


def _apply_advise_intake_proof_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    if not current_blocker_clearing_proof_is_valid(
        registry_key="advise_intake_runtime_execution_proof",
        proof=proof,
        proof_ref=proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        validator=advise_intake_runtime_execution_is_valid,
    ):
        return capabilities, downstream_contracts
    return _apply_advise_intake_runtime_execution(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        proof_ref=proof_ref,
    )


def _apply_manage_intake_proof_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    if not current_blocker_clearing_proof_is_valid(
        registry_key="manage_intake_runtime_execution_proof",
        proof=proof,
        proof_ref=proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        validator=manage_intake_runtime_execution_is_valid,
    ):
        return capabilities, downstream_contracts
    return _apply_manage_intake_runtime_execution(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        proof_ref=proof_ref,
    )


def _apply_report_materialization_runtime_proof_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    if not current_blocker_clearing_proof_is_valid(
        registry_key="report_materialization_runtime_execution_proof",
        proof=proof,
        proof_ref=proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        validator=report_materialization_runtime_execution_is_valid,
    ):
        return capabilities, downstream_contracts
    return _apply_report_materialization_runtime_execution(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        proof_ref=proof_ref,
    )


def _apply_report_intake_runtime_proof_if_valid(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    evaluated_at_utc: datetime,
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    if not current_blocker_clearing_proof_is_valid(
        registry_key="report_intake_runtime_execution_proof",
        proof=proof,
        proof_ref=proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        validator=report_intake_runtime_execution_is_valid,
    ):
        return capabilities, downstream_contracts
    return _apply_report_intake_runtime_execution(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        proof_ref=proof_ref,
    )


def _apply_advise_intake_runtime_execution(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    return (
        tuple(
            _apply_advise_intake_runtime_execution_to_capability(capability, proof_ref)
            for capability in capabilities
        ),
        tuple(
            _apply_advise_intake_runtime_execution_to_contract(contract, proof_ref)
            for contract in downstream_contracts
        ),
    )


def _apply_manage_intake_runtime_execution(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    return (
        tuple(
            _apply_manage_intake_runtime_execution_to_capability(capability, proof_ref)
            for capability in capabilities
        ),
        tuple(
            _apply_manage_intake_runtime_execution_to_contract(contract, proof_ref)
            for contract in downstream_contracts
        ),
    )


def _apply_report_materialization_runtime_execution(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    return (
        tuple(
            _apply_report_materialization_runtime_execution_to_capability(
                capability,
                proof_ref,
            )
            for capability in capabilities
        ),
        tuple(
            _apply_report_materialization_runtime_execution_to_contract(contract, proof_ref)
            for contract in downstream_contracts
        ),
    )


def _apply_report_intake_runtime_execution(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    proof_ref: str | None,
) -> DownstreamReadinessComponents:
    return (
        tuple(
            _apply_report_intake_runtime_execution_to_capability(capability, proof_ref)
            for capability in capabilities
        ),
        tuple(
            _apply_report_intake_runtime_execution_to_contract(contract, proof_ref)
            for contract in downstream_contracts
        ),
    )


def _apply_route_source_contract(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    capability_id: str,
    contract_id: str,
    proof_ref: str | None,
    target_route: str,
) -> DownstreamReadinessComponents:
    return (
        tuple(
            _apply_route_source_contract_to_capability(
                capability,
                capability_id=capability_id,
                proof_ref=proof_ref,
            )
            for capability in capabilities
        ),
        tuple(
            _apply_route_source_contract_to_contract(
                contract,
                contract_id=contract_id,
                proof_ref=proof_ref,
                target_route=target_route,
            )
            for contract in downstream_contracts
        ),
    )


def _apply_route_source_contract_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    *,
    capability_id: str,
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != capability_id:
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_route_source_contract_to_contract(
    contract: DownstreamRealizationContractReadiness,
    *,
    contract_id: str,
    proof_ref: str | None,
    target_route: str,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != contract_id:
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=target_route,
        route_fit_status=contract.route_fit_status,
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=contract.blockers,
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_advise_intake_runtime_execution_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "advise-proposal-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker not in ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_advise_intake_runtime_execution_to_contract(
    contract: DownstreamRealizationContractReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-advise-proposal-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=ADVISE_PROPOSAL_ROUTE,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in contract.blockers
            if blocker not in ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_manage_intake_runtime_execution_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "manage-action-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker not in MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_manage_intake_runtime_execution_to_contract(
    contract: DownstreamRealizationContractReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-manage-action-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=MANAGE_ACTION_ROUTE,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in contract.blockers
            if blocker not in MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_report_intake_route_source_contract_proof_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    report_intake_route_source_contract_proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "report-render-archive-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if report_intake_route_source_contract_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, report_intake_route_source_contract_proof_ref))
        )
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_report_intake_route_source_contract_proof_to_contract(
    contract: DownstreamRealizationContractReadiness,
    report_intake_route_source_contract_proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-report-evidence-pack-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if report_intake_route_source_contract_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, report_intake_route_source_contract_proof_ref))
        )
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=contract.target_route,
        route_fit_status=contract.route_fit_status,
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=contract.blockers,
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_report_materialization_source_contract_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    report_materialization_source_contract_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "report-render-archive-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if report_materialization_source_contract_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, report_materialization_source_contract_ref))
        )
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_report_materialization_source_contract_to_contract(
    contract: DownstreamRealizationContractReadiness,
    report_materialization_source_contract_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-report-evidence-pack-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if report_materialization_source_contract_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, report_materialization_source_contract_ref))
        )
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=contract.target_route,
        route_fit_status=contract.route_fit_status,
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=contract.blockers,
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_report_materialization_runtime_execution_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "report-render-archive-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker not in REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_report_intake_runtime_execution_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "report-render-archive-realization":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_downstream_capability_readiness(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker not in REPORT_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=capability.blocker_issue_refs,
    )


def _apply_report_intake_runtime_execution_to_contract(
    contract: DownstreamRealizationContractReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-report-evidence-pack-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=contract.target_route,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in contract.blockers
            if blocker not in REPORT_INTAKE_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=contract.blocker_issue_refs,
    )


def _apply_report_materialization_runtime_execution_to_contract(
    contract: DownstreamRealizationContractReadiness,
    proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-report-evidence-pack-intake:v1":
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=REPORT_MATERIALIZATION_ROUTE,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in contract.blockers
            if blocker not in REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED
        ),
        blocker_issue_refs=contract.blocker_issue_refs,
    )
