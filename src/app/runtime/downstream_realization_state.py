from __future__ import annotations

import os
from dataclasses import dataclass

from app.contracts.operational_limits import (
    DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
    DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
)
from app.domain import SourceSystem
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpAdviseProposalRealizationClient,
    HttpManageActionRealizationClient,
    HttpReportEvidencePackMaterializationClient,
    ManageRealizationServiceContext,
    ReportRealizationServiceContext,
)
from app.ports.downstream_realization import (
    AdviseProposalRealizationClient,
    ManageActionRealizationClient,
    ReportEvidencePackMaterializationClient,
)
from app.runtime.settings import RuntimeConfigurationError, RuntimeProfile, load_runtime_settings

ADVISE_BASE_URL_ENV = "LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL"
ADVISE_SUBMIT_PATH_ENV = "LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH"
MANAGE_BASE_URL_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL"
MANAGE_SUBMIT_PATH_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH"
REPORT_BASE_URL_ENV = "LOTUS_IDEA_REPORT_REALIZATION_BASE_URL"
REPORT_SUBMIT_PATH_ENV = "LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS"
MAX_CONNECTIONS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_CONNECTIONS"
MAX_KEEPALIVE_CONNECTIONS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_MAX_KEEPALIVE_CONNECTIONS"
POOL_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_POOL_TIMEOUT_SECONDS"
RETRY_MAX_ATTEMPTS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_ATTEMPTS"
RETRY_INITIAL_BACKOFF_SECONDS_ENV = (
    "LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_INITIAL_BACKOFF_SECONDS"
)
RETRY_MAX_BACKOFF_SECONDS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_RETRY_MAX_BACKOFF_SECONDS"
MANAGE_ACTOR_ID_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_ACTOR_ID"
MANAGE_ROLE_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_ROLE"
MANAGE_TENANT_ID_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_TENANT_ID"
MANAGE_SERVICE_IDENTITY_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_SERVICE_IDENTITY"
MANAGE_CAPABILITIES_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_CAPABILITIES"
REPORT_ACTOR_ID_ENV = "LOTUS_IDEA_REPORT_REALIZATION_ACTOR_ID"
REPORT_CALLER_APPLICATION_ENV = "LOTUS_IDEA_REPORT_REALIZATION_CALLER_APPLICATION"
REPORT_TENANT_ID_ENV = "LOTUS_IDEA_REPORT_REALIZATION_TENANT_ID"
REPORT_REGION_ENV = "LOTUS_IDEA_REPORT_REALIZATION_REGION"
REPORT_OUTPUT_FORMATS_ENV = "LOTUS_IDEA_REPORT_REALIZATION_OUTPUT_FORMATS"
_MANAGE_SERVICE_CONTEXT_FIXTURE_PROFILES = {RuntimeProfile.LOCAL, RuntimeProfile.TEST}
_REPORT_SERVICE_CONTEXT_FIXTURE_PROFILES = {RuntimeProfile.LOCAL, RuntimeProfile.TEST}
_REPORT_LOCAL_TEST_FIXTURE_TENANT_ID = "tenant-sg"
_REPORT_LOCAL_TEST_FIXTURE_REGION = "APAC"
_REPORT_LOCAL_TEST_FIXTURE_OUTPUT_FORMATS = ("json",)


class DownstreamRealizationClientsUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConversionRealizationClients:
    advise_client: AdviseProposalRealizationClient
    manage_client: ManageActionRealizationClient


_CONVERSION_CLIENTS: ConversionRealizationClients | None = None
_REPORT_CLIENT: ReportEvidencePackMaterializationClient | None = None


def get_conversion_realization_clients() -> ConversionRealizationClients:
    global _CONVERSION_CLIENTS
    if _CONVERSION_CLIENTS is None:
        _CONVERSION_CLIENTS = ConversionRealizationClients(
            advise_client=HttpAdviseProposalRealizationClient(
                _adapter_config(
                    base_url_env=ADVISE_BASE_URL_ENV,
                    submit_path_env=ADVISE_SUBMIT_PATH_ENV,
                    source_authority=SourceSystem.LOTUS_ADVISE,
                )
            ),
            manage_client=HttpManageActionRealizationClient(
                _manage_adapter_config(
                    base_url_env=MANAGE_BASE_URL_ENV,
                    submit_path_env=MANAGE_SUBMIT_PATH_ENV,
                    source_authority=SourceSystem.LOTUS_MANAGE,
                )
            ),
        )
    return _CONVERSION_CLIENTS


