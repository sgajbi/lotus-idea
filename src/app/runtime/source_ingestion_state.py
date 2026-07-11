from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from app.contracts.operational_limits import (
    DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
    DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
)
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
from app.infrastructure.lotus_advise_sources import LotusAdvisePolicyEvaluationSourceAdapter
from app.infrastructure.lotus_core_sources import LotusCoreHighCashSourceAdapter
from app.infrastructure.lotus_manage_sources import LotusManageMandateHealthSourceAdapter
from app.infrastructure.lotus_performance_sources import (
    LotusPerformanceUnderperformanceSourceAdapter,
)
from app.infrastructure.lotus_risk_sources import (
    LotusRiskConcentrationSourceAdapter,
    LotusRiskDrawdownSourceAdapter,
    LotusRiskVolatilitySourceAdapter,
)
from app.ports.advise_sources import AdvisePolicyEvaluationSourcePort
from app.ports.performance_sources import PerformanceUnderperformanceSourcePort
from app.ports.core_sources import (
    CoreBenchmarkAssignmentSourcePort,
    CoreBondMaturitySourcePort,
    CoreLowIncomeSourcePort,
    CoreOpportunitySourcePort,
)
from app.ports.manage_sources import ManageMandateHealthSourcePort
from app.ports.risk_sources import (
    RiskConcentrationSourcePort,
    RiskDrawdownSourcePort,
    RiskVolatilitySourcePort,
)

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
RISK_BASE_URL_ENV = "LOTUS_RISK_BASE_URL"
RISK_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_RISK_TIMEOUT_SECONDS"
PERFORMANCE_BASE_URL_ENV = "LOTUS_PERFORMANCE_BASE_URL"
PERFORMANCE_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_PERFORMANCE_TIMEOUT_SECONDS"
MANAGE_BASE_URL_ENV = "LOTUS_MANAGE_BASE_URL"
MANAGE_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_MANAGE_TIMEOUT_SECONDS"
ADVISE_BASE_URL_ENV = "LOTUS_ADVISE_BASE_URL"
ADVISE_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_ADVISE_TIMEOUT_SECONDS"


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
class CoreLowIncomeSourceRuntime:
    core_source: CoreLowIncomeSourcePort
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.core_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class CoreBenchmarkAssignmentSourceRuntime:
    core_source: CoreBenchmarkAssignmentSourcePort
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.core_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class CoreBondMaturitySourceRuntime:
    core_source: CoreBondMaturitySourcePort
    core_base_url_configured: bool
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.core_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class RiskConcentrationSourceRuntime:
    risk_source: RiskConcentrationSourcePort
    risk_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.risk_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class RiskVolatilitySourceRuntime:
    risk_source: RiskVolatilitySourcePort
    risk_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.risk_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class RiskDrawdownSourceRuntime:
    risk_source: RiskDrawdownSourcePort
    risk_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.risk_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class PerformanceUnderperformanceSourceRuntime:
    performance_source: PerformanceUnderperformanceSourcePort
    performance_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.performance_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class ManageMandateHealthSourceRuntime:
    manage_source: ManageMandateHealthSourcePort
    manage_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.manage_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class AdvisePolicyEvaluationSourceRuntime:
    advise_source: AdvisePolicyEvaluationSourcePort
    advise_base_url_configured: bool

    def close(self) -> None:
        close = getattr(self.advise_source, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class CoreHighCashSourceRuntimeBlocker:
    code: str
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class CoreLowIncomeSourceRuntimeBlocker:
    code: str
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class CoreBenchmarkAssignmentSourceRuntimeBlocker:
    code: str
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class CoreBondMaturitySourceRuntimeBlocker:
    code: str
    core_base_url_configured: bool = False
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class RiskConcentrationSourceRuntimeBlocker:
    code: str
    risk_base_url_configured: bool = False


@dataclass(frozen=True)
class RiskVolatilitySourceRuntimeBlocker:
    code: str
    risk_base_url_configured: bool = False


@dataclass(frozen=True)
class RiskDrawdownSourceRuntimeBlocker:
    code: str
    risk_base_url_configured: bool = False


@dataclass(frozen=True)
class PerformanceUnderperformanceSourceRuntimeBlocker:
    code: str
    performance_base_url_configured: bool = False


@dataclass(frozen=True)
class ManageMandateHealthSourceRuntimeBlocker:
    code: str
    manage_base_url_configured: bool = False


@dataclass(frozen=True)
class AdvisePolicyEvaluationSourceRuntimeBlocker:
    code: str
    advise_base_url_configured: bool = False


@dataclass(frozen=True)
class _ConfiguredCoreSourceAdapter:
    core_source: LotusCoreHighCashSourceAdapter
    core_query_base_url_configured: bool
    core_query_control_plane_base_url_configured: bool


@dataclass(frozen=True)
class _CoreSourceAdapterBlocker:
    code: str
    core_query_base_url_configured: bool = False
    core_query_control_plane_base_url_configured: bool = False


@dataclass(frozen=True)
class _ConfiguredRiskSourceClient:
    risk_client: DownstreamJsonClient


@dataclass(frozen=True)
class _RiskSourceClientBlocker:
    code: str
    risk_base_url_configured: bool = False


@dataclass(frozen=True)
class _ConfiguredPerformanceSourceClient:
    performance_client: DownstreamJsonClient


@dataclass(frozen=True)
class _PerformanceSourceClientBlocker:
    code: str
    performance_base_url_configured: bool = False


@dataclass(frozen=True)
class _ConfiguredManageSourceClient:
    manage_client: DownstreamJsonClient


@dataclass(frozen=True)
class _ManageSourceClientBlocker:
    code: str
    manage_base_url_configured: bool = False


@dataclass(frozen=True)
class _ConfiguredAdviseSourceClient:
    advise_client: DownstreamJsonClient


@dataclass(frozen=True)
class _AdviseSourceClientBlocker:
    code: str
    advise_base_url_configured: bool = False


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
    adapter = _build_configured_core_source_adapter_from_environment()
    if isinstance(adapter, _CoreSourceAdapterBlocker):
        return CoreHighCashSourceRuntimeBlocker(
            adapter.code,
            core_base_url_configured=adapter.code != "lotus_core_base_url_not_configured",
            core_query_base_url_configured=adapter.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                adapter.core_query_control_plane_base_url_configured
            ),
        )
    return CoreHighCashSourceRuntime(
        core_source=adapter.core_source,
        core_base_url_configured=True,
        core_query_base_url_configured=adapter.core_query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            adapter.core_query_control_plane_base_url_configured
        ),
    )


