from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from app.application.downstream_realization_readiness import (
    build_downstream_realization_readiness_snapshot,
)
from app.application.downstream_realization.route_source_contract import (
    ADVISE_PROPOSAL_ROUTE,
    MANAGE_ACTION_ROUTE,
)
from app.application.report.intake_route_source_contract import (
    REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
)
from app.application.report.materialization_source_contract import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_ROUTE,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
)
from app.domain import (
    ConversionOutcomeIdentity,
    ConversionOutcomeStatus,
    ConversionTarget,
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    SourceSystem,
)
from app.ports.idea_repository import DownstreamRealizationReadinessRepositorySummary
from tests.unit.downstream_realization.fixtures import (
    valid_advise_route_source_contract,
    valid_manage_route_source_contract,
)


@dataclass(frozen=True)
class _WorkflowRecord:
    conversion_intents: tuple[object, ...] = ()
    conversion_outcomes: tuple[object, ...] = ()
    report_evidence_packs: tuple[object, ...] = ()


@dataclass(frozen=True)
class _Outcome:
    identity: ConversionOutcomeIdentity

    @property
    def conversion_intent_id(self) -> str:
        return self.identity.conversion_intent_id


def _outcome(
    status: ConversionOutcomeStatus,
    *,
    outcome_id: str,
    version: int,
    minute: int,
) -> _Outcome:
    return _Outcome(
        ConversionOutcomeIdentity(
            conversion_outcome_id=outcome_id,
            conversion_intent_id="intent-001",
            target=ConversionTarget.REPORT_EVIDENCE,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=version,
            status=status,
            downstream_reference=(
                "report-evidence-001"
                if status in {ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED}
                else None
            ),
            recorded_at_utc=datetime(2026, 6, 21, 10, tzinfo=UTC) + timedelta(minutes=minute),
            actor_subject="lotus-report-worker",
        )
    )


def test_downstream_realization_readiness_reports_blocked_foundation_posture() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    assert snapshot.repository == "lotus-idea"
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.durable_storage_backed is False
    assert snapshot.conversion_intent_count == 0
    assert snapshot.conversion_outcome_count == 0
    assert snapshot.report_evidence_pack_request_count == 0
    assert snapshot.downstream_adapter_foundation_present is True
    assert snapshot.supported_feature_promoted is False
    assert "advise_proposal_creation_adapter_missing" not in snapshot.blockers
    assert "manage_action_register_adapter_missing" not in snapshot.blockers
    assert "report_evidence_pack_materialization_missing" not in snapshot.blockers
    assert "advise_live_contract_proof_missing" in snapshot.blockers
    assert "manage_live_contract_proof_missing" in snapshot.blockers
    assert "lotus_report_live_intake_route_proof_missing" in snapshot.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in snapshot.blockers
    assert "dedicated_report_idea_evidence_intake_contract_missing" not in snapshot.blockers
    assert set(snapshot.source_of_truth) == {
        "conversion_workflow",
        "report_evidence_workflow",
        "downstream_realization_orchestration",
        "downstream_realization_api",
        "downstream_adapter_port",
        "downstream_adapter_foundation",
        "downstream_contract_plan",
        "downstream_contract_gate",
        "rfc_slice_12",
        "rfc_slice_13",
    }
    assert len(snapshot.downstream_contracts) == 3


def test_downstream_realization_readiness_counts_internal_workflow_records() -> None:
    repository = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={
                "idea-candidate-redacted": cast(
                    Any,
                    _WorkflowRecord(
                        conversion_intents=(object(), object()),
                        conversion_outcomes=(
                            _outcome(
                                ConversionOutcomeStatus.REQUESTED,
                                outcome_id="outcome-001",
                                version=1,
                                minute=0,
                            ),
                            _outcome(
                                ConversionOutcomeStatus.ACCEPTED,
                                outcome_id="outcome-002",
                                version=2,
                                minute=1,
                            ),
                        ),
                        report_evidence_packs=(object(),),
                    ),
                )
            },
            idempotency_records={},
            idempotency_candidates={},
        )
    )

    snapshot = build_downstream_realization_readiness_snapshot(
        repository=repository,
        durable_storage_backed=True,
    )

    assert snapshot.durable_storage_backed is True
    assert snapshot.conversion_intent_count == 2
    assert snapshot.conversion_outcome_count == 1
    assert snapshot.report_evidence_pack_request_count == 1
    assert snapshot.certification_ready is False


