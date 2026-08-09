# ruff: noqa: E402
from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)
from app.application.implementation_proof_readiness import (
    ImplementationProofReadinessProofInputs,
)
from scripts.implementation_proof_readiness_outbox_inputs import (
    outbox_proof_artifact_inputs,
)


@dataclass(frozen=True)
class ProofArtifactInput:
    payload: dict[str, Any] | None
    proof_ref: str | None


class ProofArtifactInputReader(Protocol):
    def __call__(
        self,
        path_value: str | None,
        *,
        artifact_name: str,
        ref_name: str,
    ) -> ProofArtifactInput: ...


class SourceSafeArtifactRef(Protocol):
    def __call__(
        self,
        path: Path | None,
        *,
        artifact_name: str,
    ) -> str | None: ...


@dataclass(frozen=True)
class ProofArtifactBinding:
    readiness_field: str
    args_attribute: str
    artifact_name: str
    ref_name: str


_FOUNDATION_PROOF_ARTIFACTS: tuple[ProofArtifactBinding, ...] = (
    ProofArtifactBinding(
        "durable_repository_proof",
        "durable_repository_proof",
        "durable repository proof",
        "durable repository proof artifact",
    ),
    ProofArtifactBinding(
        "runtime_trust_telemetry_test_execution",
        "runtime_trust_telemetry_test_execution",
        "runtime trust telemetry test execution",
        "runtime trust telemetry test execution artifact",
    ),
    ProofArtifactBinding(
        "ai_lineage_store_proof",
        "ai_lineage_store_proof",
        "AI lineage store proof",
        "AI lineage store proof artifact",
    ),
    ProofArtifactBinding(
        "ai_model_risk_operations_proof",
        "ai_model_risk_operations_proof",
        "AI model-risk operations proof",
        "AI model-risk operations proof artifact",
    ),
    ProofArtifactBinding(
        "operator_workflows_operations_proof",
        "operator_workflows_operations_proof",
        "operator workflows operations proof",
        "operator workflows operations proof artifact",
    ),
    ProofArtifactBinding(
        "ai_workflow_pack_registration_proof",
        "ai_workflow_pack_registration_proof",
        "AI workflow-pack registration source-contract proof",
        "AI workflow-pack registration source-contract proof artifact",
    ),
    ProofArtifactBinding(
        "ai_workflow_pack_runtime_execution_proof",
        "ai_workflow_pack_runtime_execution_proof",
        "AI workflow-pack runtime execution proof",
        "AI workflow-pack runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "advise_proposal_route_proof",
        "advise_proposal_route_source_contract_proof",
        "Advise proposal route source contract",
        "Advise proposal route source-contract artifact",
    ),
    ProofArtifactBinding(
        "advise_intake_runtime_execution_proof",
        "advise_intake_runtime_execution_proof",
        "Advise idea-intake runtime execution proof",
        "Advise idea-intake runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "manage_action_route_proof",
        "manage_action_route_source_contract_proof",
        "Manage action route source contract",
        "Manage action route source-contract artifact",
    ),
    ProofArtifactBinding(
        "manage_intake_runtime_execution_proof",
        "manage_intake_runtime_execution_proof",
        "Manage idea action-intake runtime execution proof",
        "Manage idea action-intake runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "report_intake_route_source_contract_proof",
        "report_intake_route_source_contract_proof",
        "Report intake-route source-contract proof",
        "Report intake-route source-contract proof artifact",
    ),
    ProofArtifactBinding(
        "report_intake_runtime_execution_proof",
        "report_intake_runtime_execution_proof",
        "Report intake runtime execution proof",
        "Report intake runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "report_materialization_source_contract_proof",
        "report_materialization_source_contract_proof",
        "report materialization source contract",
        "report materialization source contract artifact",
    ),
    ProofArtifactBinding(
        "report_materialization_runtime_execution_proof",
        "report_materialization_runtime_execution_proof",
        "Report materialization runtime execution proof",
        "Report materialization runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "mesh_policy_source_contract_proof",
        "mesh_policy_source_contract_proof",
        "mesh policy source contract",
        "mesh policy source-contract artifact",
    ),
    ProofArtifactBinding(
        "workbench_read_path_source_contract_proof",
        "workbench_read_path_source_contract_proof",
        "Workbench read-path source-contract proof",
        "Workbench read-path source-contract proof artifact",
    ),
    ProofArtifactBinding(
        "gateway_workbench_contract_proof",
        "gateway_workbench_contract_proof",
        "Gateway/Workbench contract proof",
        "Gateway/Workbench contract proof artifact",
    ),
    ProofArtifactBinding(
        "gateway_workbench_discovery_contract_proof",
        "gateway_workbench_discovery_contract_proof",
        "Gateway/Workbench discovery contract proof",
        "Gateway/Workbench discovery contract proof artifact",
    ),
    ProofArtifactBinding(
        "gateway_workbench_runtime_execution_proof",
        "gateway_workbench_runtime_execution_proof",
        "Gateway/Workbench runtime execution proof",
        "Gateway/Workbench runtime execution proof artifact",
    ),
    ProofArtifactBinding(
        "platform_catalog_source_contract_proof",
        "platform_catalog_source_contract_proof",
        "platform catalog source contract",
        "platform catalog source contract artifact",
    ),
    ProofArtifactBinding(
        "opportunity_archetype_evidence_pack_proof",
        "opportunity_archetype_evidence_pack",
        "canonical opportunity archetype evidence pack",
        "canonical opportunity archetype evidence-pack artifact",
    ),
)

