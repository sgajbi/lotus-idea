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
from app.application.source_ingestion import SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING
from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION
from app.infrastructure.downstream_client import DownstreamClientConfig
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)
from app.infrastructure.lotus_risk_sources import (
    LotusRiskConcentrationSourceAdapter,
    LotusRiskDrawdownSourceAdapter,
    LotusRiskVolatilitySourceAdapter,
)
from app.runtime.source_ingestion_state import (
    CoreBenchmarkAssignmentSourceRuntime,
    CoreBenchmarkAssignmentSourceRuntimeBlocker,
    CoreBondMaturitySourceRuntime,
    CoreBondMaturitySourceRuntimeBlocker,
    CoreHighCashSourceRuntime,
    CoreHighCashSourceRuntimeBlocker,
    CoreLowIncomeSourceRuntime,
    CoreLowIncomeSourceRuntimeBlocker,
    PERFORMANCE_BASE_URL_ENV,
    PERFORMANCE_TIMEOUT_SECONDS_ENV,
    RISK_BASE_URL_ENV,
    RISK_TIMEOUT_SECONDS_ENV,
    PerformanceUnderperformanceSourceRuntime,
    PerformanceUnderperformanceSourceRuntimeBlocker,
    RiskConcentrationSourceRuntime,
    RiskConcentrationSourceRuntimeBlocker,
    RiskDrawdownSourceRuntime,
    RiskDrawdownSourceRuntimeBlocker,
    RiskVolatilitySourceRuntime,
    RiskVolatilitySourceRuntimeBlocker,
    SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
    SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
    SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV,
    SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV,
    SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV,
    SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV,
    SourceIngestionRuntime,
    SourceIngestionRuntimeBlocker,
    build_core_benchmark_assignment_source_runtime_from_environment,
    build_core_bond_maturity_source_runtime_from_environment,
    build_core_high_cash_source_runtime_from_environment,
    build_core_low_income_source_runtime_from_environment,
    build_performance_underperformance_source_runtime_from_environment,
    build_risk_concentration_source_runtime_from_environment,
    build_risk_drawdown_source_runtime_from_environment,
    build_risk_volatility_source_runtime_from_environment,
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


def test_core_high_cash_source_runtime_blocks_when_core_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_core_high_cash_source_runtime_from_environment()

    assert result == CoreHighCashSourceRuntimeBlocker("lotus_core_base_url_not_configured")


def test_core_low_income_source_runtime_blocks_when_core_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_core_low_income_source_runtime_from_environment()

    assert result == CoreLowIncomeSourceRuntimeBlocker("lotus_core_base_url_not_configured")


def test_core_benchmark_assignment_source_runtime_blocks_when_core_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_core_benchmark_assignment_source_runtime_from_environment()

    assert result == CoreBenchmarkAssignmentSourceRuntimeBlocker(
        "lotus_core_base_url_not_configured"
    )


def test_core_bond_maturity_source_runtime_blocks_when_core_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)

    result = build_core_bond_maturity_source_runtime_from_environment()

    assert result == CoreBondMaturitySourceRuntimeBlocker("lotus_core_base_url_not_configured")


def test_risk_concentration_source_runtime_blocks_when_risk_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(RISK_BASE_URL_ENV, raising=False)

    result = build_risk_concentration_source_runtime_from_environment()

    assert result == RiskConcentrationSourceRuntimeBlocker("lotus_risk_base_url_not_configured")


def test_risk_volatility_source_runtime_blocks_when_risk_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(RISK_BASE_URL_ENV, raising=False)

    result = build_risk_volatility_source_runtime_from_environment()

    assert result == RiskVolatilitySourceRuntimeBlocker("lotus_risk_base_url_not_configured")


def test_risk_drawdown_source_runtime_blocks_when_risk_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(RISK_BASE_URL_ENV, raising=False)

    result = build_risk_drawdown_source_runtime_from_environment()

    assert result == RiskDrawdownSourceRuntimeBlocker("lotus_risk_base_url_not_configured")


def test_performance_underperformance_source_runtime_blocks_when_base_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PERFORMANCE_BASE_URL_ENV, raising=False)

    result = build_performance_underperformance_source_runtime_from_environment()

    assert result == PerformanceUnderperformanceSourceRuntimeBlocker(
        "lotus_performance_base_url_not_configured"
    )


