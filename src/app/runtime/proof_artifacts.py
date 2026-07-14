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
from app.application.bond_maturity_live_proof import BOND_MATURITY_LIVE_PROOF_ENV
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.data_mesh.platform_catalog_source_contract import PLATFORM_CATALOG_SOURCE_CONTRACT_ENV
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.report.intake_route_source_contract import (
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.source_ingestion_readiness import LIVE_PROOF_ENV, SCHEDULED_WORKER_PROOF_ENV
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)
from app.runtime.proof_artifact_files import read_optional_json_object


@dataclass(frozen=True)
class ConfiguredImplementationProofArtifacts:
    source_ingestion_live_proof: dict[str, Any] | None
    source_ingestion_live_proof_ref: str | None
    source_ingestion_scheduled_worker_proof_ref: str | None
    durable_repository_proof: dict[str, Any] | None
    durable_repository_proof_ref: str | None
    runtime_trust_telemetry_proof: dict[str, Any] | None
    runtime_trust_telemetry_proof_ref: str | None
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
    outbox_broker_source_contract_proof: dict[str, Any] | None
    outbox_broker_source_contract_proof_ref: str | None
    outbox_platform_mesh_event_source_contract_proof: dict[str, Any] | None
    outbox_platform_mesh_event_source_contract_proof_ref: str | None
    report_intake_route_source_contract_proof: dict[str, Any] | None
    report_intake_route_source_contract_proof_ref: str | None
    platform_catalog_source_contract: dict[str, Any] | None
    platform_catalog_source_contract_ref: str | None
    workbench_read_path_source_contract_proof: dict[str, Any] | None
    workbench_read_path_source_contract_proof_ref: str | None
    gateway_workbench_contract_proof: dict[str, Any] | None
    gateway_workbench_contract_proof_ref: str | None
    gateway_workbench_discovery_contract_proof: dict[str, Any] | None
    gateway_workbench_discovery_contract_proof_ref: str | None
    bond_maturity_live_proof: dict[str, Any] | None
    bond_maturity_live_proof_ref: str | None
    low_income_core_cashflow_live_proof: dict[str, Any] | None
    low_income_core_cashflow_live_proof_ref: str | None


_REF_ONLY_PROOF_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    (
        SCHEDULED_WORKER_PROOF_ENV,
        "source_ingestion_scheduled_worker_proof_ref",
        "source ingestion scheduled-worker proof",
    ),
)

_JSON_PROOF_ARTIFACTS: tuple[tuple[str, str, str, str], ...] = (
    (
        LIVE_PROOF_ENV,
        "source_ingestion_live_proof",
        "source_ingestion_live_proof_ref",
        "source ingestion live proof",
    ),
    (
        DURABLE_REPOSITORY_PROOF_ENV,
        "durable_repository_proof",
        "durable_repository_proof_ref",
        "durable repository proof",
    ),
    (
        RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
        "runtime_trust_telemetry_proof",
        "runtime_trust_telemetry_proof_ref",
        "runtime trust telemetry proof",
    ),
    (
        AI_LINEAGE_STORE_PROOF_ENV,
        "ai_lineage_store_proof",
        "ai_lineage_store_proof_ref",
        "AI lineage store proof",
    ),
    (
        AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
        "ai_model_risk_operations_proof",
        "ai_model_risk_operations_proof_ref",
        "AI model-risk operations proof",
    ),
    (
        OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
        "operator_workflows_operations_proof",
        "operator_workflows_operations_proof_ref",
        "operator workflows operations proof",
    ),
    (
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        "ai_workflow_pack_registration_proof",
        "ai_workflow_pack_registration_proof_ref",
        "AI workflow-pack registration source-contract proof",
    ),
    (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
        "ai_workflow_pack_runtime_execution_proof",
        "ai_workflow_pack_runtime_execution_proof_ref",
        "AI workflow-pack runtime execution proof",
    ),
    (
        OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
        "outbox_broker_source_contract_proof",
        "outbox_broker_source_contract_proof_ref",
        "outbox broker source-contract proof",
    ),
    (
        OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
        "outbox_platform_mesh_event_source_contract_proof",
        "outbox_platform_mesh_event_source_contract_proof_ref",
        "outbox platform mesh event source-contract proof",
    ),
    (
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
        "report_intake_route_source_contract_proof",
        "report_intake_route_source_contract_proof_ref",
        "Report intake-route source-contract proof",
    ),
    (
        PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
        "platform_catalog_source_contract",
        "platform_catalog_source_contract_ref",
        "platform catalog source contract",
    ),
    (
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
        "workbench_read_path_source_contract_proof",
        "workbench_read_path_source_contract_proof_ref",
        "Workbench read-path source-contract proof",
    ),
    (
        GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
        "gateway_workbench_contract_proof",
        "gateway_workbench_contract_proof_ref",
        "Gateway/Workbench contract proof",
    ),
    (
        GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
        "gateway_workbench_discovery_contract_proof",
        "gateway_workbench_discovery_contract_proof_ref",
        "Gateway/Workbench discovery contract proof",
    ),
    (
        BOND_MATURITY_LIVE_PROOF_ENV,
        "bond_maturity_live_proof",
        "bond_maturity_live_proof_ref",
        "bond maturity live proof",
    ),
    (
        LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
        "low_income_core_cashflow_live_proof",
        "low_income_core_cashflow_live_proof_ref",
        "low-income Core cashflow live proof",
    ),
)


def configured_implementation_proof_artifacts(
    *,
    repository_root: Path | None = None,
) -> ConfiguredImplementationProofArtifacts:
    root = repository_root or Path.cwd()
    artifact_fields: dict[str, Any] = {}

    for env_name, ref_field, artifact_name in _REF_ONLY_PROOF_ARTIFACTS:
        path = _configured_path(env_name, root=root)
        artifact_fields[ref_field] = _source_safe_artifact_ref(
            path,
            root=root,
            artifact_name=f"{artifact_name} artifact",
        )

    for env_name, proof_field, ref_field, artifact_name in _JSON_PROOF_ARTIFACTS:
        path = _configured_path(env_name, root=root)
        proof_ref = _source_safe_artifact_ref(
            path,
            root=root,
            artifact_name=f"{artifact_name} artifact",
        )
        payload = read_optional_json_object(path, artifact_name=artifact_name)
        if payload is not None and path is not None and proof_ref is not None:
            payload = bind_aggregate_proof_provenance(
                payload,
                artifact_path=path,
                proof_ref=proof_ref,
                repository_root=root,
            )
        artifact_fields[proof_field] = payload
        artifact_fields[ref_field] = proof_ref

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
