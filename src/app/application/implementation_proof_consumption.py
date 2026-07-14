from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, cast

from app.application.ai_lineage_store_proof import ai_lineage_store_proof_is_valid
from app.application.ai_model_risk_operations.source_contract_proof import (
    ai_model_risk_operations_proof_is_valid,
)
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    ai_workflow_pack_registration_proof_is_valid,
)
from app.application.ai_runtime_proof import (
    ai_workflow_pack_runtime_execution_proof_is_valid,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_ROUTE_BLOCKERS_CLEARED,
    MANAGE_ROUTE_BLOCKERS_CLEARED,
    advise_proposal_route_proof_is_valid,
    manage_action_route_proof_is_valid,
)
from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_BLOCKERS_CLEARED,
    durable_repository_proof_is_valid,
)
from app.application.workbench.discovery_contract_proof import (
    gateway_workbench_discovery_contract_proof_is_valid,
)
from app.application.workbench.contract_proof import (
    gateway_workbench_contract_proof_is_valid,
)
from app.application.implementation_proof_capability_updates import (
    apply_blocker_proof,
    apply_supporting_evidence,
    build_capability_readiness,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
)
from app.application.implementation_proof_opportunity_archetype_proofs import (
    apply_opportunity_archetype_proofs_from_scope,
)
from app.application.mesh_policy_proof import (
    MESH_POLICY_BLOCKERS_CLEARED,
    mesh_policy_proof_is_valid,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    operator_workflows_operations_proof_is_valid,
)
from app.application.outbox.broker.source_contract_proof import (
    outbox_broker_source_contract_proof_is_valid,
)
from app.application.outbox.consumer_contract_proof import (
    outbox_consumer_contract_proof_is_valid,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    outbox_platform_mesh_event_source_contract_proof_is_valid,
)
from app.application.platform_mesh_onboarding_proof import (
    PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED,
    platform_mesh_onboarding_proof_is_valid,
)
from app.application.proof_provenance import aggregate_proof_artifact_is_current
from app.application.report.materialization_source_contract import (
    report_materialization_source_contract_is_valid,
)
from app.application.runtime_trust_telemetry_proof import (
    runtime_trust_telemetry_proof_is_valid,
)
from app.application.source_ingestion_live_proof import (
    source_ingestion_live_proof_can_clear_aggregate_blockers,
)
from app.application.source_ingestion_readiness import SourceIngestionReadinessSnapshot
from app.application.workbench.read_path_source_contract import (
    workbench_read_path_source_contract_proof_is_valid,
)