def build_core_low_income_source_runtime_from_environment() -> (
    CoreLowIncomeSourceRuntime | CoreLowIncomeSourceRuntimeBlocker
):
    adapter = _build_configured_core_source_adapter_from_environment()
    if isinstance(adapter, _CoreSourceAdapterBlocker):
        return CoreLowIncomeSourceRuntimeBlocker(
            adapter.code,
            core_base_url_configured=adapter.code != "lotus_core_base_url_not_configured",
            core_query_base_url_configured=adapter.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                adapter.core_query_control_plane_base_url_configured
            ),
        )
    return CoreLowIncomeSourceRuntime(
        core_source=adapter.core_source,
        core_base_url_configured=True,
        core_query_base_url_configured=adapter.core_query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            adapter.core_query_control_plane_base_url_configured
        ),
    )


def build_core_benchmark_assignment_source_runtime_from_environment() -> (
    CoreBenchmarkAssignmentSourceRuntime | CoreBenchmarkAssignmentSourceRuntimeBlocker
):
    adapter = _build_configured_core_source_adapter_from_environment()
    if isinstance(adapter, _CoreSourceAdapterBlocker):
        return CoreBenchmarkAssignmentSourceRuntimeBlocker(
            adapter.code,
            core_base_url_configured=adapter.code != "lotus_core_base_url_not_configured",
            core_query_base_url_configured=adapter.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                adapter.core_query_control_plane_base_url_configured
            ),
        )
    return CoreBenchmarkAssignmentSourceRuntime(
        core_source=adapter.core_source,
        core_base_url_configured=True,
        core_query_base_url_configured=adapter.core_query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            adapter.core_query_control_plane_base_url_configured
        ),
    )


