from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.application.downstream_realization_contracts import (
    DownstreamRealizationContractPlanRecord,
    load_downstream_realization_contract_plan,
)
from app.application.downstream_realization_issue_refs import capability_blocker_issue_refs
from app.application.downstream_realization.route_source_contract import (
    ADVISE_PROPOSAL_ROUTE,
    MANAGE_ACTION_ROUTE,
    advise_route_source_contract_is_valid,
    manage_route_source_contract_is_valid,
)
from app.application.implementation_proof_artifact_registry import (
    ProofArtifactEffect,
    proof_artifact_effect_matches_payload,
)
from app.application.report.intake_route_source_contract import (
    report_intake_route_source_contract_proof_is_valid,
)
from app.application.report.materialization_source_contract import (
    report_materialization_source_contract_is_valid,
)
from app.domain.conversion_governance import GovernedConversionOutcome
from app.domain.conversion_outcome_policy import current_conversion_outcome_identity
from app.domain.downstream_submission import DownstreamSubmissionPosture
from app.ports.idea_repository import (
    CandidateSnapshotRepository,
    DownstreamRealizationReadinessProjectionRepository,
    DownstreamRealizationReadinessRepositorySummary,
)


@dataclass(frozen=True)
class DownstreamRealizationCapabilityReadiness:
    capability_id: str
    name: str
    source_authority: str
    readiness_status: str
    supportability_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        _freeze_blocker_readiness(self)


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
    blocker_issue_refs: Mapping[str, tuple[str, ...]]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        _freeze_blocker_readiness(self)


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
    downstream_submission_count: int
    downstream_reconciliation_required_count: int
    downstream_adapter_foundation_present: bool
    source_of_truth: Mapping[str, str]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]
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
        object.__setattr__(
            self,
            "blocker_issue_refs",
            _immutable_issue_refs(self.blocker_issue_refs),
        )
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
    report_intake_route_source_contract_proof: Mapping[str, object] | None = None,
    report_intake_route_source_contract_proof_ref: str | None = None,
    report_materialization_source_contract_proof: Mapping[str, object] | None = None,
    report_materialization_source_contract_proof_ref: str | None = None,
) -> DownstreamRealizationReadinessSnapshot:
    readiness_summary = _downstream_realization_readiness_summary(repository)
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...] = (
        _advise_conversion_capability(),
        _manage_conversion_capability(),
        _report_render_archive_capability(),
    )
    contract_plan = load_downstream_realization_contract_plan()
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...] = tuple(
        _downstream_contract_from_plan(record) for record in contract_plan.contracts
    )
    capabilities, downstream_contracts = _apply_available_downstream_proofs(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        advise_proposal_route_proof=advise_proposal_route_proof,
        advise_proposal_route_proof_ref=advise_proposal_route_proof_ref,
        manage_action_route_proof=manage_action_route_proof,
        manage_action_route_proof_ref=manage_action_route_proof_ref,
        report_intake_route_source_contract_proof=report_intake_route_source_contract_proof,
        report_intake_route_source_contract_proof_ref=report_intake_route_source_contract_proof_ref,
        report_materialization_source_contract_proof=report_materialization_source_contract_proof,
        report_materialization_source_contract_proof_ref=(
            report_materialization_source_contract_proof_ref
        ),
    )
    capability_blockers = tuple(
        blocker for capability in capabilities for blocker in capability.blockers
    )
    contract_blockers = tuple(
        blocker for contract in downstream_contracts for blocker in contract.blockers
    )
    blockers = tuple(dict.fromkeys((*capability_blockers, *contract_blockers)))
    blocker_issue_refs = _merge_blocker_issue_refs(capabilities, downstream_contracts)
    certification_ready = not blockers
    return DownstreamRealizationReadinessSnapshot(
        repository="lotus-idea",
        readiness_status=("ready" if certification_ready else "blocked"),
        supportability_status=("supported" if certification_ready else "not_certified"),
        certification_ready=certification_ready,
        durable_storage_backed=durable_storage_backed,
        conversion_intent_count=readiness_summary.conversion_intent_count,
        conversion_outcome_count=readiness_summary.conversion_outcome_count,
        report_evidence_pack_request_count=(readiness_summary.report_evidence_pack_request_count),
        downstream_submission_count=readiness_summary.downstream_submission_count,
        downstream_reconciliation_required_count=(
            readiness_summary.downstream_reconciliation_required_count
        ),
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
            "downstream_submission_reconciliation": (
                "src/app/application/downstream_submission_reconciliation.py"
            ),
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
        blocker_issue_refs=blocker_issue_refs,
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        supported_feature_promoted=False,
    )


def _downstream_realization_readiness_summary(
    repository: CandidateSnapshotRepository,
) -> DownstreamRealizationReadinessRepositorySummary:
    if isinstance(repository, DownstreamRealizationReadinessProjectionRepository):
        return repository.downstream_realization_readiness_summary()
    snapshot = repository.snapshot()
    records = tuple(snapshot.candidate_records.values())
    return DownstreamRealizationReadinessRepositorySummary(
        conversion_intent_count=sum(len(record.conversion_intents) for record in records),
        conversion_outcome_count=sum(
            _valid_conversion_outcome_stream_count(record.conversion_outcomes) for record in records
        ),
        report_evidence_pack_request_count=sum(
            len(record.report_evidence_packs) for record in records
        ),
        downstream_submission_count=len(snapshot.downstream_submission_records),
        downstream_reconciliation_required_count=sum(
            1
            for record in snapshot.downstream_submission_records.values()
            if record.status
            in {
                DownstreamSubmissionPosture.IN_FLIGHT,
                DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            }
        ),
    )