def test_core_high_cash_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")

    result = build_core_high_cash_source_runtime_from_environment()

    assert isinstance(result, CoreHighCashSourceRuntime)
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_core_low_income_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")

    result = build_core_low_income_source_runtime_from_environment()

    assert isinstance(result, CoreLowIncomeSourceRuntime)
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_core_benchmark_assignment_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")

    result = build_core_benchmark_assignment_source_runtime_from_environment()

    assert isinstance(result, CoreBenchmarkAssignmentSourceRuntime)
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_core_bond_maturity_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")

    result = build_core_bond_maturity_source_runtime_from_environment()

    assert isinstance(result, CoreBondMaturitySourceRuntime)
    assert result.core_base_url_configured is True
    assert result.core_query_base_url_configured is True
    assert result.core_query_control_plane_base_url_configured is True
    assert isinstance(result.core_source, LotusCoreHighCashSourceAdapter)


def test_risk_concentration_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_concentration_source_runtime_from_environment()

    assert isinstance(result, RiskConcentrationSourceRuntime)
    assert result.risk_base_url_configured is True
    assert isinstance(result.risk_source, LotusRiskConcentrationSourceAdapter)


def test_risk_volatility_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_volatility_source_runtime_from_environment()

    assert isinstance(result, RiskVolatilitySourceRuntime)
    assert result.risk_base_url_configured is True
    assert isinstance(result.risk_source, LotusRiskVolatilitySourceAdapter)


def test_risk_drawdown_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_drawdown_source_runtime_from_environment()

    assert isinstance(result, RiskDrawdownSourceRuntime)
    assert result.risk_base_url_configured is True
    assert isinstance(result.risk_source, LotusRiskDrawdownSourceAdapter)


def test_performance_underperformance_source_runtime_builds_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.setenv(PERFORMANCE_BASE_URL_ENV, "http://localhost:8400")

    result = build_performance_underperformance_source_runtime_from_environment()

    assert isinstance(result, PerformanceUnderperformanceSourceRuntime)
    assert result.performance_base_url_configured is True
    assert isinstance(result.performance_source, LotusPerformanceUnderperformanceSourceAdapter)


def test_core_high_cash_source_runtime_blocks_invalid_core_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CORE_BASE_URL_ENV, "not-a-url")

    result = build_core_high_cash_source_runtime_from_environment()

    assert result == CoreHighCashSourceRuntimeBlocker(
        "lotus_core_base_url_invalid",
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_core_low_income_source_runtime_blocks_invalid_core_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CORE_BASE_URL_ENV, "not-a-url")

    result = build_core_low_income_source_runtime_from_environment()

    assert result == CoreLowIncomeSourceRuntimeBlocker(
        "lotus_core_base_url_invalid",
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_core_benchmark_assignment_source_runtime_blocks_invalid_core_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CORE_BASE_URL_ENV, "not-a-url")

    result = build_core_benchmark_assignment_source_runtime_from_environment()

    assert result == CoreBenchmarkAssignmentSourceRuntimeBlocker(
        "lotus_core_base_url_invalid",
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_core_bond_maturity_source_runtime_blocks_invalid_core_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CORE_BASE_URL_ENV, "not-a-url")

    result = build_core_bond_maturity_source_runtime_from_environment()

    assert result == CoreBondMaturitySourceRuntimeBlocker(
        "lotus_core_base_url_invalid",
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )


def test_risk_concentration_source_runtime_blocks_invalid_risk_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "not-a-url")

    result = build_risk_concentration_source_runtime_from_environment()

    assert result == RiskConcentrationSourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_risk_volatility_source_runtime_blocks_invalid_risk_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "not-a-url")

    result = build_risk_volatility_source_runtime_from_environment()

    assert result == RiskVolatilitySourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_risk_drawdown_source_runtime_blocks_invalid_risk_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "not-a-url")

    result = build_risk_drawdown_source_runtime_from_environment()

    assert result == RiskDrawdownSourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_performance_underperformance_source_runtime_blocks_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERFORMANCE_BASE_URL_ENV, "not-a-url")

    result = build_performance_underperformance_source_runtime_from_environment()

    assert result == PerformanceUnderperformanceSourceRuntimeBlocker(
        "lotus_performance_base_url_invalid",
        performance_base_url_configured=True,
    )


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