def build_core_bond_maturity_source_runtime_from_environment() -> (
    CoreBondMaturitySourceRuntime | CoreBondMaturitySourceRuntimeBlocker
):
    adapter = _build_configured_core_source_adapter_from_environment()
    if isinstance(adapter, _CoreSourceAdapterBlocker):
        return CoreBondMaturitySourceRuntimeBlocker(
            adapter.code,
            core_base_url_configured=adapter.code != "lotus_core_base_url_not_configured",
            core_query_base_url_configured=adapter.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                adapter.core_query_control_plane_base_url_configured
            ),
        )
    return CoreBondMaturitySourceRuntime(
        core_source=adapter.core_source,
        core_base_url_configured=True,
        core_query_base_url_configured=adapter.core_query_base_url_configured,
        core_query_control_plane_base_url_configured=(
            adapter.core_query_control_plane_base_url_configured
        ),
    )


def build_risk_concentration_source_runtime_from_environment() -> (
    RiskConcentrationSourceRuntime | RiskConcentrationSourceRuntimeBlocker
):
    configured_client = _build_configured_risk_source_client_from_environment()
    if isinstance(configured_client, _RiskSourceClientBlocker):
        return RiskConcentrationSourceRuntimeBlocker(
            configured_client.code,
            risk_base_url_configured=configured_client.risk_base_url_configured,
        )
    return RiskConcentrationSourceRuntime(
        risk_source=LotusRiskConcentrationSourceAdapter(configured_client.risk_client),
        risk_base_url_configured=True,
    )


def build_risk_volatility_source_runtime_from_environment() -> (
    RiskVolatilitySourceRuntime | RiskVolatilitySourceRuntimeBlocker
):
    configured_client = _build_configured_risk_source_client_from_environment()
    if isinstance(configured_client, _RiskSourceClientBlocker):
        return RiskVolatilitySourceRuntimeBlocker(
            configured_client.code,
            risk_base_url_configured=configured_client.risk_base_url_configured,
        )
    return RiskVolatilitySourceRuntime(
        risk_source=LotusRiskVolatilitySourceAdapter(configured_client.risk_client),
        risk_base_url_configured=True,
    )


def build_risk_drawdown_source_runtime_from_environment() -> (
    RiskDrawdownSourceRuntime | RiskDrawdownSourceRuntimeBlocker
):
    configured_client = _build_configured_risk_source_client_from_environment()
    if isinstance(configured_client, _RiskSourceClientBlocker):
        return RiskDrawdownSourceRuntimeBlocker(
            configured_client.code,
            risk_base_url_configured=configured_client.risk_base_url_configured,
        )
    return RiskDrawdownSourceRuntime(
        risk_source=LotusRiskDrawdownSourceAdapter(configured_client.risk_client),
        risk_base_url_configured=True,
    )


def build_performance_underperformance_source_runtime_from_environment() -> (
    PerformanceUnderperformanceSourceRuntime | PerformanceUnderperformanceSourceRuntimeBlocker
):
    configured_client = _build_configured_performance_source_client_from_environment()
    if isinstance(configured_client, _PerformanceSourceClientBlocker):
        return PerformanceUnderperformanceSourceRuntimeBlocker(
            configured_client.code,
            performance_base_url_configured=configured_client.performance_base_url_configured,
        )
    return PerformanceUnderperformanceSourceRuntime(
        performance_source=LotusPerformanceUnderperformanceSourceAdapter(
            configured_client.performance_client
        ),
        performance_base_url_configured=True,
    )


