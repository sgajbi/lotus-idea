from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.application.downstream_realization_contracts import (
    DownstreamRealizationContractPlanRecord,
    load_downstream_realization_contract_plan,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_ROUTE_BLOCKERS_CLEARED,
    MANAGE_ACTION_ROUTE,
    MANAGE_ROUTE_BLOCKERS_CLEARED,
    advise_proposal_route_proof_is_valid,
    manage_action_route_proof_is_valid,
)
from app.application.report_intake_route_proof import (
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    report_intake_route_proof_is_valid,
)
from app.ports.idea_repository import CandidateSnapshotRepository


@dataclass(frozen=True)
class DownstreamRealizationCapabilityReadiness:
    capability_id: str
    name: str
    source_authority: str
    readiness_status: str
    supportability_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))


@dataclass(frozen=True)
class DownstreamRealizationContractReadiness:
    contract_id: str
    owner_repository: str
    source_authority: str
    target_route: str
    route_fit_status: str
    adapter_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))


@dataclass(frozen=True)
class DownstreamRealizationReadinessSnapshot:
    repository: str
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    durable_storage_backed: bool
    conversion_intent_count: int
    conversion_outcome_count: int
    report_evidence_pack_request_count: int
    downstream_adapter_foundation_present: bool
    source_of_truth: Mapping[str, str]
    blockers: tuple[str, ...]
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...]
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...]
    supported_feature_promoted: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_of_truth",
            MappingProxyType(dict(self.source_of_truth)),
        )
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(
            self,
            "downstream_contracts",
            tuple(self.downstream_contracts),
        )


def build_downstream_realization_readiness_snapshot(
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    advise_proposal_route_proof: Mapping[str, object] | None = None,
    advise_proposal_route_proof_ref: str | None = None,
    manage_action_route_proof: Mapping[str, object] | None = None,
    manage_action_route_proof_ref: str | None = None,
    report_intake_route_proof: Mapping[str, object] | None = None,
    report_intake_route_proof_ref: str | None = None,
) -> DownstreamRealizationReadinessSnapshot:
    snapshot = repository.snapshot()
    records = tuple(snapshot.candidate_records.values())
    conversion_intent_count = sum(len(record.conversion_intents) for record in records)
    conversion_outcome_count = sum(len(record.conversion_outcomes) for record in records)
    report_evidence_pack_request_count = sum(
        len(record.report_evidence_packs) for record in records
    )
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...] = (
        _advise_conversion_capability(),
        _manage_conversion_capability(),
        _report_render_archive_capability(),
    )
    contract_plan = load_downstream_realization_contract_plan()
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...] = tuple(
        _downstream_contract_from_plan(record) for record in contract_plan.contracts
    )
    if advise_proposal_route_proof and advise_proposal_route_proof_is_valid(
        advise_proposal_route_proof
    ):
        capabilities = tuple(
            _apply_route_proof_to_capability(
                capability,
                capability_id="advise-proposal-realization",
                blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=advise_proposal_route_proof_ref,
            )
            for capability in capabilities
        )
        downstream_contracts = tuple(
            _apply_route_proof_to_contract(
                contract,
                contract_id="lotus-idea-to-lotus-advise-proposal-intake:v1",
                blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=advise_proposal_route_proof_ref,
                target_route=ADVISE_PROPOSAL_ROUTE,
            )
            for contract in downstream_contracts
        )
    if manage_action_route_proof and manage_action_route_proof_is_valid(manage_action_route_proof):
        capabilities = tuple(
            _apply_route_proof_to_capability(
                capability,
                capability_id="manage-action-realization",
                blockers_cleared=MANAGE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=manage_action_route_proof_ref,
            )
            for capability in capabilities
        )
        downstream_contracts = tuple(
            _apply_route_proof_to_contract(
                contract,
                contract_id="lotus-idea-to-lotus-manage-action-intake:v1",
                blockers_cleared=MANAGE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=manage_action_route_proof_ref,
                target_route=MANAGE_ACTION_ROUTE,
            )
            for contract in downstream_contracts
        )
    if report_intake_route_proof and report_intake_route_proof_is_valid(report_intake_route_proof):
        capabilities = tuple(
            _apply_report_intake_route_proof_to_capability(
                capability,
                report_intake_route_proof_ref,
            )
            for capability in capabilities
        )
        downstream_contracts = tuple(
            _apply_report_intake_route_proof_to_contract(
                contract,
                report_intake_route_proof_ref,
            )
            for contract in downstream_contracts
        )
    capability_blockers = tuple(
        blocker for capability in capabilities for blocker in capability.blockers
    )
    contract_blockers = tuple(
        blocker for contract in downstream_contracts for blocker in contract.blockers
    )
    blockers = tuple(dict.fromkeys((*capability_blockers, *contract_blockers)))
    certification_ready = not blockers
    return DownstreamRealizationReadinessSnapshot(
        repository="lotus-idea",
        readiness_status=("ready" if certification_ready else "blocked"),
        supportability_status=("supported" if certification_ready else "not_certified"),
        certification_ready=certification_ready,
        durable_storage_backed=durable_storage_backed,
        conversion_intent_count=conversion_intent_count,
        conversion_outcome_count=conversion_outcome_count,
        report_evidence_pack_request_count=report_evidence_pack_request_count,
        downstream_adapter_foundation_present=True,
        source_of_truth={
            "conversion_workflow": "src/app/application/conversion_workflow.py",
            "report_evidence_workflow": "src/app/application/report_evidence.py",
            "downstream_realization_orchestration": (
                "src/app/application/downstream_realization.py"
            ),
            "downstream_realization_api": "src/app/api/downstream_realization.py",
            "downstream_adapter_port": "src/app/ports/downstream_realization.py",
            "downstream_adapter_foundation": "src/app/infrastructure/downstream_realization.py",
            "downstream_contract_plan": (
                "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json"
            ),
            "downstream_contract_gate": "scripts/downstream_realization_contract_gate.py",
            "rfc_slice_12": (
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                "RFC-0002-slice-12-advise-and-manage-conversion-realization.md"
            ),
            "rfc_slice_13": (
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                "RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md"
            ),
        },
        blockers=blockers,
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        supported_feature_promoted=False,
    )