def test_source_ingestion_runtime_blocks_manifest_over_batch_ceiling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "maxItems": SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING + 1,
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
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")

    result = build_source_ingestion_runtime_from_environment()

    assert result == SourceIngestionRuntimeBlocker(
        "source_ingestion_batch_limit_exceeded",
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


def test_risk_concentration_source_runtime_blocks_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")
    monkeypatch.setenv(RISK_TIMEOUT_SECONDS_ENV, "0")

    result = build_risk_concentration_source_runtime_from_environment()

    assert result == RiskConcentrationSourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_risk_volatility_source_runtime_blocks_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")
    monkeypatch.setenv(RISK_TIMEOUT_SECONDS_ENV, "0")

    result = build_risk_volatility_source_runtime_from_environment()

    assert result == RiskVolatilitySourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_risk_drawdown_source_runtime_blocks_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")
    monkeypatch.setenv(RISK_TIMEOUT_SECONDS_ENV, "0")

    result = build_risk_drawdown_source_runtime_from_environment()

    assert result == RiskDrawdownSourceRuntimeBlocker(
        "lotus_risk_base_url_invalid",
        risk_base_url_configured=True,
    )


def test_performance_underperformance_source_runtime_blocks_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERFORMANCE_BASE_URL_ENV, "http://localhost:8400")
    monkeypatch.setenv(PERFORMANCE_TIMEOUT_SECONDS_ENV, "0")

    result = build_performance_underperformance_source_runtime_from_environment()

    assert result == PerformanceUnderperformanceSourceRuntimeBlocker(
        "lotus_performance_base_url_invalid",
        performance_base_url_configured=True,
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


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        (SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, "0"),
        (SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, "-0.01"),
        (SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, "slow"),
    ],
)
def test_source_ingestion_runtime_blocks_invalid_retry_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    env_name: str,
    env_value: str,
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(env_name, env_value)

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


def test_risk_concentration_source_runtime_close_releases_owned_risk_client(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_concentration_source_runtime_from_environment()

    assert isinstance(result, RiskConcentrationSourceRuntime)
    assert len(created_clients) == 1
    result.close()
    assert created_clients[0].closed is True


def test_risk_volatility_source_runtime_close_releases_owned_risk_client(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_volatility_source_runtime_from_environment()

    assert isinstance(result, RiskVolatilitySourceRuntime)
    assert len(created_clients) == 1
    result.close()
    assert created_clients[0].closed is True


def test_risk_drawdown_source_runtime_close_releases_owned_risk_client(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setenv(RISK_BASE_URL_ENV, "http://localhost:8300")

    result = build_risk_drawdown_source_runtime_from_environment()

    assert isinstance(result, RiskDrawdownSourceRuntime)
    assert len(created_clients) == 1
    result.close()
    assert created_clients[0].closed is True


def test_performance_underperformance_source_runtime_close_releases_owned_client(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setenv(PERFORMANCE_BASE_URL_ENV, "http://localhost:8400")

    result = build_performance_underperformance_source_runtime_from_environment()

    assert isinstance(result, PerformanceUnderperformanceSourceRuntime)
    assert len(created_clients) == 1
    result.close()
    assert created_clients[0].closed is True


def test_source_ingestion_runtime_applies_retry_policy_to_read_only_core_clients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class CapturingDownstreamClient:
        def __init__(self, config: object) -> None:
            self.config = config
            created_clients.append(self)

        def close(self) -> None:
            return None

    created_clients: list[CapturingDownstreamClient] = []
    monkeypatch.setattr(
        "app.runtime.source_ingestion_state.DownstreamJsonClient",
        CapturingDownstreamClient,
    )
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8100")
    monkeypatch.setenv(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, "3")
    monkeypatch.setenv(SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, "0.1")
    monkeypatch.setenv(SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, "0.4")

    result = build_source_ingestion_runtime_from_environment()

    assert isinstance(result, SourceIngestionRuntime)
    assert len(created_clients) == 2
    for created_client in created_clients:
        config = created_client.config
        assert isinstance(config, DownstreamClientConfig)
        assert config.retry_max_attempts == 3
        assert config.retry_initial_backoff_seconds == 0.1
        assert config.retry_max_backoff_seconds == 0.4
        assert config.retry_post_without_idempotency is True


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
