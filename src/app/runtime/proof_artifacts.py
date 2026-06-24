from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.outbox_broker_proof import OUTBOX_BROKER_PROOF_ENV
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
    outbox_broker_proof: dict[str, Any] | None
    outbox_broker_proof_ref: str | None
    workbench_read_path_proof: dict[str, Any] | None
    workbench_read_path_proof_ref: str | None


def configured_implementation_proof_artifacts(
    *,
    repository_root: Path | None = None,
) -> ConfiguredImplementationProofArtifacts:
    root = repository_root or Path.cwd()
    source_ingestion_live_proof_path = _configured_path(LIVE_PROOF_ENV, root=root)
    source_ingestion_scheduled_worker_proof_path = _configured_path(
        SCHEDULED_WORKER_PROOF_ENV,
        root=root,
    )
    durable_repository_proof_path = _configured_path(DURABLE_REPOSITORY_PROOF_ENV, root=root)
    runtime_trust_telemetry_proof_path = _configured_path(
        RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
        root=root,
    )
    outbox_broker_proof_path = _configured_path(OUTBOX_BROKER_PROOF_ENV, root=root)
    workbench_read_path_proof_path = _configured_path(WORKBENCH_READ_PATH_PROOF_ENV, root=root)
    return ConfiguredImplementationProofArtifacts(
        source_ingestion_live_proof_ref=_source_safe_artifact_ref(
            source_ingestion_live_proof_path,
            root=root,
            artifact_name="source ingestion live proof artifact",
        ),
        source_ingestion_scheduled_worker_proof_ref=_source_safe_artifact_ref(
            source_ingestion_scheduled_worker_proof_path,
            root=root,
            artifact_name="source ingestion scheduled-worker proof artifact",
        ),
        durable_repository_proof=_read_optional_json_object(
            durable_repository_proof_path,
            artifact_name="durable repository proof",
        ),
        durable_repository_proof_ref=_source_safe_artifact_ref(
            durable_repository_proof_path,
            root=root,
            artifact_name="durable repository proof artifact",
        ),
        runtime_trust_telemetry_proof=_read_optional_json_object(
            runtime_trust_telemetry_proof_path,
            artifact_name="runtime trust telemetry proof",
        ),
        runtime_trust_telemetry_proof_ref=_source_safe_artifact_ref(
            runtime_trust_telemetry_proof_path,
            root=root,
            artifact_name="runtime trust telemetry proof artifact",
        ),
        outbox_broker_proof=_read_optional_json_object(
            outbox_broker_proof_path,
            artifact_name="outbox broker proof",
        ),
        outbox_broker_proof_ref=_source_safe_artifact_ref(
            outbox_broker_proof_path,
            root=root,
            artifact_name="outbox broker proof artifact",
        ),
        workbench_read_path_proof=_read_optional_json_object(
            workbench_read_path_proof_path,
            artifact_name="workbench read-path proof",
        ),
        workbench_read_path_proof_ref=_source_safe_artifact_ref(
            workbench_read_path_proof_path,
            root=root,
            artifact_name="workbench read-path proof artifact",
        ),
    )


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
