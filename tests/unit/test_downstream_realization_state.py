from __future__ import annotations

import pytest

from app.runtime.downstream_realization_state import (
    ADVISE_BASE_URL_ENV,
    ADVISE_SUBMIT_PATH_ENV,
    MAX_CONNECTIONS_ENV,
    MAX_KEEPALIVE_CONNECTIONS_ENV,
    MANAGE_BASE_URL_ENV,
    MANAGE_SUBMIT_PATH_ENV,
    POOL_TIMEOUT_SECONDS_ENV,
    REPORT_BASE_URL_ENV,
    REPORT_SUBMIT_PATH_ENV,
    TIMEOUT_SECONDS_ENV,
    ConversionRealizationClients,
    DownstreamRealizationClientsUnavailableError,
    close_downstream_realization_clients,
    get_conversion_realization_clients,
    get_report_evidence_pack_realization_client,
    reset_downstream_realization_clients_for_tests,
)


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
    monkeypatch.setenv(REPORT_BASE_URL_ENV, "https://report.example")
    monkeypatch.setenv(REPORT_SUBMIT_PATH_ENV, "/reports/idea-evidence-intake")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "1.25")

    report_client = get_report_evidence_pack_realization_client()

    assert get_report_evidence_pack_realization_client() is report_client


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


def configure_conversion_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADVISE_BASE_URL_ENV, "https://advise.example")
    monkeypatch.setenv(ADVISE_SUBMIT_PATH_ENV, "/advisory/idea-intake")
    monkeypatch.setenv(MANAGE_BASE_URL_ENV, "https://manage.example")
    monkeypatch.setenv(MANAGE_SUBMIT_PATH_ENV, "/manage/idea-intake")
    monkeypatch.setenv(TIMEOUT_SECONDS_ENV, "1.25")
