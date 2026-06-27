from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_model_risk_operations_proof import AI_MODEL_RISK_OPERATIONS_PROOF_ENV
from app.application.ai_workflow_pack_registration_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.outbox_broker_proof import OUTBOX_BROKER_PROOF_ENV
from app.application.outbox_platform_mesh_event_publication_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
)
from app.application.platform_mesh_onboarding_proof import PLATFORM_MESH_ONBOARDING_PROOF_ENV
from app.application.report_intake_route_proof import REPORT_INTAKE_ROUTE_PROOF_ENV
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.source_ingestion_readiness import LIVE_PROOF_ENV, SCHEDULED_WORKER_PROOF_ENV
from app.application.workbench_read_path_proof import WORKBENCH_READ_PATH_PROOF_ENV


@dataclass(frozen=True)
class ConfiguredImplementationProofArtifacts:
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
    ai_workflow_pack_registration_proof: dict[str, Any] | None
    ai_workflow_pack_registration_proof_ref: str | None
    ai_workflow_pack_runtime_execution_proof: dict[str, Any] | None
    ai_workflow_pack_runtime_execution_proof_ref: str | None
    outbox_broker_proof: dict[str, Any] | None
    outbox_broker_proof_ref: str | None
    outbox_platform_mesh_event_publication_proof: dict[str, Any] | None
    outbox_platform_mesh_event_publication_proof_ref: str | None
    report_intake_route_proof: dict[str, Any] | None
    report_intake_route_proof_ref: str | None
    platform_mesh_onboarding_proof: dict[str, Any] | None
    platform_mesh_onboarding_proof_ref: str | None
    workbench_read_path_proof: dict[str, Any] | None
    workbench_read_path_proof_ref: str | None


_REF_ONLY_PROOF_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    (
        LIVE_PROOF_ENV,
        "source_ingestion_live_proof_ref",
        "source ingestion live proof",
    ),
    (
        SCHEDULED_WORKER_PROOF_ENV,
        "source_ingestion_scheduled_worker_proof_ref",
        "source ingestion scheduled-worker proof",
    ),
)

_JSON_PROOF_ARTIFACTS: tuple[tuple[str, str, str, str], ...] = (
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
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        "ai_workflow_pack_registration_proof",
        "ai_workflow_pack_registration_proof_ref",
        "AI workflow-pack registration proof",
    ),
    (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
        "ai_workflow_pack_runtime_execution_proof",
        "ai_workflow_pack_runtime_execution_proof_ref",
        "AI workflow-pack runtime execution proof",
    ),
    (
        OUTBOX_BROKER_PROOF_ENV,
        "outbox_broker_proof",
        "outbox_broker_proof_ref",
        "outbox broker proof",
    ),
    (
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
        "outbox_platform_mesh_event_publication_proof",
        "outbox_platform_mesh_event_publication_proof_ref",
        "outbox platform mesh event publication proof",
    ),
    (
        REPORT_INTAKE_ROUTE_PROOF_ENV,
        "report_intake_route_proof",
        "report_intake_route_proof_ref",
        "report intake route proof",
    ),
    (
        PLATFORM_MESH_ONBOARDING_PROOF_ENV,
        "platform_mesh_onboarding_proof",
        "platform_mesh_onboarding_proof_ref",
        "platform mesh onboarding proof",
    ),
    (
        WORKBENCH_READ_PATH_PROOF_ENV,
        "workbench_read_path_proof",
        "workbench_read_path_proof_ref",
        "workbench read-path proof",
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
        artifact_fields[proof_field] = _read_optional_json_object(
            path,
            artifact_name=artifact_name,
        )
        artifact_fields[ref_field] = _source_safe_artifact_ref(
            path,
            root=root,
            artifact_name=f"{artifact_name} artifact",
        )

    return ConfiguredImplementationProofArtifacts(**artifact_fields)


def _configured_path(env_name: str, *, root: Path) -> Path | None:
    configured = os.getenv(env_name, "").strip()
    if not configured:
        return None
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path
    return root / configured_path


def _read_optional_json_object(
    path: Path | None,
    *,
    artifact_name: str,
) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_name} must be a JSON object")
    return payload


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