_OPPORTUNITY_ARCHETYPE_PROOF_ARTIFACTS: tuple[ProofArtifactBinding, ...] = (
    ProofArtifactBinding(
        "risk_concentration_live_proof",
        "risk_concentration_live_proof",
        "Risk concentration runtime execution",
        "Risk concentration runtime execution artifact",
    ),
    ProofArtifactBinding(
        "high_volatility_live_proof",
        "high_volatility_live_proof",
        "High volatility live proof",
        "High volatility live proof artifact",
    ),
    ProofArtifactBinding(
        "risk_drawdown_live_proof",
        "risk_drawdown_live_proof",
        "Risk drawdown live proof",
        "Risk drawdown live proof artifact",
    ),
    ProofArtifactBinding(
        "performance_underperformance_live_proof",
        "performance_underperformance_live_proof",
        "Performance underperformance live proof",
        "Performance underperformance live proof artifact",
    ),
    ProofArtifactBinding(
        "core_benchmark_assignment_live_proof",
        "core_benchmark_assignment_live_proof",
        "Core benchmark assignment live proof",
        "Core benchmark assignment live proof artifact",
    ),
    ProofArtifactBinding(
        "core_portfolio_state_live_proof",
        "core_portfolio_state_live_proof",
        "Core portfolio-state runtime evidence",
        "Core portfolio-state runtime evidence artifact",
    ),
    ProofArtifactBinding(
        "bond_maturity_live_proof",
        "bond_maturity_live_proof",
        "Bond maturity live proof",
        "Bond maturity live proof artifact",
    ),
    ProofArtifactBinding(
        "low_income_core_cashflow_live_proof",
        "low_income_core_cashflow_live_proof",
        "Low-income Core cashflow live proof",
        "Low-income Core cashflow live proof artifact",
    ),
    ProofArtifactBinding(
        "manage_mandate_live_proof",
        "manage_mandate_live_proof",
        "Manage mandate live proof",
        "Manage mandate live proof artifact",
    ),
    ProofArtifactBinding(
        "mandate_restriction_live_proof",
        "mandate_restriction_live_proof",
        "Mandate/restriction live proof",
        "Mandate/restriction live proof artifact",
    ),
    ProofArtifactBinding(
        "mandate_restriction_source_product_proof",
        "mandate_restriction_source_product_proof",
        "Mandate/restriction source-product proof",
        "Mandate/restriction source-product proof artifact",
    ),
    ProofArtifactBinding(
        "missing_suitability_live_proof",
        "missing_suitability_live_proof",
        "Missing suitability live proof",
        "Missing suitability live proof artifact",
    ),
    ProofArtifactBinding(
        "missing_risk_profile_live_proof",
        "missing_risk_profile_live_proof",
        "Missing risk-profile live proof",
        "Missing risk-profile live proof artifact",
    ),
    ProofArtifactBinding(
        "missing_risk_profile_source_product_proof",
        "missing_risk_profile_source_product_proof",
        "Missing risk-profile source-product proof",
        "Missing risk-profile source-product proof artifact",
    ),
    ProofArtifactBinding(
        "missing_benchmark_live_proof",
        "missing_benchmark_live_proof",
        "Missing benchmark live proof",
        "Missing benchmark live proof artifact",
    ),
    ProofArtifactBinding(
        "missing_benchmark_performance_readiness_proof",
        "missing_benchmark_performance_readiness_proof",
        "Missing benchmark Performance readiness proof",
        "Missing benchmark Performance readiness proof artifact",
    ),
)