def build_manage_mandate_health_source_runtime_from_environment() -> (
    ManageMandateHealthSourceRuntime | ManageMandateHealthSourceRuntimeBlocker
):
    configured_client = _build_configured_manage_source_client_from_environment()
    if isinstance(configured_client, _ManageSourceClientBlocker):
        return ManageMandateHealthSourceRuntimeBlocker(
            configured_client.code,
            manage_base_url_configured=configured_client.manage_base_url_configured,
        )
    return ManageMandateHealthSourceRuntime(
        manage_source=LotusManageMandateHealthSourceAdapter(configured_client.manage_client),
        manage_base_url_configured=True,
    )


def build_advise_policy_evaluation_source_runtime_from_environment() -> (
    AdvisePolicyEvaluationSourceRuntime | AdvisePolicyEvaluationSourceRuntimeBlocker
):
    configured_client = _build_configured_advise_source_client_from_environment()
    if isinstance(configured_client, _AdviseSourceClientBlocker):
        return AdvisePolicyEvaluationSourceRuntimeBlocker(
            configured_client.code,
            advise_base_url_configured=configured_client.advise_base_url_configured,
        )
    return AdvisePolicyEvaluationSourceRuntime(
        advise_source=LotusAdvisePolicyEvaluationSourceAdapter(configured_client.advise_client),
        advise_base_url_configured=True,
    )


def _build_configured_risk_source_client_from_environment() -> (
    _ConfiguredRiskSourceClient | _RiskSourceClientBlocker
):
    risk_base_url = os.getenv(RISK_BASE_URL_ENV, "").strip()
    if not risk_base_url:
        return _RiskSourceClientBlocker("lotus_risk_base_url_not_configured")
    try:
        risk_config = _risk_source_client_config(risk_base_url)
    except DownstreamClientConfigurationError:
        return _RiskSourceClientBlocker(
            "lotus_risk_base_url_invalid",
            risk_base_url_configured=True,
        )
    return _ConfiguredRiskSourceClient(risk_client=DownstreamJsonClient(risk_config))


def _build_configured_performance_source_client_from_environment() -> (
    _ConfiguredPerformanceSourceClient | _PerformanceSourceClientBlocker
):
    performance_base_url = os.getenv(PERFORMANCE_BASE_URL_ENV, "").strip()
    if not performance_base_url:
        return _PerformanceSourceClientBlocker("lotus_performance_base_url_not_configured")
    try:
        performance_config = _performance_source_client_config(performance_base_url)
    except DownstreamClientConfigurationError:
        return _PerformanceSourceClientBlocker(
            "lotus_performance_base_url_invalid",
            performance_base_url_configured=True,
        )
    return _ConfiguredPerformanceSourceClient(
        performance_client=DownstreamJsonClient(performance_config)
    )


def _build_configured_manage_source_client_from_environment() -> (
    _ConfiguredManageSourceClient | _ManageSourceClientBlocker
):
    manage_base_url = os.getenv(MANAGE_BASE_URL_ENV, "").strip()
    if not manage_base_url:
        return _ManageSourceClientBlocker("lotus_manage_base_url_not_configured")
    try:
        manage_config = _manage_source_client_config(manage_base_url)
    except DownstreamClientConfigurationError:
        return _ManageSourceClientBlocker(
            "lotus_manage_base_url_invalid",
            manage_base_url_configured=True,
        )
    return _ConfiguredManageSourceClient(manage_client=DownstreamJsonClient(manage_config))


def _build_configured_advise_source_client_from_environment() -> (
    _ConfiguredAdviseSourceClient | _AdviseSourceClientBlocker
):
    advise_base_url = os.getenv(ADVISE_BASE_URL_ENV, "").strip()
    if not advise_base_url:
        return _AdviseSourceClientBlocker("lotus_advise_base_url_not_configured")
    try:
        advise_config = _advise_source_client_config(advise_base_url)
    except DownstreamClientConfigurationError:
        return _AdviseSourceClientBlocker(
            "lotus_advise_base_url_invalid",
            advise_base_url_configured=True,
        )
    return _ConfiguredAdviseSourceClient(advise_client=DownstreamJsonClient(advise_config))