def test_downstream_realization_readiness_excludes_invalid_outcome_history() -> None:
    record = _WorkflowRecord(
        conversion_outcomes=(
            _outcome(
                ConversionOutcomeStatus.REJECTED,
                outcome_id="outcome-001",
                version=1,
                minute=0,
            ),
            _outcome(
                ConversionOutcomeStatus.ACCEPTED,
                outcome_id="outcome-002",
                version=2,
                minute=1,
            ),
        )
    )
    repository = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={"idea-candidate-redacted": cast(Any, record)},
            idempotency_records={},
            idempotency_candidates={},
        )
    )

    snapshot = build_downstream_realization_readiness_snapshot(
        repository=repository,
        durable_storage_backed=False,
    )

    assert snapshot.conversion_outcome_count == 0


def test_downstream_realization_readiness_uses_repository_projection_without_snapshot() -> None:
    repository = _ProjectionOnlyDownstreamReadinessRepository(
        DownstreamRealizationReadinessRepositorySummary(
            conversion_intent_count=2,
            conversion_outcome_count=1,
            report_evidence_pack_request_count=3,
        )
    )

    snapshot = build_downstream_realization_readiness_snapshot(
        repository=repository,
        durable_storage_backed=True,
    )

    assert repository.projection_calls == 1
    assert snapshot.conversion_intent_count == 2
    assert snapshot.conversion_outcome_count == 1
    assert snapshot.report_evidence_pack_request_count == 3
    assert snapshot.certification_ready is False


def test_downstream_realization_readiness_capabilities_preserve_source_authority() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    source_authorities = {
        capability.capability_id: capability.source_authority
        for capability in snapshot.capabilities
    }
    assert source_authorities == {
        "advise-proposal-realization": "lotus-advise",
        "manage-action-realization": "lotus-manage",
        "report-render-archive-realization": "lotus-report",
    }
    assert all(
        capability.supportability_status == "not_certified"
        and capability.supportability_status != "supported"
        and not capability.certification_ready
        for capability in snapshot.capabilities
    )
    capabilities = {capability.capability_id: capability for capability in snapshot.capabilities}
    assert (
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"
        in capabilities["advise-proposal-realization"].evidence_refs
    )
    assert (
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"
        in capabilities["manage-action-realization"].evidence_refs
    )
    assert (
        "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"
        in capabilities["report-render-archive-realization"].evidence_refs
    )


def test_downstream_realization_readiness_contracts_preserve_downstream_authority() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    contracts = {contract.contract_id: contract for contract in snapshot.downstream_contracts}

    assert set(contracts) == {
        "lotus-idea-to-lotus-advise-proposal-intake:v1",
        "lotus-idea-to-lotus-manage-action-intake:v1",
        "lotus-idea-to-lotus-report-evidence-pack-intake:v1",
    }
    assert (
        contracts["lotus-idea-to-lotus-advise-proposal-intake:v1"].source_authority
        == "lotus-advise"
    )
    assert (
        contracts["lotus-idea-to-lotus-manage-action-intake:v1"].source_authority == "lotus-manage"
    )
    report_contract = contracts["lotus-idea-to-lotus-report-evidence-pack-intake:v1"]
    assert report_contract.owner_repository == "lotus-report"
    assert report_contract.target_route == "planned:lotus-report-idea-evidence-pack-intake"
    assert "lotus_report_live_intake_route_proof_missing" in report_contract.blockers
    assert "dedicated_report_idea_evidence_intake_contract_missing" not in (
        report_contract.blockers
    )
    assert (
        "lotus-report/contracts/idea-evidence-intake/"
        "lotus-report-idea-evidence-pack-intake.v1.json" in report_contract.evidence_refs
    )
    assert all(
        contract.route_fit_status == "not_certified"
        and contract.adapter_status == "adapter_foundation_present"
        and not contract.certification_ready
        for contract in snapshot.downstream_contracts
    )


