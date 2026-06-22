from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION
from app.repository_state import DATABASE_URL_ENV


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORE_BASE_URL_ENV = "LOTUS_CORE_BASE_URL"
MANIFEST_ENV = "LOTUS_IDEA_SOURCE_INGESTION_MANIFEST"
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
    core_base_url_configured: bool
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
    configured_manifest_path = _resolve_manifest_path(
        configured_manifest,
        repository_root=repository_root,
    )
    configuration_blockers = _configuration_blockers(
        example_manifest=example_manifest,
        configured_manifest_path=configured_manifest_path,
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
        core_base_url_configured=bool(os.getenv(CORE_BASE_URL_ENV, "").strip()),
        durable_repository_configured=bool(os.getenv(DATABASE_URL_ENV, "").strip()),
        run_once_configuration_status=("configured" if not configuration_blockers else "blocked"),
        certification_status="not_certified",
        configuration_blockers=configuration_blockers,
        certification_blockers=(
            "live_core_source_proof_missing",
            "scheduled_worker_deploy_proof_missing",
            "data_mesh_runtime_telemetry_missing",
            "gateway_workbench_proof_missing",
        ),
        supported_feature_promoted=False,
    )


def _configuration_blockers(
    *,
    example_manifest: Path,
    configured_manifest_path: Path | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not example_manifest.is_file():
        blockers.append("example_manifest_missing")
    if configured_manifest_path is None:
        blockers.append("source_ingestion_manifest_not_configured")
    elif not configured_manifest_path.is_file():
        blockers.append("source_ingestion_manifest_unreadable")
    if not os.getenv(CORE_BASE_URL_ENV, "").strip():
        blockers.append("lotus_core_base_url_not_configured")
    if not os.getenv(DATABASE_URL_ENV, "").strip():
        blockers.append("durable_repository_not_configured")
    return tuple(blockers)


def _resolve_manifest_path(
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
