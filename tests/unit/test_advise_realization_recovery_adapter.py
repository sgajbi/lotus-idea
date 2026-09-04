from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.domain import SourceSystem
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpAdviseProposalRealizationClient,
)
from tests.unit.test_downstream_realization_adapters import (
    _advise_history_payload,
    advise_service_context,
    downstream_json_client,
    report_access_scope,
)


RECOVERY_PATH = (
    "/advisory/proposals/idea-intake/by-conversion-intent/{conversion_intent_id}/realization"
)


def test_advise_adapter_recovers_exact_owner_history_in_trusted_scope() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json=_advise_history_payload())

    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/proposals/idea-intake",
            recovery_history_path_template=RECOVERY_PATH,
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        ),
        client=downstream_json_client("https://advise.example", httpx.MockTransport(handler)),
    )

    history = adapter.load_proposal_realization_by_conversion_intent(
        conversion_intent_id="conversion-advise_proposal-001",
        access_scope=report_access_scope(),
        correlation_id="corr-recovery",
        trace_id="trace-recovery",
    )

    assert captured["path"] == RECOVERY_PATH.format(
        conversion_intent_id="conversion-advise_proposal-001"
    )
    assert captured["headers"]["x-portfolio-id"] == "PB_SG_GLOBAL_BAL_001"
    assert captured["headers"]["x-correlation-id"] == "corr-recovery"
    assert captured["headers"]["x-trace-id"] == "trace-recovery"
    # Identity binding against the requested conversion intent is enforced by
    # the application reconciliation boundary, not rewritten by the adapter.
    assert history.conversion_intent_id == "conversion-001"
    assert history.current_source_event_version == 2


@pytest.mark.parametrize(
    ("recovery_path_template", "message"),
    [
        ("advisory/{conversion_intent_id}", "start with '/'"),
        ("/advisory/history", "one {conversion_intent_id} placeholder"),
        (
            "/advisory/{conversion_intent_id}/{conversion_intent_id}",
            "one {conversion_intent_id} placeholder",
        ),
        ("/advisory/{conversion_intent_id}?debug=true", "query string or fragment"),
    ],
)
def test_advise_recovery_history_config_rejects_ambiguous_routes(
    recovery_path_template: str,
    message: str,
) -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match=message):
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/proposals/idea-intake",
            recovery_history_path_template=recovery_path_template,
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        )


def test_advise_recovery_reader_requires_configured_route_and_printable_identity() -> None:
    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/proposals/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        ),
        client=downstream_json_client(
            "https://advise.example",
            httpx.MockTransport(lambda _request: httpx.Response(500)),
        ),
    )

    with pytest.raises(
        DownstreamRealizationConfigurationError,
        match="recovery_history_path_template",
    ):
        adapter.load_proposal_realization_by_conversion_intent(
            conversion_intent_id="conversion-001",
            access_scope=report_access_scope(),
        )

    configured = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/proposals/idea-intake",
            recovery_history_path_template=RECOVERY_PATH,
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        ),
        client=downstream_json_client(
            "https://advise.example",
            httpx.MockTransport(lambda _request: httpx.Response(500)),
        ),
    )
    with pytest.raises(ValueError, match="conversion_intent_id is required"):
        configured.load_proposal_realization_by_conversion_intent(
            conversion_intent_id=" ",
            access_scope=report_access_scope(),
        )