def get_report_evidence_pack_realization_client() -> ReportEvidencePackMaterializationClient:
    global _REPORT_CLIENT
    if _REPORT_CLIENT is None:
        _REPORT_CLIENT = HttpReportEvidencePackMaterializationClient(
            _report_adapter_config(
                base_url_env=REPORT_BASE_URL_ENV,
                submit_path_env=REPORT_SUBMIT_PATH_ENV,
                source_authority=SourceSystem.LOTUS_REPORT,
            )
        )
    return _REPORT_CLIENT


def reset_downstream_realization_clients_for_tests(
    *,
    conversion_clients: ConversionRealizationClients | None = None,
    report_client: ReportEvidencePackMaterializationClient | None = None,
) -> None:
    global _CONVERSION_CLIENTS, _REPORT_CLIENT
    close_downstream_realization_clients()
    _CONVERSION_CLIENTS = conversion_clients
    _REPORT_CLIENT = report_client


def close_downstream_realization_clients() -> None:
    global _CONVERSION_CLIENTS, _REPORT_CLIENT
    if _CONVERSION_CLIENTS is not None:
        _close_if_supported(_CONVERSION_CLIENTS.advise_client)
        _close_if_supported(_CONVERSION_CLIENTS.manage_client)
    if _REPORT_CLIENT is not None:
        _close_if_supported(_REPORT_CLIENT)
    _CONVERSION_CLIENTS = None
    _REPORT_CLIENT = None


def _adapter_config(
    *,
    base_url_env: str,
    submit_path_env: str,
    source_authority: SourceSystem,
) -> DownstreamRealizationAdapterConfig:
    base_url = _required_env(base_url_env)
    submit_path = _required_env(submit_path_env)
    try:
        return DownstreamRealizationAdapterConfig(
            base_url=base_url,
            submit_path=submit_path,
            source_authority=source_authority,
            timeout_seconds=_timeout_seconds(),
            max_connections=_positive_int_env(
                MAX_CONNECTIONS_ENV, default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS
            ),
            max_keepalive_connections=_positive_int_env(
                MAX_KEEPALIVE_CONNECTIONS_ENV,
                default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
            ),
            pool_timeout_seconds=_positive_float_env(POOL_TIMEOUT_SECONDS_ENV, default=2.0),
            retry_max_attempts=_positive_int_env(RETRY_MAX_ATTEMPTS_ENV, default=1),
            retry_initial_backoff_seconds=_non_negative_float_env(
                RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
            ),
            retry_max_backoff_seconds=_non_negative_float_env(
                RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
            ),
        )
    except DownstreamRealizationConfigurationError as exc:
        raise DownstreamRealizationClientsUnavailableError(str(exc)) from exc


def _manage_adapter_config(
    *,
    base_url_env: str,
    submit_path_env: str,
    source_authority: SourceSystem,
) -> DownstreamRealizationAdapterConfig:
    try:
        _require_manage_service_context_fixture_profile()
        service_context = ManageRealizationServiceContext(
            actor_id=_required_env(MANAGE_ACTOR_ID_ENV),
            role=_required_env(MANAGE_ROLE_ENV),
            tenant_id=_required_env(MANAGE_TENANT_ID_ENV),
            service_identity=_required_env(MANAGE_SERVICE_IDENTITY_ENV),
            capabilities=_required_env(MANAGE_CAPABILITIES_ENV),
        )
        return DownstreamRealizationAdapterConfig(
            base_url=_required_env(base_url_env),
            submit_path=_required_env(submit_path_env),
            source_authority=source_authority,
            timeout_seconds=_timeout_seconds(),
            max_connections=_positive_int_env(
                MAX_CONNECTIONS_ENV, default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS
            ),
            max_keepalive_connections=_positive_int_env(
                MAX_KEEPALIVE_CONNECTIONS_ENV,
                default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
            ),
            pool_timeout_seconds=_positive_float_env(POOL_TIMEOUT_SECONDS_ENV, default=2.0),
            retry_max_attempts=_positive_int_env(RETRY_MAX_ATTEMPTS_ENV, default=1),
            retry_initial_backoff_seconds=_non_negative_float_env(
                RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
            ),
            retry_max_backoff_seconds=_non_negative_float_env(
                RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
            ),
            manage_service_context=service_context,
        )
    except (DownstreamRealizationConfigurationError, RuntimeConfigurationError) as exc:
        raise DownstreamRealizationClientsUnavailableError(str(exc)) from exc


