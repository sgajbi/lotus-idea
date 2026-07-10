from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from app.application.downstream_realization_readiness import (
    build_downstream_realization_readiness_snapshot,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE,
    MANAGE_ACTION_ROUTE,
)
from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
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
from tests.support.downstream_route_contract_fixtures import (
    valid_advise_route_proof,
    valid_manage_route_proof,
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


def test_downstream_realization_readiness_uses_report_route_proof_without_materialization() -> None:
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_proof=_valid_report_intake_route_proof(),
        report_intake_route_proof_ref="output/downstream/report-intake-route-proof.json",
    )

    assert "lotus_report_live_intake_route_proof_missing" not in snapshot.blockers
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
    assert "lotus_report_live_intake_route_proof_missing" not in report_capability.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in (report_capability.blockers)
    assert "output/downstream/report-intake-route-proof.json" in report_capability.evidence_refs
    report_contract = next(
        contract
        for contract in snapshot.downstream_contracts
        if contract.contract_id == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    assert report_contract.target_route == REPORT_INTAKE_ROUTE
    assert report_contract.route_fit_status == "route_foundation_proven_not_certified"
    assert "lotus_report_live_intake_route_proof_missing" not in report_contract.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in report_contract.blockers
    assert "output/downstream/report-intake-route-proof.json" in report_contract.evidence_refs


def test_downstream_realization_readiness_uses_advise_and_manage_route_proofs_without_authority() -> (
    None
):
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        advise_proposal_route_proof=valid_advise_route_proof(),
        advise_proposal_route_proof_ref="output/downstream/advise-proposal-route-proof.json",
        manage_action_route_proof=valid_manage_route_proof(),
        manage_action_route_proof_ref="output/downstream/manage-action-route-proof.json",
    )

    assert "advise_live_contract_proof_missing" not in snapshot.blockers
    assert "manage_live_contract_proof_missing" not in snapshot.blockers
    assert "suitability_policy_authority_remains_lotus_advise" in snapshot.blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in snapshot.blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    capabilities = {capability.capability_id: capability for capability in snapshot.capabilities}
    assert "advise_live_contract_proof_missing" not in (
        capabilities["advise-proposal-realization"].blockers
    )
    assert "suitability_policy_authority_remains_lotus_advise" in (
        capabilities["advise-proposal-realization"].blockers
    )
    assert "manage_live_contract_proof_missing" not in (
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
    assert advise_contract.route_fit_status == "route_foundation_proven_not_certified"
    assert manage_contract.route_fit_status == "route_foundation_proven_not_certified"
    assert "output/downstream/advise-proposal-route-proof.json" in (advise_contract.evidence_refs)
    assert "output/downstream/manage-action-route-proof.json" in manage_contract.evidence_refs


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


def _valid_report_intake_route_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-24T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_intake_route_contract",
        "proofScope": "source_safe_report_intake_route_only",
        "reportIntakeRouteProofValid": True,
        "aggregateBlockersCleared": REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
        "evidenceRefs": (
            "../lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json",
            "../lotus-report/src/app/idea_evidence_intake/models.py",
            "../lotus-report/src/app/idea_evidence_intake/service.py",
            "../lotus-report/src/app/routers/idea_evidence_intake.py",
            "../lotus-report/tests/unit/test_idea_evidence_intake_service.py",
            "../lotus-report/tests/integration/test_idea_evidence_intake_api.py",
            "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
            "GET /api/v1/downstream-realization/readiness",
            "GET /api/v1/implementation-proof/readiness",
        ),
        "targetRoute": REPORT_INTAKE_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractProvesRoute": True,
            "reportContractPreservesNonProofBoundaries": True,
            "reportContractRetainsMaterializationBlockers": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }
