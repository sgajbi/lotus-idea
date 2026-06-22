from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from app.application.downstream_realization_readiness import (
    build_downstream_realization_readiness_snapshot,
)
from app.domain import IdeaRepositorySnapshot, InMemoryIdeaRepository


@dataclass(frozen=True)
class _WorkflowRecord:
    conversion_intents: tuple[object, ...] = ()
    conversion_outcomes: tuple[object, ...] = ()
    report_evidence_packs: tuple[object, ...] = ()


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
    assert "report_evidence_pack_live_materialization_proof_missing" in snapshot.blockers
    assert "dedicated_report_idea_evidence_intake_contract_missing" in snapshot.blockers
    assert set(snapshot.source_of_truth) == {
        "conversion_workflow",
        "report_evidence_workflow",
        "downstream_realization_orchestration",
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
                        conversion_outcomes=(object(),),
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
    assert "dedicated_report_idea_evidence_intake_contract_missing" in (report_contract.blockers)
    assert all(
        contract.route_fit_status == "not_certified"
        and contract.adapter_status == "adapter_foundation_present"
        and not contract.certification_ready
        for contract in snapshot.downstream_contracts
    )
