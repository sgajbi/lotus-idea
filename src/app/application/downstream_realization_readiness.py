from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

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
) -> DownstreamRealizationReadinessSnapshot:
    snapshot = repository.snapshot()
    records = tuple(snapshot.candidate_records.values())
    conversion_intent_count = sum(len(record.conversion_intents) for record in records)
    conversion_outcome_count = sum(len(record.conversion_outcomes) for record in records)
    report_evidence_pack_request_count = sum(
        len(record.report_evidence_packs) for record in records
    )
    capabilities = (
        _advise_conversion_capability(),
        _manage_conversion_capability(),
        _report_render_archive_capability(),
    )
    downstream_contracts = _downstream_contracts()
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
        source_of_truth={
            "conversion_workflow": "src/app/application/conversion_workflow.py",
            "report_evidence_workflow": "src/app/application/report_evidence.py",
            "downstream_contract_plan": ("src/app/application/downstream_realization_readiness.py"),
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
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "advise_proposal_creation_adapter_missing",
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
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "manage_action_register_adapter_missing",
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
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
            "lotus-render",
            "lotus-archive",
        ),
        blockers=(
            "report_evidence_pack_materialization_missing",
            "rendered_output_creation_missing",
            "archive_record_creation_missing",
            "client_publication_authority_blocked",
        ),
    )


def _downstream_contracts() -> tuple[DownstreamRealizationContractReadiness, ...]:
    return (
        DownstreamRealizationContractReadiness(
            contract_id="lotus-idea-to-lotus-advise-proposal-intake:v1",
            owner_repository="lotus-advise",
            source_authority="lotus-advise",
            target_route="planned:lotus-advise-proposal-intake",
            route_fit_status="not_certified",
            adapter_status="planned",
            evidence_refs=(
                "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
                "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
            ),
            blockers=(
                "advise_proposal_creation_adapter_missing",
                "suitability_policy_authority_remains_lotus_advise",
                "advise_live_contract_proof_missing",
            ),
        ),
        DownstreamRealizationContractReadiness(
            contract_id="lotus-idea-to-lotus-manage-action-intake:v1",
            owner_repository="lotus-manage",
            source_authority="lotus-manage",
            target_route="planned:lotus-manage-action-intake",
            route_fit_status="not_certified",
            adapter_status="planned",
            evidence_refs=(
                "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
                "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
            ),
            blockers=(
                "manage_action_register_adapter_missing",
                "rebalance_execution_authority_remains_lotus_manage",
                "manage_live_contract_proof_missing",
            ),
        ),
        DownstreamRealizationContractReadiness(
            contract_id="lotus-idea-to-lotus-report-evidence-pack-intake:v1",
            owner_repository="lotus-report",
            source_authority="lotus-report",
            target_route="planned:lotus-report-idea-evidence-pack-intake",
            route_fit_status="not_certified",
            adapter_status="planned",
            evidence_refs=(
                "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
                "lotus-render",
                "lotus-archive",
            ),
            blockers=(
                "dedicated_report_idea_evidence_intake_contract_missing",
                "report_evidence_pack_materialization_missing",
                "rendered_output_creation_missing",
                "archive_record_creation_missing",
                "client_publication_authority_blocked",
            ),
        ),
    )