def build_proof_inputs(
    args: argparse.Namespace,
    *,
    proof_artifact_input: ProofArtifactInputReader,
    source_safe_artifact_ref: SourceSafeArtifactRef,
    resolve_optional_path: Callable[[str | None], Path | None],
) -> ImplementationProofReadinessProofInputs:
    source_ingestion_runtime_execution = proof_artifact_input(
        args.source_ingestion_runtime_execution,
        artifact_name="source ingestion runtime execution",
        ref_name="source ingestion runtime execution artifact",
    )
    return ImplementationProofReadinessProofInputs(
        source_ingestion_runtime_execution=source_ingestion_runtime_execution.payload,
        source_ingestion_runtime_execution_ref=source_ingestion_runtime_execution.proof_ref,
        source_ingestion_scheduled_worker_source_contract_ref=source_safe_artifact_ref(
            resolve_optional_path(args.source_ingestion_scheduled_worker_source_contract),
            artifact_name="source ingestion scheduled-worker source-contract artifact",
        ),
        source_ingestion_scheduled_worker_deployment_evidence_ref=source_safe_artifact_ref(
            resolve_optional_path(args.source_ingestion_scheduled_worker_deployment_evidence),
            artifact_name="source ingestion scheduled-worker deployment-evidence artifact",
        ),
        **_proof_artifact_payload_fields(_proof_artifact_inputs(args, proof_artifact_input)),
    )


def _proof_artifact_inputs(
    args: argparse.Namespace,
    proof_artifact_input: ProofArtifactInputReader,
) -> dict[str, ProofArtifactInput]:
    return (
        _read_proof_artifact_bindings(args, _FOUNDATION_PROOF_ARTIFACTS, proof_artifact_input)
        | outbox_proof_artifact_inputs(args, proof_artifact_input)
        | _read_proof_artifact_bindings(
            args,
            _OPPORTUNITY_ARCHETYPE_PROOF_ARTIFACTS,
            proof_artifact_input,
        )
    )


def _read_proof_artifact_bindings(
    args: argparse.Namespace,
    bindings: tuple[ProofArtifactBinding, ...],
    proof_artifact_input: ProofArtifactInputReader,
) -> dict[str, ProofArtifactInput]:
    return {
        binding.readiness_field: proof_artifact_input(
            getattr(args, binding.args_attribute),
            artifact_name=binding.artifact_name,
            ref_name=binding.ref_name,
        )
        for binding in bindings
    }


def _proof_artifact_payload_fields(
    proof_artifacts: dict[str, ProofArtifactInput],
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for readiness_field, artifact in proof_artifacts.items():
        fields[readiness_field] = artifact.payload
        fields[f"{readiness_field}_ref"] = artifact.proof_ref
    return fields