def _build_configured_core_source_adapter_from_environment() -> (
    _ConfiguredCoreSourceAdapter | _CoreSourceAdapterBlocker
):
    core_source_urls = core_source_runtime_urls_from_environment()
    if not core_source_urls.fully_configured:
        return _CoreSourceAdapterBlocker(
            "lotus_core_base_url_not_configured",
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
    try:
        query_config, query_control_plane_config = _core_source_client_configs(core_source_urls)
    except DownstreamClientConfigurationError:
        return _CoreSourceAdapterBlocker(
            "lotus_core_base_url_invalid",
            core_query_base_url_configured=core_source_urls.query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                core_source_urls.query_control_plane_base_url_configured
            ),
        )
    return _ConfiguredCoreSourceAdapter(
        core_source=LotusCoreHighCashSourceAdapter(
            query_client=DownstreamJsonClient(query_config),
            query_control_plane_client=DownstreamJsonClient(query_control_plane_config),
        ),
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
    max_connections = _positive_int_env(
        SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
        default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
    )
    max_keepalive_connections = _positive_int_env(
        SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
        default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
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
            dependency="lotus-core-query",
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
            dependency="lotus-core-control",
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


def _risk_source_client_config(risk_base_url: str) -> DownstreamClientConfig:
    return DownstreamClientConfig(
        base_url=risk_base_url,
        dependency="lotus-risk",
        timeout_seconds=_positive_float_env(
            RISK_TIMEOUT_SECONDS_ENV, default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS
        ),
        max_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
        ),
        max_keepalive_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
        ),
        pool_timeout_seconds=_positive_float_env(
            SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, default=2.0
        ),
        retry_max_attempts=_positive_int_env(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, default=1),
        retry_initial_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
        ),
        retry_max_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
        ),
        retry_post_without_idempotency=True,
    )


def _performance_source_client_config(performance_base_url: str) -> DownstreamClientConfig:
    return DownstreamClientConfig(
        base_url=performance_base_url,
        dependency="lotus-performance",
        timeout_seconds=_positive_float_env(
            PERFORMANCE_TIMEOUT_SECONDS_ENV, default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS
        ),
        max_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
        ),
        max_keepalive_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
        ),
        pool_timeout_seconds=_positive_float_env(
            SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, default=2.0
        ),
        retry_max_attempts=_positive_int_env(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, default=1),
        retry_initial_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
        ),
        retry_max_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
        ),
        retry_post_without_idempotency=True,
    )


def _manage_source_client_config(manage_base_url: str) -> DownstreamClientConfig:
    return DownstreamClientConfig(
        base_url=manage_base_url,
        dependency="lotus-manage",
        timeout_seconds=_positive_float_env(
            MANAGE_TIMEOUT_SECONDS_ENV, default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS
        ),
        max_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
        ),
        max_keepalive_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
        ),
        pool_timeout_seconds=_positive_float_env(
            SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, default=2.0
        ),
        retry_max_attempts=_positive_int_env(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, default=1),
        retry_initial_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
        ),
        retry_max_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
        ),
        retry_post_without_idempotency=True,
    )


def _advise_source_client_config(advise_base_url: str) -> DownstreamClientConfig:
    return DownstreamClientConfig(
        base_url=advise_base_url,
        dependency="lotus-advise",
        timeout_seconds=_positive_float_env(
            ADVISE_TIMEOUT_SECONDS_ENV, default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS
        ),
        max_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
        ),
        max_keepalive_connections=_positive_int_env(
            SOURCE_INGESTION_MAX_KEEPALIVE_CONNECTIONS_ENV,
            default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
        ),
        pool_timeout_seconds=_positive_float_env(
            SOURCE_INGESTION_POOL_TIMEOUT_SECONDS_ENV, default=2.0
        ),
        retry_max_attempts=_positive_int_env(SOURCE_INGESTION_RETRY_MAX_ATTEMPTS_ENV, default=1),
        retry_initial_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
        ),
        retry_max_backoff_seconds=_non_negative_float_env(
            SOURCE_INGESTION_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
        ),
        retry_post_without_idempotency=True,
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _timeout_seconds_from_environment() -> float:
    return _positive_float_env(
        TIMEOUT_SECONDS_ENV,
        default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
    )


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