def apply_available_proofs_from_scope(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    scope: Mapping[str, object],
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    proof_args: dict[str, Any] = {
        name: scope[name]
        for name in _apply_available_proofs.__annotations__
        if name not in {"capabilities", "return"}
    }
    return _apply_available_proofs(capabilities=capabilities, **proof_args)


def _apply_available_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    repository_root: Path,
    durable_repository_proof: Mapping[str, object] | None,
    durable_repository_proof_ref: str | None,
    runtime_trust_telemetry_proof: Mapping[str, object] | None,
    runtime_trust_telemetry_proof_ref: str | None,
    ai_lineage_store_proof: Mapping[str, object] | None,
    ai_lineage_store_proof_ref: str | None,
    ai_model_risk_operations_proof: Mapping[str, object] | None,
    ai_model_risk_operations_proof_ref: str | None,
    operator_workflows_operations_proof: Mapping[str, object] | None,
    operator_workflows_operations_proof_ref: str | None,
    ai_workflow_pack_registration_proof: Mapping[str, object] | None,
    ai_workflow_pack_registration_proof_ref: str | None,
    ai_workflow_pack_runtime_execution_proof: Mapping[str, object] | None,
    ai_workflow_pack_runtime_execution_proof_ref: str | None,
    advise_proposal_route_proof: Mapping[str, object] | None,
    advise_proposal_route_proof_ref: str | None,
    manage_action_route_proof: Mapping[str, object] | None,
    manage_action_route_proof_ref: str | None,
    report_materialization_source_contract_proof: Mapping[str, object] | None,
    report_materialization_source_contract_proof_ref: str | None,
    mesh_policy_proof: Mapping[str, object] | None,
    mesh_policy_proof_ref: str | None,
    outbox_broker_source_contract_proof: Mapping[str, object] | None,
    outbox_broker_source_contract_proof_ref: str | None,
    outbox_consumer_contract_proof: Mapping[str, object] | None,
    outbox_consumer_contract_proof_ref: str | None,
    outbox_platform_mesh_event_source_contract_proof: Mapping[str, object] | None,
    outbox_platform_mesh_event_source_contract_proof_ref: str | None,
    platform_mesh_onboarding_proof: Mapping[str, object] | None,
    platform_mesh_onboarding_proof_ref: str | None,
    workbench_read_path_source_contract_proof: Mapping[str, object] | None,
    workbench_read_path_source_contract_proof_ref: str | None,
    gateway_workbench_contract_proof: Mapping[str, object] | None,
    gateway_workbench_contract_proof_ref: str | None,
    gateway_workbench_discovery_contract_proof: Mapping[str, object] | None,
    gateway_workbench_discovery_contract_proof_ref: str | None,
    source_ingestion_live_proof: Mapping[str, object] | None,
    source_ingestion_live_proof_ref: str | None,
    source_ingestion: SourceIngestionReadinessSnapshot,
    risk_concentration_live_proof: Mapping[str, object] | None,
    risk_concentration_live_proof_ref: str | None,
    high_volatility_live_proof: Mapping[str, object] | None,
    high_volatility_live_proof_ref: str | None,
    risk_drawdown_live_proof: Mapping[str, object] | None,
    risk_drawdown_live_proof_ref: str | None,
    performance_underperformance_live_proof: Mapping[str, object] | None,
    performance_underperformance_live_proof_ref: str | None,
    core_benchmark_assignment_live_proof: Mapping[str, object] | None,
    core_benchmark_assignment_live_proof_ref: str | None,
    core_portfolio_state_live_proof: Mapping[str, object] | None,
    core_portfolio_state_live_proof_ref: str | None,
    bond_maturity_live_proof: Mapping[str, object] | None,
    bond_maturity_live_proof_ref: str | None,
    low_income_core_cashflow_live_proof: Mapping[str, object] | None,
    low_income_core_cashflow_live_proof_ref: str | None,
    manage_mandate_live_proof: Mapping[str, object] | None,
    manage_mandate_live_proof_ref: str | None,
    mandate_restriction_live_proof: Mapping[str, object] | None,
    mandate_restriction_live_proof_ref: str | None,
    mandate_restriction_source_product_proof: Mapping[str, object] | None,
    mandate_restriction_source_product_proof_ref: str | None,
    missing_suitability_live_proof: Mapping[str, object] | None,
    missing_suitability_live_proof_ref: str | None,
    missing_risk_profile_source_product_proof: Mapping[str, object] | None,
    missing_risk_profile_source_product_proof_ref: str | None,
    missing_risk_profile_live_proof: Mapping[str, object] | None,
    missing_risk_profile_live_proof_ref: str | None,
    missing_benchmark_live_proof: Mapping[str, object] | None,
    missing_benchmark_live_proof_ref: str | None,
    missing_benchmark_performance_readiness_proof: Mapping[str, object] | None,
    missing_benchmark_performance_readiness_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    capabilities = _apply_storage_and_runtime_proofs(
        capabilities=capabilities,
        evaluated_at_utc=evaluated_at_utc,
        durable_repository_proof=durable_repository_proof,
        durable_repository_proof_ref=durable_repository_proof_ref,
        runtime_trust_telemetry_proof=runtime_trust_telemetry_proof,
        runtime_trust_telemetry_proof_ref=runtime_trust_telemetry_proof_ref,
    )
    capabilities = _apply_ai_proofs(
        capabilities=capabilities,
        evaluated_at_utc=evaluated_at_utc,
        ai_lineage_store_proof=ai_lineage_store_proof,
        ai_lineage_store_proof_ref=ai_lineage_store_proof_ref,
        ai_model_risk_operations_proof=ai_model_risk_operations_proof,
        ai_model_risk_operations_proof_ref=ai_model_risk_operations_proof_ref,
        ai_workflow_pack_registration_proof=ai_workflow_pack_registration_proof,
        ai_workflow_pack_registration_proof_ref=ai_workflow_pack_registration_proof_ref,
        ai_workflow_pack_runtime_execution_proof=ai_workflow_pack_runtime_execution_proof,
        ai_workflow_pack_runtime_execution_proof_ref=ai_workflow_pack_runtime_execution_proof_ref,
    )
    capabilities = _apply_downstream_proofs(
        capabilities=capabilities,
        evaluated_at_utc=evaluated_at_utc,
        advise_proposal_route_proof=advise_proposal_route_proof,
        advise_proposal_route_proof_ref=advise_proposal_route_proof_ref,
        manage_action_route_proof=manage_action_route_proof,
        manage_action_route_proof_ref=manage_action_route_proof_ref,
        report_materialization_source_contract_proof=report_materialization_source_contract_proof,
        report_materialization_source_contract_proof_ref=(
            report_materialization_source_contract_proof_ref
        ),
    )
    capabilities = _apply_platform_surface_and_operator_proofs(
        capabilities=capabilities,
        scope=locals(),
    )
    return _apply_opportunity_archetype_proofs(capabilities=capabilities, scope=locals())


def _apply_opportunity_archetype_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    scope: Mapping[str, object],
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    return apply_opportunity_archetype_proofs_from_scope(
        capabilities=capabilities,
        source_ingestion_live_proof_current=source_ingestion_live_proof_can_clear_aggregate_blockers(
            cast(Mapping[str, object] | None, scope["source_ingestion_live_proof"]),
            evaluated_at_utc=cast(datetime, scope["evaluated_at_utc"]),
            proof_ref=cast(str | None, scope["source_ingestion_live_proof_ref"]),
            repository_root=cast(Path, scope["repository_root"]),
        ),
        source_ingestion_live_proof_ref=cast(str | None, scope["source_ingestion_live_proof_ref"]),
        evaluated_at_utc=cast(datetime, scope["evaluated_at_utc"]),
        scope=scope,
    )


def _apply_platform_surface_and_operator_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    scope: Mapping[str, object],
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    proof_args: dict[str, Any] = {
        name: scope[name]
        for name in _apply_platform_and_surface_proofs.__annotations__
        if name not in {"capabilities", "return"}
    }
    return _apply_platform_and_surface_proofs(capabilities=capabilities, **proof_args)


def _apply_storage_and_runtime_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    durable_repository_proof: Mapping[str, object] | None,
    durable_repository_proof_ref: str | None,
    runtime_trust_telemetry_proof: Mapping[str, object] | None,
    runtime_trust_telemetry_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if _proof_can_clear_blockers(
        durable_repository_proof,
        durable_repository_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=durable_repository_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_durable_repository_proof(capability, durable_repository_proof_ref)
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        runtime_trust_telemetry_proof,
        runtime_trust_telemetry_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=runtime_trust_telemetry_proof_is_valid,
    ):
        assert runtime_trust_telemetry_proof is not None
        capabilities = tuple(
            _apply_runtime_trust_telemetry_proof(
                capability,
                runtime_trust_telemetry_proof,
                runtime_trust_telemetry_proof_ref,
            )
            for capability in capabilities
        )
    return capabilities


def _apply_ai_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    ai_lineage_store_proof: Mapping[str, object] | None,
    ai_lineage_store_proof_ref: str | None,
    ai_model_risk_operations_proof: Mapping[str, object] | None,
    ai_model_risk_operations_proof_ref: str | None,
    ai_workflow_pack_registration_proof: Mapping[str, object] | None,
    ai_workflow_pack_registration_proof_ref: str | None,
    ai_workflow_pack_runtime_execution_proof: Mapping[str, object] | None,
    ai_workflow_pack_runtime_execution_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if _proof_can_clear_blockers(
        ai_lineage_store_proof,
        ai_lineage_store_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=ai_lineage_store_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_ai_lineage_store_proof(capability, ai_lineage_store_proof_ref)
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        ai_model_risk_operations_proof,
        ai_model_risk_operations_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=ai_model_risk_operations_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_ai_model_risk_operations_proof(capability, ai_model_risk_operations_proof_ref)
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        ai_workflow_pack_registration_proof,
        ai_workflow_pack_registration_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=ai_workflow_pack_registration_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_ai_workflow_pack_registration_proof(
                capability,
                ai_workflow_pack_registration_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        ai_workflow_pack_runtime_execution_proof,
        ai_workflow_pack_runtime_execution_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=ai_workflow_pack_runtime_execution_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_ai_workflow_pack_runtime_execution_proof(
                capability,
                ai_workflow_pack_runtime_execution_proof_ref,
            )
            for capability in capabilities
        )
    return capabilities


def _apply_downstream_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    advise_proposal_route_proof: Mapping[str, object] | None,
    advise_proposal_route_proof_ref: str | None,
    manage_action_route_proof: Mapping[str, object] | None,
    manage_action_route_proof_ref: str | None,
    report_materialization_source_contract_proof: Mapping[str, object] | None,
    report_materialization_source_contract_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if _proof_can_clear_blockers(
        advise_proposal_route_proof,
        advise_proposal_route_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=advise_proposal_route_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_downstream_route_contract_proof(
                capability,
                capability_id="downstream-realization",
                blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=advise_proposal_route_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        manage_action_route_proof,
        manage_action_route_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=manage_action_route_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_downstream_route_contract_proof(
                capability,
                capability_id="downstream-realization",
                blockers_cleared=MANAGE_ROUTE_BLOCKERS_CLEARED,
                proof_ref=manage_action_route_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        report_materialization_source_contract_proof,
        report_materialization_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=report_materialization_source_contract_is_valid,
    ):
        capabilities = tuple(
            _apply_report_materialization_source_contract(
                capability,
                report_materialization_source_contract_proof_ref,
            )
            for capability in capabilities
        )
    return capabilities


def _apply_platform_and_surface_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    mesh_policy_proof: Mapping[str, object] | None,
    mesh_policy_proof_ref: str | None,
    outbox_broker_source_contract_proof: Mapping[str, object] | None,
    outbox_broker_source_contract_proof_ref: str | None,
    outbox_consumer_contract_proof: Mapping[str, object] | None,
    outbox_consumer_contract_proof_ref: str | None,
    outbox_platform_mesh_event_source_contract_proof: Mapping[str, object] | None,
    outbox_platform_mesh_event_source_contract_proof_ref: str | None,
    platform_mesh_onboarding_proof: Mapping[str, object] | None,
    platform_mesh_onboarding_proof_ref: str | None,
    workbench_read_path_source_contract_proof: Mapping[str, object] | None,
    workbench_read_path_source_contract_proof_ref: str | None,
    gateway_workbench_contract_proof: Mapping[str, object] | None,
    gateway_workbench_contract_proof_ref: str | None,
    gateway_workbench_discovery_contract_proof: Mapping[str, object] | None,
    gateway_workbench_discovery_contract_proof_ref: str | None,
    operator_workflows_operations_proof: Mapping[str, object] | None,
    operator_workflows_operations_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if _proof_can_clear_blockers(
        mesh_policy_proof,
        mesh_policy_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=mesh_policy_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_mesh_policy_proof(capability, mesh_policy_proof_ref)
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        outbox_broker_source_contract_proof,
        outbox_broker_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_broker_source_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_outbox_broker_source_contract(
                capability,
                outbox_broker_source_contract_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        outbox_consumer_contract_proof,
        outbox_consumer_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_consumer_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_outbox_consumer_contract_proof(
                capability,
                outbox_consumer_contract_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        outbox_platform_mesh_event_source_contract_proof,
        outbox_platform_mesh_event_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=outbox_platform_mesh_event_source_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_outbox_platform_mesh_event_source_contract(
                capability,
                outbox_platform_mesh_event_source_contract_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_can_clear_blockers(
        platform_mesh_onboarding_proof,
        platform_mesh_onboarding_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=platform_mesh_onboarding_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_platform_mesh_onboarding_proof(capability, platform_mesh_onboarding_proof_ref)
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        workbench_read_path_source_contract_proof,
        workbench_read_path_source_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=workbench_read_path_source_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_workbench_read_path_source_contract(
                capability,
                workbench_read_path_source_contract_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        gateway_workbench_contract_proof,
        gateway_workbench_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=gateway_workbench_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_gateway_workbench_contract_proof(
                capability,
                gateway_workbench_contract_proof_ref,
            )
            for capability in capabilities
        )
    if _proof_is_valid_and_current(
        gateway_workbench_discovery_contract_proof,
        gateway_workbench_discovery_contract_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=gateway_workbench_discovery_contract_proof_is_valid,
    ):
        capabilities = tuple(
            _apply_gateway_workbench_discovery_contract_proof(
                capability,
                gateway_workbench_discovery_contract_proof_ref,
            )
            for capability in capabilities
        )
    capabilities = _apply_operator_workflows_operations_proof_if_valid(
        capabilities=capabilities,
        evaluated_at_utc=evaluated_at_utc,
        operator_workflows_operations_proof=operator_workflows_operations_proof,
        operator_workflows_operations_proof_ref=operator_workflows_operations_proof_ref,
    )
    return capabilities


def _apply_operator_workflows_operations_proof_if_valid(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    evaluated_at_utc: datetime,
    operator_workflows_operations_proof: Mapping[str, object] | None,
    operator_workflows_operations_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if not _proof_is_valid_and_current(
        operator_workflows_operations_proof,
        operator_workflows_operations_proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=operator_workflows_operations_proof_is_valid,
    ):
        return capabilities
    return tuple(
        _apply_operator_workflows_operations_source_contract(
            capability, operator_workflows_operations_proof_ref
        )
        for capability in capabilities
    )


def _apply_operator_workflows_operations_source_contract(
    capability: ImplementationProofCapabilityReadiness,
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "operator-workflows-operations":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _proof_can_clear_blockers(
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
    *,
    evaluated_at_utc: datetime,
    proof_is_valid: Any,
) -> bool:
    return _proof_is_valid_and_current(
        proof,
        proof_ref,
        evaluated_at_utc=evaluated_at_utc,
        proof_is_valid=proof_is_valid,
    )


def _proof_is_valid_and_current(
    proof: Mapping[str, object] | None,
    proof_ref: str | None,
    *,
    evaluated_at_utc: datetime,
    proof_is_valid: Any,
) -> bool:
    return bool(
        proof
        and proof_is_valid(proof)
        and aggregate_proof_artifact_is_current(
            proof,
            evaluated_at_utc=evaluated_at_utc,
            proof_ref=proof_ref,
        )
    )


def _apply_downstream_route_contract_proof(
    capability: ImplementationProofCapabilityReadiness,
    *,
    capability_id: str,
    blockers_cleared: tuple[str, ...],
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=(capability_id,),
        blockers_cleared=blockers_cleared,
        proof_ref=proof_ref,
    )


def _apply_report_materialization_source_contract(
    capability: ImplementationProofCapabilityReadiness,
    report_materialization_source_contract_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_supporting_evidence(
        capability,
        capability_ids=("downstream-realization",),
        evidence_ref=report_materialization_source_contract_ref,
    )


def _apply_mesh_policy_proof(
    capability: ImplementationProofCapabilityReadiness,
    mesh_policy_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("data-mesh-certification", "operator-workflows-operations"),
        blockers_cleared=MESH_POLICY_BLOCKERS_CLEARED,
        proof_ref=mesh_policy_proof_ref,
    )


def _apply_durable_repository_proof(
    capability: ImplementationProofCapabilityReadiness,
    durable_repository_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if not set(capability.blockers).intersection(DURABLE_REPOSITORY_BLOCKERS_CLEARED):
        return capability
    evidence_refs = capability.evidence_refs
    if durable_repository_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, durable_repository_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker not in DURABLE_REPOSITORY_BLOCKERS_CLEARED
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_runtime_trust_telemetry_proof(
    capability: ImplementationProofCapabilityReadiness,
    runtime_trust_telemetry_proof: Mapping[str, object],
    runtime_trust_telemetry_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    blockers_cleared_value = runtime_trust_telemetry_proof.get("aggregateBlockersCleared", ())
    blockers_cleared = (
        blockers_cleared_value if isinstance(blockers_cleared_value, (list, tuple)) else ()
    )
    return apply_blocker_proof(
        capability,
        blockers_cleared=tuple(str(blocker) for blocker in blockers_cleared),
        proof_ref=runtime_trust_telemetry_proof_ref,
    )


def _apply_workbench_read_path_source_contract(
    capability: ImplementationProofCapabilityReadiness,
    workbench_read_path_source_contract_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    evidence_refs = capability.evidence_refs
    if workbench_read_path_source_contract_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, workbench_read_path_source_contract_proof_ref))
        )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_gateway_workbench_contract_proof(
    capability: ImplementationProofCapabilityReadiness,
    gateway_workbench_contract_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in (
        "source-ingestion",
        "outbox-delivery",
        "operator-workflows-operations",
    ):
        return capability
    evidence_refs = capability.evidence_refs
    if gateway_workbench_contract_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, gateway_workbench_contract_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_gateway_workbench_discovery_contract_proof(
    capability: ImplementationProofCapabilityReadiness,
    gateway_workbench_discovery_contract_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in (
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
    ):
        return capability
    evidence_refs = capability.evidence_refs
    if gateway_workbench_discovery_contract_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, gateway_workbench_discovery_contract_proof_ref))
        )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_lineage_store_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_lineage_store_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "certified_ai_lineage_store_missing" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_lineage_store_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, ai_lineage_store_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "certified_ai_lineage_store_missing"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_model_risk_operations_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_model_risk_operations_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    evidence_refs = capability.evidence_refs
    if ai_model_risk_operations_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, ai_model_risk_operations_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_workflow_pack_registration_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_workflow_pack_registration_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "workflow_pack_runtime_contract_not_certified" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_workflow_pack_registration_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, ai_workflow_pack_registration_proof_ref))
        )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_workflow_pack_runtime_execution_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_workflow_pack_runtime_execution_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "lotus_ai_runtime_execution_missing" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_workflow_pack_runtime_execution_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, ai_workflow_pack_runtime_execution_proof_ref))
        )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            dict.fromkeys(
                (
                    *(
                        blocker
                        for blocker in capability.blockers
                        if blocker != "lotus_ai_runtime_execution_missing"
                    ),
                    "lotus_ai_live_provider_execution_missing",
                )
            )
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_outbox_broker_source_contract(
    capability: ImplementationProofCapabilityReadiness,
    outbox_broker_source_contract_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in {"outbox-delivery", "operator-workflows-operations"}:
        return capability
    evidence_refs = capability.evidence_refs
    if outbox_broker_source_contract_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, outbox_broker_source_contract_proof_ref))
        )
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_outbox_consumer_contract_proof(
    capability: ImplementationProofCapabilityReadiness,
    outbox_consumer_contract_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "outbox-delivery":
        return capability
    evidence_refs = capability.evidence_refs
    if outbox_consumer_contract_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, outbox_consumer_contract_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_outbox_platform_mesh_event_source_contract(
    capability: ImplementationProofCapabilityReadiness,
    proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "outbox-delivery":
        return capability
    evidence_refs = capability.evidence_refs
    if proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=capability.blockers,
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_platform_mesh_onboarding_proof(
    capability: ImplementationProofCapabilityReadiness,
    platform_mesh_onboarding_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in {
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
    }:
        return capability
    blockers_to_clear = set(PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED)
    if not blockers_to_clear.intersection(capability.blockers):
        return capability
    evidence_refs = capability.evidence_refs
    if platform_mesh_onboarding_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, platform_mesh_onboarding_proof_ref)))
    return build_capability_readiness(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )
