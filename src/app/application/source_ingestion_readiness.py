from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from app.application.source_ingestion_runtime_evidence import (
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV as SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    source_ingestion_runtime_execution_is_valid,
)
from app.application.source_ingestion_scheduled_worker import (
    scheduled_worker_deploy_proof_is_valid,
)
from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION
from app.runtime.repository_state import DATABASE_URL_ENV


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
CORE_QUERY_BASE_URL_ENV = "LOTUS_CORE_QUERY_BASE_URL"
CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV = "LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL"
MANIFEST_ENV = "LOTUS_IDEA_SOURCE_INGESTION_MANIFEST"
SCHEDULED_WORKER_PROOF_ENV = "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_TIMEOUT_SECONDS"
EXAMPLE_MANIFEST_PATH = Path(
    "docs/examples/source-ingestion/high-cash-worker-manifest.example.json"
)


@dataclass(frozen=True)
class SourceIngestionReadinessSnapshot:
    repository: str
    source_authority: str
    opportunity_family: str
    manifest_schema_version: str
    example_manifest_path: str
    example_manifest_available: bool
    configured_manifest_available: bool
    configured_live_proof_available: bool
    live_core_source_proof_valid: bool
    configured_scheduled_worker_proof_available: bool
    scheduled_worker_deploy_proof_valid: bool
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool
    durable_repository_configured: bool
    run_once_configuration_status: str
    certification_status: str
    configuration_blockers: tuple[str, ...]
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool

    @property
    def run_once_configured(self) -> bool:
        return not self.configuration_blockers

    @property
    def live_source_certified(self) -> bool:
        return self.certification_status == "certified"


def build_source_ingestion_readiness_snapshot(
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> SourceIngestionReadinessSnapshot:
    example_manifest = repository_root / EXAMPLE_MANIFEST_PATH
    configured_manifest = os.getenv(MANIFEST_ENV, "").strip()
    configured_manifest_path = resolve_source_ingestion_manifest_path(
        configured_manifest,
        repository_root=repository_root,
    )
    configured_runtime_execution_path = resolve_source_ingestion_manifest_path(
        os.getenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, "").strip(),
        repository_root=repository_root,
    )
    configured_scheduled_worker_proof_path = resolve_source_ingestion_manifest_path(
        os.getenv(SCHEDULED_WORKER_PROOF_ENV, "").strip(),
        repository_root=repository_root,
    )
    core_source_urls = core_source_runtime_urls_from_environment()
    live_core_source_proof_valid = _runtime_execution_valid(configured_runtime_execution_path)
    scheduled_worker_deploy_proof_valid = _scheduled_worker_deploy_proof_valid(
        configured_scheduled_worker_proof_path
    )
    configuration_blockers = _configuration_blockers(
        example_manifest=example_manifest,
        configured_manifest_path=configured_manifest_path,
        core_source_urls=core_source_urls,
    )
    certification_blockers = _certification_blockers(
        live_core_source_proof_valid=live_core_source_proof_valid,
        scheduled_worker_deploy_proof_valid=scheduled_worker_deploy_proof_valid,
    )
    return SourceIngestionReadinessSnapshot(
        repository="lotus-idea",
        source_authority="lotus-core",
        opportunity_family="high_cash",
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        example_manifest_path=EXAMPLE_MANIFEST_PATH.as_posix(),
        example_manifest_available=example_manifest.is_file(),
        configured_manifest_available=bool(
            configured_manifest_path and configured_manifest_path.is_file()
        ),
        configured_live_proof_available=bool(
            configured_runtime_execution_path and configured_runtime_execution_path.is_file()
        ),
        live_core_source_proof_valid=live_core_source_proof_valid,
        configured_scheduled_worker_proof_available=bool(
            configured_scheduled_worker_proof_path
            and configured_scheduled_worker_proof_path.is_file()
        ),
        scheduled_worker_deploy_proof_valid=scheduled_worker_deploy_proof_valid,
        core_base_url_configured=core_source_urls.fully_configured,
        core_query_base_url_configured=core_source_urls.query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            core_source_urls.query_control_plane_base_url_configured
        ),
        durable_repository_configured=bool(os.getenv(DATABASE_URL_ENV, "").strip()),
        run_once_configuration_status=("configured" if not configuration_blockers else "blocked"),
        certification_status="not_certified",
        configuration_blockers=configuration_blockers,
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