def _valid_conversion_outcome_stream_count(
    outcomes: tuple[GovernedConversionOutcome, ...],
) -> int:
    intent_ids = {outcome.conversion_intent_id for outcome in outcomes}
    return sum(
        current_conversion_outcome_identity(
            tuple(
                outcome.identity
                for outcome in outcomes
                if outcome.conversion_intent_id == intent_id
            )
        )
        is not None
        for intent_id in intent_ids
    )


def _apply_available_downstream_proofs(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    advise_proposal_route_proof: Mapping[str, object] | None,
    advise_proposal_route_proof_ref: str | None,
    manage_action_route_proof: Mapping[str, object] | None,
    manage_action_route_proof_ref: str | None,
    report_intake_route_source_contract_proof: Mapping[str, object] | None,
    report_intake_route_source_contract_proof_ref: str | None,
    report_materialization_source_contract_proof: Mapping[str, object] | None,
    report_materialization_source_contract_proof_ref: str | None,
) -> tuple[
    tuple[DownstreamRealizationCapabilityReadiness, ...],
    tuple[DownstreamRealizationContractReadiness, ...],
]:
    if (
        proof_artifact_effect_matches_payload(
            "advise_proposal_route_proof",
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        )
        and advise_proposal_route_proof
        and advise_route_source_contract_is_valid(advise_proposal_route_proof)
    ):
        capabilities, downstream_contracts = _apply_route_source_contract(
            capabilities=capabilities,
            downstream_contracts=downstream_contracts,
            capability_id="advise-proposal-realization",
            contract_id="lotus-idea-to-lotus-advise-proposal-intake:v1",
            proof_ref=advise_proposal_route_proof_ref,
            target_route=ADVISE_PROPOSAL_ROUTE,
        )
    if (
        proof_artifact_effect_matches_payload(
            "manage_action_route_proof",
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        )
        and manage_action_route_proof
        and manage_route_source_contract_is_valid(manage_action_route_proof)
    ):
        capabilities, downstream_contracts = _apply_route_source_contract(
            capabilities=capabilities,
            downstream_contracts=downstream_contracts,
            capability_id="manage-action-realization",
            contract_id="lotus-idea-to-lotus-manage-action-intake:v1",
            proof_ref=manage_action_route_proof_ref,
            target_route=MANAGE_ACTION_ROUTE,
        )
    if (
        proof_artifact_effect_matches_payload(
            "report_intake_route_source_contract_proof",
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        )
        and report_intake_route_source_contract_proof
        and report_intake_route_source_contract_proof_is_valid(
            report_intake_route_source_contract_proof
        )
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
    if (
        proof_artifact_effect_matches_payload(
            "report_materialization_source_contract_proof",
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        )
        and report_materialization_source_contract_proof
        and report_materialization_source_contract_is_valid(
            report_materialization_source_contract_proof
        )
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


def _apply_route_source_contract(
    *,
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
    capability_id: str,
    contract_id: str,
    proof_ref: str | None,
    target_route: str,
) -> tuple[
    tuple[DownstreamRealizationCapabilityReadiness, ...],
    tuple[DownstreamRealizationContractReadiness, ...],
]:
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


def _capability(
    capability_id: str,
    name: str,
    source_authority: str,
    *,
    evidence_refs: tuple[str, ...],
    blockers: tuple[str, ...],
    blocker_issue_refs: Mapping[str, tuple[str, ...]],
) -> DownstreamRealizationCapabilityReadiness:
    return DownstreamRealizationCapabilityReadiness(
        capability_id=capability_id,
        name=name,
        source_authority=source_authority,
        readiness_status="planned",
        supportability_status="not_certified",
        evidence_refs=evidence_refs,
        blockers=blockers,
        blocker_issue_refs=blocker_issue_refs,
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
        blocker_issue_refs=capability_blocker_issue_refs("advise-proposal-realization"),
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
        blocker_issue_refs=capability_blocker_issue_refs("manage-action-realization"),
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
        blocker_issue_refs=capability_blocker_issue_refs("report-render-archive-realization"),
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
        blocker_issue_refs=record.blocker_issue_refs,
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
    return _capability(
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
    return _capability(
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
    return _capability(
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


def _merge_blocker_issue_refs(
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
) -> Mapping[str, tuple[str, ...]]:
    merged: dict[str, tuple[str, ...]] = {}
    for readiness in (*capabilities, *downstream_contracts):
        for blocker, issue_refs in readiness.blocker_issue_refs.items():
            merged[blocker] = tuple(dict.fromkeys((*merged.get(blocker, ()), *issue_refs)))
    return merged


def _immutable_issue_refs(
    issue_refs: Mapping[str, tuple[str, ...]],
) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType(
        {
            str(blocker): tuple(str(issue_ref) for issue_ref in refs)
            for blocker, refs in issue_refs.items()
        }
    )


def _freeze_blocker_readiness(
    readiness: DownstreamRealizationCapabilityReadiness | DownstreamRealizationContractReadiness,
) -> None:
    object.__setattr__(readiness, "evidence_refs", tuple(readiness.evidence_refs))
    object.__setattr__(readiness, "blockers", tuple(readiness.blockers))
    object.__setattr__(
        readiness,
        "blocker_issue_refs",
        _immutable_issue_refs(readiness.blocker_issue_refs),
    )
