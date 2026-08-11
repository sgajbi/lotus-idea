from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping

from app.application.downstream_realization_proof_application import DownstreamProofInputs
from app.application.downstream_realization_readiness_catalog import (
    initial_downstream_readiness_components,
)
from app.application.downstream_realization_readiness_models import (
    DownstreamRealizationCapabilityReadiness as DownstreamRealizationCapabilityReadiness,
    DownstreamRealizationContractReadiness as DownstreamRealizationContractReadiness,
    DownstreamRealizationReadinessSnapshot as DownstreamRealizationReadinessSnapshot,
)
from app.application.downstream_realization_readiness_proofs import (
    apply_available_downstream_proofs,
)
from app.domain.conversion_governance import GovernedConversionOutcome
from app.domain.conversion_outcome_policy import current_conversion_outcome_identity
from app.domain.downstream_submission import DownstreamSubmissionPosture
from app.ports.idea_repository import (
    CandidateSnapshotRepository,
    DownstreamRealizationReadinessProjectionRepository,
    DownstreamRealizationReadinessRepositorySummary,
)


__all__ = [
    "DownstreamRealizationCapabilityReadiness",
    "DownstreamRealizationContractReadiness",
    "DownstreamRealizationReadinessSnapshot",
    "build_downstream_realization_readiness_snapshot",
]


def build_downstream_realization_readiness_snapshot(
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    evaluated_at_utc: datetime | None = None,
    advise_proposal_route_proof: Mapping[str, object] | None = None,
    advise_proposal_route_proof_ref: str | None = None,
    advise_intake_runtime_execution_proof: Mapping[str, object] | None = None,
    advise_intake_runtime_execution_proof_ref: str | None = None,
    manage_intake_runtime_execution_proof: Mapping[str, object] | None = None,
    manage_intake_runtime_execution_proof_ref: str | None = None,
    manage_action_route_proof: Mapping[str, object] | None = None,
    manage_action_route_proof_ref: str | None = None,
    report_intake_route_source_contract_proof: Mapping[str, object] | None = None,
    report_intake_route_source_contract_proof_ref: str | None = None,
    report_intake_runtime_execution_proof: Mapping[str, object] | None = None,
    report_intake_runtime_execution_proof_ref: str | None = None,
    report_materialization_source_contract_proof: Mapping[str, object] | None = None,
    report_materialization_source_contract_proof_ref: str | None = None,
    report_materialization_runtime_execution_proof: Mapping[str, object] | None = None,
    report_materialization_runtime_execution_proof_ref: str | None = None,
) -> DownstreamRealizationReadinessSnapshot:
    readiness_summary = _downstream_realization_readiness_summary(repository)
    capabilities, downstream_contracts = initial_downstream_readiness_components()
    capabilities, downstream_contracts = apply_available_downstream_proofs(
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        evaluated_at_utc=evaluated_at_utc or datetime.now(UTC),
        proofs=DownstreamProofInputs(
            advise_proposal_route_proof=advise_proposal_route_proof,
            advise_proposal_route_proof_ref=advise_proposal_route_proof_ref,
            advise_intake_runtime_execution_proof=advise_intake_runtime_execution_proof,
            advise_intake_runtime_execution_proof_ref=advise_intake_runtime_execution_proof_ref,
            manage_intake_runtime_execution_proof=manage_intake_runtime_execution_proof,
            manage_intake_runtime_execution_proof_ref=manage_intake_runtime_execution_proof_ref,
            manage_action_route_proof=manage_action_route_proof,
            manage_action_route_proof_ref=manage_action_route_proof_ref,
            report_intake_route_source_contract_proof=report_intake_route_source_contract_proof,
            report_intake_route_source_contract_proof_ref=(
                report_intake_route_source_contract_proof_ref
            ),
            report_intake_runtime_execution_proof=report_intake_runtime_execution_proof,
            report_intake_runtime_execution_proof_ref=report_intake_runtime_execution_proof_ref,
            report_materialization_source_contract_proof=(
                report_materialization_source_contract_proof
            ),
            report_materialization_source_contract_proof_ref=(
                report_materialization_source_contract_proof_ref
            ),
            report_materialization_runtime_execution_proof=(
                report_materialization_runtime_execution_proof
            ),
            report_materialization_runtime_execution_proof_ref=(
                report_materialization_runtime_execution_proof_ref
            ),
        ),
    )
    blockers = _aggregate_downstream_blockers(capabilities, downstream_contracts)
    blocker_issue_refs = _merge_blocker_issue_refs(capabilities, downstream_contracts)
    certification_ready = not blockers
    return _build_downstream_readiness_snapshot(
        readiness_summary=readiness_summary,
        durable_storage_backed=durable_storage_backed,
        certification_ready=certification_ready,
        blockers=blockers,
        blocker_issue_refs=blocker_issue_refs,
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
    )


def _aggregate_downstream_blockers(
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
) -> tuple[str, ...]:
    capability_blockers = tuple(
        blocker for capability in capabilities for blocker in capability.blockers
    )
    contract_blockers = tuple(
        blocker for contract in downstream_contracts for blocker in contract.blockers
    )
    return tuple(dict.fromkeys((*capability_blockers, *contract_blockers)))


def _build_downstream_readiness_snapshot(
    *,
    readiness_summary: DownstreamRealizationReadinessRepositorySummary,
    durable_storage_backed: bool,
    certification_ready: bool,
    blockers: tuple[str, ...],
    blocker_issue_refs: Mapping[str, tuple[str, ...]],
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
) -> DownstreamRealizationReadinessSnapshot:
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
        source_of_truth=_downstream_realization_source_of_truth(),
        blockers=blockers,
        blocker_issue_refs=blocker_issue_refs,
        capabilities=capabilities,
        downstream_contracts=downstream_contracts,
        supported_feature_promoted=False,
    )


def _downstream_realization_source_of_truth() -> Mapping[str, str]:
    return {
        "conversion_workflow": "src/app/application/conversion_workflow.py",
        "report_evidence_workflow": "src/app/application/report_evidence.py",
        "downstream_realization_orchestration": "src/app/application/downstream_realization.py",
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
    }


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


def _merge_blocker_issue_refs(
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...],
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...],
) -> Mapping[str, tuple[str, ...]]:
    merged: dict[str, tuple[str, ...]] = {}
    for capability in capabilities:
        for blocker, issue_refs in capability.blocker_issue_refs.items():
            merged[blocker] = tuple(dict.fromkeys((*merged.get(blocker, ()), *issue_refs)))
    for downstream_contract in downstream_contracts:
        for blocker, issue_refs in downstream_contract.blocker_issue_refs.items():
            merged[blocker] = tuple(dict.fromkeys((*merged.get(blocker, ()), *issue_refs)))
    return merged