def _report_adapter_config(
    *,
    base_url_env: str,
    submit_path_env: str,
    source_authority: SourceSystem,
) -> DownstreamRealizationAdapterConfig:
    try:
        _require_report_service_context_fixture_profile()
        service_context = ReportRealizationServiceContext(
            actor_id=_required_env(REPORT_ACTOR_ID_ENV),
            caller_application=_required_env(REPORT_CALLER_APPLICATION_ENV),
            tenant_id=_required_env(REPORT_TENANT_ID_ENV),
            region=_required_env(REPORT_REGION_ENV),
            requested_output_formats=_csv_env(REPORT_OUTPUT_FORMATS_ENV),
        )
        _require_report_service_context_fixture_values(service_context)
        return DownstreamRealizationAdapterConfig(
            base_url=_required_env(base_url_env),
            submit_path=_required_env(submit_path_env),
            source_authority=source_authority,
            timeout_seconds=_timeout_seconds(),
            max_connections=_positive_int_env(
                MAX_CONNECTIONS_ENV, default=DEFAULT_DEPENDENCY_MAX_CONNECTIONS
            ),
            max_keepalive_connections=_positive_int_env(
                MAX_KEEPALIVE_CONNECTIONS_ENV,
                default=DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
            ),
            pool_timeout_seconds=_positive_float_env(POOL_TIMEOUT_SECONDS_ENV, default=2.0),
            retry_max_attempts=_positive_int_env(RETRY_MAX_ATTEMPTS_ENV, default=1),
            retry_initial_backoff_seconds=_non_negative_float_env(
                RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
            ),
            retry_max_backoff_seconds=_non_negative_float_env(
                RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
            ),
            report_service_context=service_context,
        )
    except (DownstreamRealizationConfigurationError, RuntimeConfigurationError) as exc:
        raise DownstreamRealizationClientsUnavailableError(str(exc)) from exc


def _require_manage_service_context_fixture_profile() -> None:
    profile = load_runtime_settings().runtime_profile
    if profile not in _MANAGE_SERVICE_CONTEXT_FIXTURE_PROFILES:
        raise DownstreamRealizationClientsUnavailableError(
            "Manage realization service-context fixture is restricted to local and test "
            "runtime profiles until trusted service identity is available."
        )


def _require_report_service_context_fixture_profile() -> None:
    profile = load_runtime_settings().runtime_profile
    if profile not in _REPORT_SERVICE_CONTEXT_FIXTURE_PROFILES:
        raise DownstreamRealizationClientsUnavailableError(
            "Report realization service-context fixture is restricted to local and test "
            "runtime profiles until trusted service identity is available."
        )


def _require_report_service_context_fixture_values(
    service_context: ReportRealizationServiceContext,
) -> None:
    if service_context.tenant_id != _REPORT_LOCAL_TEST_FIXTURE_TENANT_ID:
        raise DownstreamRealizationClientsUnavailableError(
            "Report realization local/test fixture tenant_id must be "
            f"'{_REPORT_LOCAL_TEST_FIXTURE_TENANT_ID}'."
        )
    if service_context.region != _REPORT_LOCAL_TEST_FIXTURE_REGION:
        raise DownstreamRealizationClientsUnavailableError(
            "Report realization local/test fixture region must be "
            f"'{_REPORT_LOCAL_TEST_FIXTURE_REGION}'."
        )
    if service_context.requested_output_formats != _REPORT_LOCAL_TEST_FIXTURE_OUTPUT_FORMATS:
        raise DownstreamRealizationClientsUnavailableError(
            "Report realization local/test fixture requested_output_formats must be 'json'."
        )


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise DownstreamRealizationClientsUnavailableError(f"{name} is not configured")
    return value


def _csv_env(name: str) -> tuple[str, ...]:
    value = _required_env(name)
    values = tuple(item.strip().lower() for item in value.split(","))
    if not values or any(not item for item in values):
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be a non-empty CSV value")
    return values


def _timeout_seconds() -> float:
    return _positive_float_env(TIMEOUT_SECONDS_ENV, default=DEFAULT_DEPENDENCY_TIMEOUT_SECONDS)


def _positive_float_env(name: str, *, default: float) -> float:
    raw_timeout = os.getenv(name, str(default)).strip()
    try:
        duration_seconds = float(raw_timeout)
    except ValueError as exc:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be numeric") from exc
    if duration_seconds <= 0:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be positive")
    return duration_seconds


def _non_negative_float_env(name: str, *, default: float) -> float:
    raw_duration = os.getenv(name, str(default)).strip()
    try:
        duration_seconds = float(raw_duration)
    except ValueError as exc:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be numeric") from exc
    if duration_seconds < 0:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must not be negative")
    return duration_seconds


def _positive_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be an integer") from exc
    if value <= 0:
        raise DownstreamRealizationClientsUnavailableError(f"{name} must be positive")
    return value


def _close_if_supported(client: object) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()
