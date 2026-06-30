from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    MANIFEST_ENV,
    TIMEOUT_SECONDS_ENV,
)
from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.runtime.source_ingestion_state import (
    SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
    SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
    SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV,
    SourceIngestionRuntime,
    SourceIngestionRuntimeBlocker,
    build_source_ingestion_runtime_from_environment,
)


def test_source_ingestion_runtime_blocks_when_manifest_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker("source_ingestion_manifest_not_configured")


def test_source_ingestion_runtime_blocks_unreadable_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_manifest = tmp_path / "missing.json"
    monkeypatch.setenv(MANIFEST_ENV, str(missing_manifest))

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker("source_ingestion_manifest_unreadable")


def test_source_ingestion_runtime_blocks_when_core_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_not_configured",
        configured_manifest_available=True,
    )


def test_source_ingestion_runtime_blocks_invalid_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "source_ingestion_manifest_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_non_object_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "source_ingestion_manifest_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_invalid_core_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "not-a-url")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "0")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_non_numeric_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "slow")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_invalid_connection_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(SOURCE_INGESTION_MAX_CONNECTIONS_ENV, "0")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_keepalive_limit_above_connection_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(SOURCE_INGESTION_MAX_CONNECTIONS_ENV, "2")
    monkeypatch.setenv(SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV, "3")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_blocks_invalid_pool_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, "0")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_invalid",
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_source_ingestion_runtime_builds_manifest_plan_and_core_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "2.5")

    result = build_source_ingestion_runtime_from_environment()

    assert isinstance(result, SourceIngestionRuntime)
    assert result.configured_manifest_available is True
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert result.plan.command.work_items[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_source_ingestion_runtime_close_releases_owned_core_clients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class CloseAwareDownstreamClient:
        def __init__(self, config: object) -> None:
            self.config = config
            self.closed = False
            created_clients.append(self)

        def close(self) -> None:
            self.closed = True

    created_clients: list[CloseAwareDownstreamClient] = []
    monkeypatch.setattr(
        "app.runtime.source_ingestion_state.DownstreamJsonClient",
        CloseAwareDownstreamClient,
    )
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")

    result = build_source_ingestion_runtime_from_environment()

    assert isinstance(result, SourceIngestionRuntime)
    assert len(created_clients) == 2
    result.close()
    assert [client.closed for client in created_clients] == [True, True]


def test_source_ingestion_runtime_builds_with_split_core_runtime_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "2.5")

    result = build_source_ingestion_runtime_from_environment()

    assert isinstance(result, SourceIngestionRuntime)
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_source_ingestion_runtime_blocks_partial_split_core_runtime_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "lotus_core_base_url_not_configured",
        configured_manifest_available=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=False,
    )


def test_source_ingestion_runtime_uses_default_timeout_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.delenv(TIMEOUT_SECONDS_ENV, raising=False)

    result = build_source_ingestion_runtime_from_environment()

    assert isinstance(result, SourceIngestionRuntime)
    assert result.plan.check_summary()["maxItems"] == 100


def write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "workItems": [
                    {
                        "portfolioId": "PB_SG_GLOBAL_BAL_001",
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest
