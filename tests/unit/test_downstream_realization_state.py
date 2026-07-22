from __future__ import annotations

import pytest

from app.runtime.downstream_realization_state import (
    ADVISE_ACTOR_ID_ENV,
    ADVISE_BASE_URL_ENV,
    ADVISE_CAPABILITIES_ENV,
    ADVISE_LEGAL_ENTITY_CODE_ENV,
    ADVISE_ROLE_ENV,
    ADVISE_SERVICE_IDENTITY_ENV,
    ADVISE_SUBMIT_PATH_ENV,
    ADVISE_TENANT_ID_ENV,
    MAX_CONNECTIONS_ENV,
    MAX_KEEPALIVE_CONNECTIONS_ENV,
    MANAGE_BASE_URL_ENV,
    MANAGE_ACTOR_ID_ENV,
    MANAGE_CAPABILITIES_ENV,
    MANAGE_ROLE_ENV,
    MANAGE_SERVICE_IDENTITY_ENV,
    MANAGE_SUBMIT_PATH_ENV,
    MANAGE_TENANT_ID_ENV,
    POOL_TIMEOUT_SECONDS_ENV,
    REPORT_BASE_URL_ENV,
    REPORT_ACTOR_ID_ENV,
    REPORT_CALLER_APPLICATION_ENV,
    REPORT_OUTPUT_FORMATS_ENV,
    REPORT_REGION_ENV,
    REPORT_SUBMIT_PATH_ENV,
    REPORT_TENANT_ID_ENV,
    RETRY_INITIAL_BACKOFF_SECONDS_ENV,
    RETRY_MAX_ATTEMPTS_ENV,
    RETRY_MAX_BACKOFF_SECONDS_ENV,
    TIMEOUT_SECONDS_ENV,
    ConversionRealizationClients,
    DownstreamRealizationClientsUnavailableError,
    close_downstream_realization_clients,
    get_conversion_realization_clients,
    get_report_evidence_pack_realization_client,
    reset_downstream_realization_clients_for_tests,
)
from app.runtime.settings import RUNTIME_PROFILE_ENV


@pytest.fixture(autouse=True)
def reset_clients() -> None:
    reset_downstream_realization_clients_for_tests(conversion_clients=None, report_client=None)


def test_conversion_realization_clients_are_built_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_conversion_env(monkeypatch)

    clients = get_conversion_realization_clients()

    assert isinstance(clients, ConversionRealizationClients)
    assert get_conversion_realization_clients() is clients


def test_report_realization_client_is_built_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_report_env(monkeypatch)

    report_client = get_report_evidence_pack_realization_client()

    assert get_report_evidence_pack_realization_client() is report_client


@pytest.mark.parametrize(
    "environment_name",
    [
        REPORT_ACTOR_ID_ENV,
        REPORT_CALLER_APPLICATION_ENV,
        REPORT_TENANT_ID_ENV,
        REPORT_REGION_ENV,
        REPORT_OUTPUT_FORMATS_ENV,
    ],
)
def test_missing_report_service_context_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    configure_report_env(monkeypatch)
    monkeypatch.delenv(environment_name, raising=False)

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{environment_name} is not configured",
    ):
        get_report_evidence_pack_realization_client()


def test_report_service_context_fixture_is_rejected_outside_local_and_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_report_env(monkeypatch)
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "production")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="restricted to local and test",
    ):
        get_report_evidence_pack_realization_client()


def test_invalid_report_adapter_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_report_env(monkeypatch)
    monkeypatch.setenv(REPORT_BASE_URL_ENV, "not-a-url")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="absolute HTTP",
    ):
        get_report_evidence_pack_realization_client()


@pytest.mark.parametrize(
    ("environment_name", "environment_value", "message"),
    [
        (REPORT_TENANT_ID_ENV, "local-development", "tenant_id must be 'tenant-sg'"),
        (REPORT_REGION_ENV, "local", "region must be 'APAC'"),
        (REPORT_OUTPUT_FORMATS_ENV, "pdf", "requested_output_formats must be 'json'"),
    ],
)
def test_report_service_context_fixture_rejects_unrecognized_owner_scope(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    environment_value: str,
    message: str,
) -> None:
    configure_report_env(monkeypatch)
    monkeypatch.setenv(environment_name, environment_value)

    with pytest.raises(DownstreamRealizationClientsUnavailableError, match=message):
        get_report_evidence_pack_realization_client()


