from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_model_risk_operations.source_contract_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
)
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.bond_maturity_runtime_evidence import BOND_MATURITY_RUNTIME_EXECUTION_ENV
from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.workbench.runtime_execution import (
    GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV,
)
from app.application.low_income_cashflow_runtime_evidence import (
    LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.broker.runtime_execution import (
    OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.report.intake_route_source_contract import (
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.report.materialization_runtime_execution import (
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
)
from app.application.runtime_trust_telemetry.test_execution_contract import (
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.application.source_ingestion_runtime_evidence import (
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
)
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)
from app.runtime.proof_artifact_files import read_optional_json_object


@dataclass(frozen=True)
class ConfiguredImplementationProofArtifacts:
    source_ingestion_runtime_execution: dict[str, Any] | None
    source_ingestion_runtime_execution_ref: str | None
    source_ingestion_scheduled_worker_source_contract_ref: str | None
    source_ingestion_scheduled_worker_deployment_evidence_ref: str | None
    durable_repository_proof: dict[str, Any] | None
    durable_repository_proof_ref: str | None
    runtime_trust_telemetry_test_execution: dict[str, Any] | None
    runtime_trust_telemetry_test_execution_ref: str | None
    ai_lineage_store_proof: dict[str, Any] | None
    ai_lineage_store_proof_ref: str | None
    ai_model_risk_operations_proof: dict[str, Any] | None
    ai_model_risk_operations_proof_ref: str | None
    operator_workflows_operations_proof: dict[str, Any] | None
    operator_workflows_operations_proof_ref: str | None
    ai_workflow_pack_registration_proof: dict[str, Any] | None
    ai_workflow_pack_registration_proof_ref: str | None
    ai_workflow_pack_runtime_execution_proof: dict[str, Any] | None
    ai_workflow_pack_runtime_execution_proof_ref: str | None
    advise_intake_runtime_execution_proof: dict[str, Any] | None
    advise_intake_runtime_execution_proof_ref: str | None
    manage_intake_runtime_execution_proof: dict[str, Any] | None
    manage_intake_runtime_execution_proof_ref: str | None
    outbox_broker_source_contract_proof: dict[str, Any] | None
    outbox_broker_source_contract_proof_ref: str | None
    outbox_broker_runtime_execution_proof: dict[str, Any] | None
    outbox_broker_runtime_execution_proof_ref: str | None
    outbox_platform_mesh_event_source_contract_proof: dict[str, Any] | None
    outbox_platform_mesh_event_source_contract_proof_ref: str | None
    report_intake_route_source_contract_proof: dict[str, Any] | None
    report_intake_route_source_contract_proof_ref: str | None
    report_materialization_runtime_execution_proof: dict[str, Any] | None
    report_materialization_runtime_execution_proof_ref: str | None
    platform_catalog_source_contract: dict[str, Any] | None
    platform_catalog_source_contract_ref: str | None
    workbench_read_path_source_contract_proof: dict[str, Any] | None
    workbench_read_path_source_contract_proof_ref: str | None
    gateway_workbench_contract_proof: dict[str, Any] | None
    gateway_workbench_contract_proof_ref: str | None
    gateway_workbench_discovery_contract_proof: dict[str, Any] | None
    gateway_workbench_discovery_contract_proof_ref: str | None
    gateway_workbench_runtime_execution_proof: dict[str, Any] | None
    gateway_workbench_runtime_execution_proof_ref: str | None
    bond_maturity_live_proof: dict[str, Any] | None
    bond_maturity_live_proof_ref: str | None
    low_income_core_cashflow_live_proof: dict[str, Any] | None
    low_income_core_cashflow_live_proof_ref: str | None


@dataclass(frozen=True)
class ConfiguredRefOnlyProofArtifact:
    env_name: str
    ref_field: str
    artifact_name: str


@dataclass(frozen=True)
class ConfiguredJsonProofArtifact:
    env_name: str
    proof_field: str
    ref_field: str
    artifact_name: str


_REF_ONLY_PROOF_ARTIFACTS: tuple[ConfiguredRefOnlyProofArtifact, ...] = (
    ConfiguredRefOnlyProofArtifact(
        env_name=SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
        ref_field="source_ingestion_scheduled_worker_source_contract_ref",
        artifact_name="source ingestion scheduled-worker source contract",
    ),
    ConfiguredRefOnlyProofArtifact(
        env_name=SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
        ref_field="source_ingestion_scheduled_worker_deployment_evidence_ref",
        artifact_name="source ingestion scheduled-worker deployment evidence",
    ),
)

_JSON_PROOF_ARTIFACTS: tuple[ConfiguredJsonProofArtifact, ...] = (
    ConfiguredJsonProofArtifact(
        env_name=SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
        proof_field="source_ingestion_runtime_execution",
        ref_field="source_ingestion_runtime_execution_ref",
        artifact_name="source ingestion runtime execution",
    ),
    ConfiguredJsonProofArtifact(
        env_name=DURABLE_REPOSITORY_PROOF_ENV,
        proof_field="durable_repository_proof",
        ref_field="durable_repository_proof_ref",
        artifact_name="durable repository proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
        proof_field="runtime_trust_telemetry_test_execution",
        ref_field="runtime_trust_telemetry_test_execution_ref",
        artifact_name="runtime trust telemetry test execution",
    ),
    ConfiguredJsonProofArtifact(
        env_name=AI_LINEAGE_STORE_PROOF_ENV,
        proof_field="ai_lineage_store_proof",
        ref_field="ai_lineage_store_proof_ref",
        artifact_name="AI lineage store proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
        proof_field="ai_model_risk_operations_proof",
        ref_field="ai_model_risk_operations_proof_ref",
        artifact_name="AI model-risk operations proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
        proof_field="operator_workflows_operations_proof",
        ref_field="operator_workflows_operations_proof_ref",
        artifact_name="operator workflows operations proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        proof_field="ai_workflow_pack_registration_proof",
        ref_field="ai_workflow_pack_registration_proof_ref",
        artifact_name="AI workflow-pack registration source-contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
        proof_field="ai_workflow_pack_runtime_execution_proof",
        ref_field="ai_workflow_pack_runtime_execution_proof_ref",
        artifact_name="AI workflow-pack runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
        proof_field="advise_intake_runtime_execution_proof",
        ref_field="advise_intake_runtime_execution_proof_ref",
        artifact_name="Advise idea-intake runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
        proof_field="manage_intake_runtime_execution_proof",
        ref_field="manage_intake_runtime_execution_proof_ref",
        artifact_name="Manage idea action-intake runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
        proof_field="outbox_broker_source_contract_proof",
        ref_field="outbox_broker_source_contract_proof_ref",
        artifact_name="outbox broker source-contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
        proof_field="outbox_broker_runtime_execution_proof",
        ref_field="outbox_broker_runtime_execution_proof_ref",
        artifact_name="outbox broker runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
        proof_field="outbox_platform_mesh_event_source_contract_proof",
        ref_field="outbox_platform_mesh_event_source_contract_proof_ref",
        artifact_name="outbox platform mesh event source-contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
        proof_field="report_intake_route_source_contract_proof",
        ref_field="report_intake_route_source_contract_proof_ref",
        artifact_name="Report intake-route source-contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
        proof_field="report_materialization_runtime_execution_proof",
        ref_field="report_materialization_runtime_execution_proof_ref",
        artifact_name="Report materialization runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
        proof_field="platform_catalog_source_contract",
        ref_field="platform_catalog_source_contract_ref",
        artifact_name="platform catalog source contract",
    ),
    ConfiguredJsonProofArtifact(
        env_name=WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
        proof_field="workbench_read_path_source_contract_proof",
        ref_field="workbench_read_path_source_contract_proof_ref",
        artifact_name="Workbench read-path source-contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
        proof_field="gateway_workbench_contract_proof",
        ref_field="gateway_workbench_contract_proof_ref",
        artifact_name="Gateway/Workbench contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
        proof_field="gateway_workbench_discovery_contract_proof",
        ref_field="gateway_workbench_discovery_contract_proof_ref",
        artifact_name="Gateway/Workbench discovery contract proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV,
        proof_field="gateway_workbench_runtime_execution_proof",
        ref_field="gateway_workbench_runtime_execution_proof_ref",
        artifact_name="Gateway/Workbench runtime execution proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=BOND_MATURITY_RUNTIME_EXECUTION_ENV,
        proof_field="bond_maturity_live_proof",
        ref_field="bond_maturity_live_proof_ref",
        artifact_name="bond maturity live proof",
    ),
    ConfiguredJsonProofArtifact(
        env_name=LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
        proof_field="low_income_core_cashflow_live_proof",
        ref_field="low_income_core_cashflow_live_proof_ref",
        artifact_name="low-income Core cashflow live proof",
    ),
)


def configured_implementation_proof_artifacts(
    *,
    repository_root: Path | None = None,
) -> ConfiguredImplementationProofArtifacts:
    root = repository_root or Path.cwd()
    artifact_fields: dict[str, Any] = {}

    for ref_binding in _REF_ONLY_PROOF_ARTIFACTS:
        path = _configured_path(ref_binding.env_name, root=root)
        artifact_fields[ref_binding.ref_field] = _source_safe_artifact_ref(
            path,
            root=root,
            artifact_name=f"{ref_binding.artifact_name} artifact",
        )

    for json_binding in _JSON_PROOF_ARTIFACTS:
        path = _configured_path(json_binding.env_name, root=root)
        proof_ref = _source_safe_artifact_ref(
            path,
            root=root,
            artifact_name=f"{json_binding.artifact_name} artifact",
        )
        payload = read_optional_json_object(path, artifact_name=json_binding.artifact_name)
        if payload is not None and path is not None and proof_ref is not None:
            payload = bind_aggregate_proof_provenance(
                payload,
                artifact_path=path,
                proof_ref=proof_ref,
                repository_root=root,
            )
        artifact_fields[json_binding.proof_field] = payload
        artifact_fields[json_binding.ref_field] = proof_ref

    return ConfiguredImplementationProofArtifacts(**artifact_fields)


def _configured_path(env_name: str, *, root: Path) -> Path | None:
    configured = os.getenv(env_name, "").strip()
    if not configured:
        return None
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path
    return root / configured_path


def _source_safe_artifact_ref(
    path: Path | None,
    *,
    root: Path,
    artifact_name: str,
) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return artifact_name
