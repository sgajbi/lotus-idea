from __future__ import annotations

import os
from dataclasses import dataclass

from app.domain import SourceSystem
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpAdviseProposalRealizationClient,
    HttpManageActionRealizationClient,
    HttpReportEvidencePackMaterializationClient,
)
from app.ports.downstream_realization import (
    AdviseProposalRealizationClient,
    ManageActionRealizationClient,
    ReportEvidencePackMaterializationClient,
)

ADVISE_BASE_URL_ENV = "LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL"
ADVISE_SUBMIT_PATH_ENV = "LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH"
MANAGE_BASE_URL_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL"
MANAGE_SUBMIT_PATH_ENV = "LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH"
REPORT_BASE_URL_ENV = "LOTUS_IDEA_REPORT_REALIZATION_BASE_URL"
REPORT_SUBMIT_PATH_ENV = "LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH"
TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS"


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
                _adapter_config(
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
            _adapter_config(
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
    _CONVERSION_CLIENTS = conversion_clients
    _REPORT_CLIENT = report_client


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
        )
    except DownstreamRealizationConfigurationError as exc:
        raise DownstreamRealizationClientsUnavailableError(str(exc)) from exc


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise DownstreamRealizationClientsUnavailableError(f"{name} is not configured")
    return value


def _timeout_seconds() -> float:
    raw_timeout = os.getenv(TIMEOUT_SECONDS_ENV, "2.0").strip()
    try:
        return float(raw_timeout)
    except ValueError as exc:
        raise DownstreamRealizationClientsUnavailableError(
            f"{TIMEOUT_SECONDS_ENV} must be numeric"
        ) from exc