def test_malformed_report_output_formats_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_report_env(monkeypatch)
    monkeypatch.setenv(REPORT_OUTPUT_FORMATS_ENV, "json, ")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{REPORT_OUTPUT_FORMATS_ENV} must be a non-empty CSV value",
    ):
        get_report_evidence_pack_realization_client()


def test_missing_downstream_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ADVISE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(ADVISE_SUBMIT_PATH_ENV, "/advisory/idea-intake")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{ADVISE_BASE_URL_ENV} is not configured",
    ):
        get_conversion_realization_clients()


@pytest.mark.parametrize(
    "environment_name",
    [
        ADVISE_ACTOR_ID_ENV,
        ADVISE_ROLE_ENV,
        ADVISE_TENANT_ID_ENV,
        ADVISE_LEGAL_ENTITY_CODE_ENV,
        ADVISE_SERVICE_IDENTITY_ENV,
        ADVISE_CAPABILITIES_ENV,
    ],
)
def test_missing_advise_service_context_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.delenv(environment_name, raising=False)

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{environment_name} is not configured",
    ):
        get_conversion_realization_clients()


@pytest.mark.parametrize(
    "environment_name",
    [
        MANAGE_ACTOR_ID_ENV,
        MANAGE_ROLE_ENV,
        MANAGE_TENANT_ID_ENV,
        MANAGE_SERVICE_IDENTITY_ENV,
        MANAGE_CAPABILITIES_ENV,
    ],
)
def test_missing_manage_service_context_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.delenv(environment_name, raising=False)

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{environment_name} is not configured",
    ):
        get_conversion_realization_clients()


def test_manage_service_context_fixture_is_rejected_outside_local_and_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "production")
    monkeypatch.setattr(
        "app.runtime.downstream_realization_state._ADVISE_SERVICE_CONTEXT_FIXTURE_PROFILES",
        {"production"},
    )

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="Manage realization service-context fixture is restricted to local and test",
    ):
        get_conversion_realization_clients()


def test_invalid_manage_adapter_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(MANAGE_BASE_URL_ENV, "not-a-url")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="absolute HTTP",
    ):
        get_conversion_realization_clients()


def test_advise_service_context_fixture_is_rejected_outside_local_and_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "production")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="restricted to local and test",
    ):
        get_conversion_realization_clients()


def test_invalid_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "not-numeric")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{TIMEOUT_SECONDS_ENV} must be numeric",
    ):
        get_conversion_realization_clients()


def test_invalid_connection_limits_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(MAX_CONNECTIONS_ENV, "0")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{MAX_CONNECTIONS_ENV} must be positive",
    ):
        get_conversion_realization_clients()


def test_non_integer_connection_limits_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(MAX_CONNECTIONS_ENV, "not-an-integer")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{MAX_CONNECTIONS_ENV} must be an integer",
    ):
        get_conversion_realization_clients()


def test_keepalive_limit_above_connection_limit_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(MAX_CONNECTIONS_ENV, "2")
    monkeypatch.setenv(MAX_KEEPALIVE_CONNECTIONS_ENV, "3")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="max_keepalive_connections must not exceed max_connections",
    ):
        get_conversion_realization_clients()


def test_invalid_pool_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(POOL_TIMEOUT_SECONDS_ENV, "0")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match=f"{POOL_TIMEOUT_SECONDS_ENV} must be positive",
    ):
        get_conversion_realization_clients()


@pytest.mark.parametrize(
    ("env_name", "env_value", "message"),
    [
        (RETRY_MAX_ATTEMPTS_ENV, "0", f"{RETRY_MAX_ATTEMPTS_ENV} must be positive"),
        (
            RETRY_INITIAL_BACKOFF_SECONDS_ENV,
            "-0.01",
            f"{RETRY_INITIAL_BACKOFF_SECONDS_ENV} must not be negative",
        ),
        (
            RETRY_MAX_BACKOFF_SECONDS_ENV,
            "slow",
            f"{RETRY_MAX_BACKOFF_SECONDS_ENV} must be numeric",
        ),
    ],
)
def test_invalid_retry_policy_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
    message: str,
) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(DownstreamRealizationClientsUnavailableError, match=message):
        get_conversion_realization_clients()


