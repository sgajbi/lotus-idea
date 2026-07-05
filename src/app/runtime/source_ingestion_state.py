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
from app.application.source_ingestion import SourceIngestionBatchLimitExceeded
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

SOURCE_INGESTION_MAX_CONNECTIONS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_MAX_CONNECTIONS"
SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV = (
    "LOTUS_IDEA_SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS"
)
SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_POOL_TIMEOUT_SECONDS"
SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_RETRY_MAX_ATTEMPTS"
SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV = (
    "LOTUS_IDEA_SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS"
)
SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV = (
    "LOTUS_IDEA_SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS"
)


@dataclass(frozen=True)
class CoreHighCashSourceRuntime:
    core_source: CoreOpportunitySourcePort
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.core_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class CoreHighCashSourceRuntimeBlocker:
    code: str
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class SourceIngestionRuntime:
    plan: SourceIngestionWorkerPlan
    core_source: CoreOpportunitySourcePort
    configured_manifest_available: bool
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.core_source, "close", None)
        if callable(close):
            close()


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
    except SourceIngestionBatchLimitExceeded:
        return SourceIngestionRuntimeBlocker(
            "source_ingestion_batch_limit_exceeded",
            configured_manifest_available=configured_manifest_available,
            core_base_url_configured=True,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
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


def build_core_high_cash_source_runtime_from_environment() -> (
    CoreHighCashSourceRuntime | CoreHighCashSourceRuntimeBlocker
):
    core_source_urls = core_source_runtime_urls_from_environment()
    if not core_source_urls.fully_configured:
        return CoreHighCashSourceRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            core_base_url_configured=False,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
    try:
        query_config, query_control_plane_config = _core_source_client_configs(core_source_urls)
    except DownstreamClientConfigurationError:
        return CoreHighCashSourceRuntimeBlocker(
            "lotus_core_base_url_invalid",
            core_base_url_configured=True,
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
    return CoreHighCashSourceRuntime(
        core_source=LotusCoreHighCashSourceAdapter(
            query_client=DownstreamJsonClient(query_config),
            query_control_plane_client=DownstreamJsonClient(query_control_plane_config),
        ),
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
    max_connections = _positive_int_env(SOURCE_INGESTION_MAX_CONNECTIONS_ENV, default=20)
    max_keepalive_connections = _positive_int_env(
        SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV, default=10
    )
    pool_timeout_seconds = _positive_float_env(
        SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, default=2.0
    )
    retry_max_attempts = _positive_int_env(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, default=1)
    retry_initial_backoff_seconds = _non_negative_float_env(
        SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
    )
    retry_max_backoff_seconds = _non_negative_float_env(
        SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
    )
    return (
        DownstreamClientConfig(
            base_url=core_source_urls.query_base_url,
            timeout_seconds=timeout_seconds,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            pool_timeout_seconds=pool_timeout_seconds,
            retry_max_attempts=retry_max_attempts,
            retry_initial_backoff_seconds=retry_initial_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_post_without_idempotency=True,
        ),
        DownstreamClientConfig(
            base_url=core_source_urls.query_control_plane_base_url,
            timeout_seconds=timeout_seconds,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            pool_timeout_seconds=pool_timeout_seconds,
            retry_max_attempts=retry_max_attempts,
            retry_initial_backoff_seconds=retry_initial_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_post_without_idempotency=True,
        ),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _timeout_seconds_from_environment() -> float:
    return _positive_float_env(TIMEOUT_SECONDS_ENV, default=2.0)


def _positive_float_env(name: str, *, default: float) -> float:
    raw_timeout = os.getenv(name, str(default))
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise DownstreamClientConfigurationError(f"{name} must be numeric") from exc
    if timeout <= 0:
        raise DownstreamClientConfigurationError(f"{name} must be positive")
    return timeout


def _non_negative_float_env(name: str, *, default: float) -> float:
    raw_duration = os.getenv(name, str(default))
    try:
        duration_seconds = float(raw_duration)
    except ValueError as exc:
        raise DownstreamClientConfigurationError(f"{name} must be numeric") from exc
    if duration_seconds < 0:
        raise DownstreamClientConfigurationError(f"{name} must not be negative")
    return duration_seconds


def _positive_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise DownstreamClientConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise DownstreamClientConfigurationError(f"{name} must be positive")
    return value