def _capability(
    capability_id: str,
    name: str,
    source_authority: str,
    *,
    evidence_refs: tuple[str, ...],
    blockers: tuple[str, ...],
) -> DownstreamRealizationCapabilityReadiness:
    return DownstreamRealizationCapabilityReadiness(
        capability_id=capability_id,
        name=name,
        source_authority=source_authority,
        readiness_status="planned",
        supportability_status="not_certified",
        evidence_refs=evidence_refs,
        blockers=blockers,
    )


def _advise_conversion_capability() -> DownstreamRealizationCapabilityReadiness:
    return _capability(
        "advise-proposal-realization",
        "Advise proposal and suitability realization",
        "lotus-advise",
        evidence_refs=(
            "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
            "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "suitability_policy_authority_remains_lotus_advise",
            "advise_live_contract_proof_missing",
        ),
    )


def _manage_conversion_capability() -> DownstreamRealizationCapabilityReadiness:
    return _capability(
        "manage-action-realization",
        "Manage action register and implementation realization",
        "lotus-manage",
        evidence_refs=(
            "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
            "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "rebalance_execution_authority_remains_lotus_manage",
            "manage_live_contract_proof_missing",
        ),
    )


def _report_render_archive_capability() -> DownstreamRealizationCapabilityReadiness:
    return _capability(
        "report-render-archive-realization",
        "Report, Render, and Archive evidence-pack materialization",
        "lotus-report",
        evidence_refs=(
            "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
            "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
            "lotus-render",
            "lotus-archive",
        ),
        blockers=(
            "report_evidence_pack_live_materialization_proof_missing",
            "rendered_output_creation_missing",
            "archive_record_creation_missing",
            "client_publication_authority_blocked",
        ),
    )


def _downstream_contract_from_plan(
    record: DownstreamRealizationContractPlanRecord,
) -> DownstreamRealizationContractReadiness:
    return DownstreamRealizationContractReadiness(
        contract_id=record.contract_id,
        owner_repository=record.owner_repository,
        source_authority=record.source_authority,
        target_route=record.target_route,
        route_fit_status=record.route_fit_status,
        adapter_status=record.adapter_status,
        evidence_refs=record.evidence_refs,
        blockers=record.blockers,
    )


def _apply_route_proof_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    *,
    capability_id: str,
    blockers_cleared: tuple[str, ...],
    proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != capability_id:
        return capability
    blockers_to_clear = set(blockers_cleared)
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
    )


def _apply_route_proof_to_contract(
    contract: DownstreamRealizationContractReadiness,
    *,
    contract_id: str,
    blockers_cleared: tuple[str, ...],
    proof_ref: str | None,
    target_route: str,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != contract_id:
        return contract
    blockers_to_clear = set(blockers_cleared)
    if not blockers_to_clear.intersection(contract.blockers):
        return contract
    evidence_refs = contract.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=target_route,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in contract.blockers if blocker not in blockers_to_clear
        ),
    )


def _apply_report_intake_route_proof_to_capability(
    capability: DownstreamRealizationCapabilityReadiness,
    report_intake_route_proof_ref: str | None,
) -> DownstreamRealizationCapabilityReadiness:
    if capability.capability_id != "report-render-archive-realization":
        return capability
    blockers_to_clear = set(REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED)
    evidence_refs = capability.evidence_refs
    if report_intake_route_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, report_intake_route_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        capability.source_authority,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
    )


def _apply_report_intake_route_proof_to_contract(
    contract: DownstreamRealizationContractReadiness,
    report_intake_route_proof_ref: str | None,
) -> DownstreamRealizationContractReadiness:
    if contract.contract_id != "lotus-idea-to-lotus-report-evidence-pack-intake:v1":
        return contract
    blockers_to_clear = set(REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED)
    if not blockers_to_clear.intersection(contract.blockers):
        return contract
    evidence_refs = contract.evidence_refs
    if report_intake_route_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, report_intake_route_proof_ref)))
    return DownstreamRealizationContractReadiness(
        contract_id=contract.contract_id,
        owner_repository=contract.owner_repository,
        source_authority=contract.source_authority,
        target_route=REPORT_INTAKE_ROUTE,
        route_fit_status="route_foundation_proven_not_certified",
        adapter_status=contract.adapter_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in contract.blockers if blocker not in blockers_to_clear
        ),
    )