def test_invalid_submit_path_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_conversion_env(monkeypatch)
    monkeypatch.setenv(ADVISE_SUBMIT_PATH_ENV, "relative-path")

    with pytest.raises(
        DownstreamRealizationClientsUnavailableError,
        match="submit_path must start",
    ):
        get_conversion_realization_clients()


def test_reset_closes_cached_clients() -> None:
    class CloseAwareClient:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    advise = CloseAwareClient()
    manage = CloseAwareClient()
    report = CloseAwareClient()

    reset_downstream_realization_clients_for_tests(
        conversion_clients=ConversionRealizationClients(
            advise_client=advise,  # type: ignore[arg-type]
            manage_client=manage,  # type: ignore[arg-type]
        ),
        report_client=report,  # type: ignore[arg-type]
    )
    reset_downstream_realization_clients_for_tests(conversion_clients=None, report_client=None)

    assert advise.closed is True
    assert manage.closed is True
    assert report.closed is True


def test_close_downstream_realization_clients_is_idempotent() -> None:
    close_downstream_realization_clients()
    close_downstream_realization_clients()


def test_reset_ignores_clients_without_close_methods() -> None:
    reset_downstream_realization_clients_for_tests(
        conversion_clients=ConversionRealizationClients(
            advise_client=object(),  # type: ignore[arg-type]
            manage_client=object(),  # type: ignore[arg-type]
        ),
        report_client=object(),  # type: ignore[arg-type]
    )
    reset_downstream_realization_clients_for_tests(conversion_clients=None, report_client=None)


def configure_conversion_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "local")
    monkeypatch.setenv(ADVISE_BASE_URL_ENV, "https://advise.example")
    monkeypatch.setenv(ADVISE_SUBMIT_PATH_ENV, "/advisory/idea-intake")
    monkeypatch.setenv(ADVISE_ACTOR_ID_ENV, "lotus-idea-local-development")
    monkeypatch.setenv(ADVISE_ROLE_ENV, "SERVICE")
    monkeypatch.setenv(ADVISE_TENANT_ID_ENV, "tenant-sg")
    monkeypatch.setenv(ADVISE_LEGAL_ENTITY_CODE_ENV, "SGPB")
    monkeypatch.setenv(ADVISE_SERVICE_IDENTITY_ENV, "lotus-idea-local-development")
    monkeypatch.setenv(ADVISE_CAPABILITIES_ENV, "advisory.idea_proposal_intake.accept")
    monkeypatch.setenv(MANAGE_BASE_URL_ENV, "https://manage.example")
    monkeypatch.setenv(MANAGE_SUBMIT_PATH_ENV, "/manage/idea-intake")
    monkeypatch.setenv(MANAGE_ACTOR_ID_ENV, "lotus-idea-local-development")
    monkeypatch.setenv(MANAGE_ROLE_ENV, "service")
    monkeypatch.setenv(MANAGE_TENANT_ID_ENV, "local-development")
    monkeypatch.setenv(MANAGE_SERVICE_IDENTITY_ENV, "lotus-idea-local-development")
    monkeypatch.setenv(MANAGE_CAPABILITIES_ENV, "manage.write")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "1.25")


def configure_report_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "local")
    monkeypatch.setenv(REPORT_BASE_URL_ENV, "https://report.example")
    monkeypatch.setenv(REPORT_SUBMIT_PATH_ENV, "/reports/idea-evidence-packs/materializations")
    monkeypatch.setenv(REPORT_ACTOR_ID_ENV, "lotus-idea-local-development")
    monkeypatch.setenv(REPORT_CALLER_APPLICATION_ENV, "lotus-idea")
    monkeypatch.setenv(REPORT_TENANT_ID_ENV, "tenant-sg")
    monkeypatch.setenv(REPORT_REGION_ENV, "APAC")
    monkeypatch.setenv(REPORT_OUTPUT_FORMATS_ENV, "json")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "1.25")