def test_downstream_readiness_adds_report_source_contract_without_clearing_runtime() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_source_contract_proof=_valid_report_intake_route_source_contract_proof(),
        report_intake_route_source_contract_proof_ref="output/report/intake-route-source-contract-proof.json",
    )

    assert "lotus_report_live_intake_route_proof_missing" in snapshot.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in snapshot.blockers
    assert "rendered_output_creation_missing" in snapshot.blockers
    assert "archive_record_creation_missing" in snapshot.blockers
    assert "client_publication_authority_blocked" in snapshot.blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    report_capability = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "report-render-archive-realization"
    )
    assert "report_evidence_pack_live_materialization_proof_missing" in (report_capability.blockers)
    assert (
        "output/report/intake-route-source-contract-proof.json" in report_capability.evidence_refs
    )
    report_contract = next(
        contract
        for contract in snapshot.downstream_contracts
        if contract.contract_id == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    assert report_contract.target_route == "planned:lotus-report-idea-evidence-pack-intake"
    assert report_contract.route_fit_status == "not_certified"
    assert "lotus_report_live_intake_route_proof_missing" in report_contract.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in report_contract.blockers
    assert "output/report/intake-route-source-contract-proof.json" in report_contract.evidence_refs


def test_materialization_source_contract_preserves_runtime_posture_and_adds_evidence() -> None:
    source_contract_ref = "output/report/materialization-source-contract-proof.json"
    baseline = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_materialization_source_contract_proof=(
            _valid_report_materialization_source_contract_proof()
        ),
        report_materialization_source_contract_proof_ref=source_contract_ref,
    )

    assert snapshot.blockers == baseline.blockers
    assert snapshot.readiness_status == baseline.readiness_status
    assert snapshot.supportability_status == baseline.supportability_status
    baseline_capability = next(
        capability
        for capability in baseline.capabilities
        if capability.capability_id == "report-render-archive-realization"
    )
    report_capability = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "report-render-archive-realization"
    )
    assert report_capability.blockers == baseline_capability.blockers
    assert report_capability.readiness_status == baseline_capability.readiness_status
    assert report_capability.supportability_status == baseline_capability.supportability_status
    assert source_contract_ref in report_capability.evidence_refs
    baseline_contract = next(
        contract
        for contract in baseline.downstream_contracts
        if contract.contract_id == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    report_contract = next(
        contract
        for contract in snapshot.downstream_contracts
        if contract.contract_id == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    assert report_contract.target_route == baseline_contract.target_route
    assert report_contract.route_fit_status == baseline_contract.route_fit_status
    assert report_contract.blockers == baseline_contract.blockers
    assert source_contract_ref in report_contract.evidence_refs


def test_route_source_contracts_preserve_live_and_authority_blockers() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        advise_proposal_route_proof=valid_advise_route_source_contract(),
        advise_proposal_route_proof_ref="output/downstream/advise-route-source-contract-proof.json",
        manage_action_route_proof=valid_manage_route_source_contract(),
        manage_action_route_proof_ref="output/downstream/manage-route-source-contract-proof.json",
    )

    assert "advise_live_contract_proof_missing" in snapshot.blockers
    assert "manage_live_contract_proof_missing" in snapshot.blockers
    assert "suitability_policy_authority_remains_lotus_advise" in snapshot.blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in snapshot.blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    capabilities = {capability.capability_id: capability for capability in snapshot.capabilities}
    assert "advise_live_contract_proof_missing" in (
        capabilities["advise-proposal-realization"].blockers
    )
    assert "suitability_policy_authority_remains_lotus_advise" in (
        capabilities["advise-proposal-realization"].blockers
    )
    assert "manage_live_contract_proof_missing" in (
        capabilities["manage-action-realization"].blockers
    )
    assert "rebalance_execution_authority_remains_lotus_manage" in (
        capabilities["manage-action-realization"].blockers
    )
    contracts = {contract.contract_id: contract for contract in snapshot.downstream_contracts}
    advise_contract = contracts["lotus-idea-to-lotus-advise-proposal-intake:v1"]
    manage_contract = contracts["lotus-idea-to-lotus-manage-action-intake:v1"]
    assert advise_contract.target_route == ADVISE_PROPOSAL_ROUTE
    assert manage_contract.target_route == MANAGE_ACTION_ROUTE
    assert "output/downstream/advise-route-source-contract-proof.json" in (
        advise_contract.evidence_refs
    )
    assert "output/downstream/manage-route-source-contract-proof.json" in (
        manage_contract.evidence_refs
    )


class _ProjectionOnlyDownstreamReadinessRepository:
    def __init__(self, summary: DownstreamRealizationReadinessRepositorySummary) -> None:
        self.summary = summary
        self.projection_calls = 0

    def downstream_realization_readiness_summary(
        self,
    ) -> DownstreamRealizationReadinessRepositorySummary:
        self.projection_calls += 1
        return self.summary

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("downstream readiness projection must not call snapshot")


def _valid_report_intake_route_source_contract_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-24T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_intake_route_source_contract",
        "proofScope": "report_intake_route_declaration_and_contract_compatibility",
        "evidenceClass": "source_contract",
        "reportIntakeRouteSourceContractValid": True,
        "aggregateBlockersCleared": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
        "targetRoute": REPORT_INTAKE_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractDeclaresCompatibleRoute": True,
            "reportContractPreservesNonProofBoundaries": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
        "reportRouteServingObserved": False,
        "requestAuthorizationObserved": False,
        "tenantIsolationObserved": False,
        "runtimeExecutionObserved": False,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def _valid_report_materialization_source_contract_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_materialization_source_contract",
        "proofScope": "report_materialization_declaration_and_contract_compatibility",
        "evidenceClass": "source_contract",
        "sourceContractValid": True,
        "aggregateBlockersCleared": REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractDeclaresMaterialization": True,
            "reportContractPreservesNonProofBoundaries": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }
