from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    MANIFEST_ENV,
    REPOSITORY_ROOT,
    TIMEOUT_SECONDS_ENV,
    CoreSourceRuntimeUrls,
    core_source_runtime_urls_from_environment,
    resolve_source_ingestion_manifest_path,
)
from app.application.source_ingestion_worker import (
    SourceIngestionWorkerPlan,
    source_ingestion_worker_plan_from_manifest,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
)
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.ports.core_sources import CoreOpportunitySourcePort


@dataclass(frozen=True)
class SourceIngestionRuntime:
    plan: SourceIngestionWorkerPlan
    core_source: CoreOpportunitySourcePort
    configured_manifest_available: bool
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool


@dataclass(frozen=True)
class SourceIngestionRuntimeBlocker:
    code: str
    configured_manifest_available: bool = False
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


def build_source_ingestion_runtime_from_environment() -> (
    SourceIngestionRuntime | SourceIngestionRuntimeBlocker
):
    manifest_path = resolve_source_ingestion_manifest_path(
        os.getenv(MANIFEST_ENV, "").strip(),
        repository_root=REPOSITORY_ROOT,
    )
    configured_manifest_available = bool(manifest_path and manifest_path.is_file())
    if manifest_path is None:
        return SourceIngestionRuntimeBlocker("source_ingestion_manifest_not_configured")
    if not manifest_path.is_file():
        return SourceIngestionRuntimeBlocker("source_ingestion_manifest_unreadable")

    core_source_urls = core_source_runtime_urls_from_environment()
    if not core_source_urls.fully_configured:
        return SourceIngestionRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            configured_manifest_available=configured_manifest_available,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )

    try:
        plan = source_ingestion_worker_plan_from_manifest(_read_manifest(manifest_path))
        query_config, query_control_plane_config = _core_source_client_configs(core_source_urls)
    except DownstreamClientConfigurationError:
        return SourceIngestionRuntimeBlocker(
            "lotus_core_base_url_invalid",
            configured_manifest_available=configured_manifest_available,
            core_base_url_configured=True,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError):
        return SourceIngestionRuntimeBlocker(
            "source_ingestion_manifest_invalid",
            configured_manifest_available=configured_manifest_available,
            core_base_url_configured=True,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )

    return SourceIngestionRuntime(
        plan=plan,
        core_source=LotusCoreHighCashSourceAdapter(
            query_client=DownstreamJsonClient(query_config),
            query_control_plane_client=DownstreamJsonClient(query_control_plane_config),
        ),
        configured_manifest_available=configured_manifest_available,
        core_base_url_configured=True,
        core_query_base_url_configured=core_source_urls.query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            core_source_urls.query_control_plane_base_url_configured
        ),
    )


def _core_source_client_configs(
    core_source_urls: CoreSourceRuntimeUrls,
) -> tuple[DownstreamClientConfig, DownstreamClientConfig]:
    if (
        core_source_urls.query_base_url is None
        or core_source_urls.query_control_plane_base_url is None
    ):
        raise DownstreamClientConfigurationError(
            f"{CORE_QUERY_BASE_URL_ENV} and {CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV} are required, "
            f"or {CORE_BASE_URL_ENV} must provide a compatibility fallback."
        )
    timeout_seconds = _timeout_seconds_from_environment()
    return (
        DownstreamClientConfig(
            base_url=core_source_urls.query_base_url,
            timeout_seconds=timeout_seconds,
        ),
        DownstreamClientConfig(
            base_url=core_source_urls.query_control_plane_base_url,
            timeout_seconds=timeout_seconds,
        ),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _timeout_seconds_from_environment() -> float:
    raw_timeout = os.getenv(TIMEOUT_SECONDS_ENV, "2.0")
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise DownstreamClientConfigurationError(
            "source ingestion timeout seconds must be numeric"
        ) from exc
    if timeout <= 0:
        raise DownstreamClientConfigurationError(
            "source ingestion timeout seconds must be positive"
        )
    return timeout