@dataclass(frozen=True)
class CoreSourceRuntimeUrls:
    query_base_url: str | None
    query_control_plane_base_url: str | None
    query_base_url_configured: bool
    query_control_plane_base_url_configured: bool

    @property
    def fully_configured(self) -> bool:
        return self.query_base_url_configured and self.query_control_plane_base_url_configured


def core_source_runtime_urls_from_environment() -> CoreSourceRuntimeUrls:
    legacy_base_url = os.getenv(CORE_BASE_URL_ENV, "").strip() or None
    query_base_url = os.getenv(CORE_QUERY_BASE_URL_ENV, "").strip() or legacy_base_url
    query_control_plane_base_url = (
        os.getenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "").strip() or legacy_base_url
    )
    return CoreSourceRuntimeUrls(
        query_base_url=query_base_url,
        query_control_plane_base_url=query_control_plane_base_url,
        query_base_url_configured=bool(query_base_url),
        query_control_plane_base_url_configured=bool(query_control_plane_base_url),
    )


def _configuration_blockers(
    *,
    example_manifest: Path,
    configured_manifest_path: Path | None,
    core_source_urls: CoreSourceRuntimeUrls,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not example_manifest.is_file():
        blockers.append("example_manifest_missing")
    if configured_manifest_path is None:
        blockers.append("source_ingestion_manifest_not_configured")
    elif not configured_manifest_path.is_file():
        blockers.append("source_ingestion_manifest_unreadable")
    if not core_source_urls.query_base_url_configured:
        blockers.append("lotus_core_query_base_url_not_configured")
    if not core_source_urls.query_control_plane_base_url_configured:
        blockers.append("lotus_core_query_control_plane_base_url_not_configured")
    if not core_source_urls.fully_configured:
        blockers.append("lotus_core_base_url_not_configured")
    if not os.getenv(DATABASE_URL_ENV, "").strip():
        blockers.append("durable_repository_not_configured")
    return tuple(blockers)


def _certification_blockers(
    *,
    live_core_source_proof_valid: bool,
    scheduled_worker_deploy_proof_valid: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not live_core_source_proof_valid:
        blockers.append("live_core_source_proof_missing")
    if not scheduled_worker_deploy_proof_valid:
        blockers.append("scheduled_worker_deploy_proof_missing")
    blockers.extend(
        (
            "data_mesh_runtime_telemetry_not_certified",
            "gateway_workbench_proof_missing",
        )
    )
    return tuple(blockers)


def _runtime_execution_valid(configured_runtime_execution_path: Path | None) -> bool:
    if configured_runtime_execution_path is None or not configured_runtime_execution_path.is_file():
        return False
    try:
        payload = json.loads(configured_runtime_execution_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and source_ingestion_runtime_execution_is_valid(payload)


def _scheduled_worker_deploy_proof_valid(
    configured_scheduled_worker_proof_path: Path | None,
) -> bool:
    if (
        configured_scheduled_worker_proof_path is None
        or not configured_scheduled_worker_proof_path.is_file()
    ):
        return False
    try:
        payload = json.loads(configured_scheduled_worker_proof_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and scheduled_worker_deploy_proof_is_valid(payload)


def resolve_source_ingestion_manifest_path(
    configured_manifest: str,
    *,
    repository_root: Path,
) -> Path | None:
    if not configured_manifest:
        return None
    manifest_path = Path(configured_manifest)
    if manifest_path.is_absolute():
        return manifest_path
    return repository_root / manifest_path
