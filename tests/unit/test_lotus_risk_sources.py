from __future__ import annotations

from datetime import UTC, date, datetime
import json
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_risk_sources import LotusRiskConcentrationSourceAdapter
from app.ports.risk_sources import (
    RiskConcentrationEvidenceRequest,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_service": "lotus-risk",
        "input_mode": "stateful",
        "single_position_concentration": {
            "top_position_weight_current": 0.23014,
            "top_position_weight_proposed": 0.23014,
        },
        "issuer_concentration": {
            "top_issuer_weight_current": 0.245075,
            "top_issuer_weight_proposed": 0.245075,
            "coverage_status": "complete",
        },
        "metadata": {
            "as_of_date": "2026-06-21",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "generated_at": "2026-06-21T10:00:00Z",
            "request_fingerprint": "risk-concentration-fingerprint",
            "calculation_supportability": {
                "state": "ready",
                "reason": "calculation_complete",
                "freshness_bucket": "current",
            },
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusRiskConcentrationSourceAdapter:
    return LotusRiskConcentrationSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://risk.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://risk.example", transport=handler),
        )
    )


def _request() -> RiskConcentrationEvidenceRequest:
    return RiskConcentrationEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def test_lotus_risk_adapter_fetches_declared_concentration_source_product() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.method, str(request.url), body))
        assert request.headers["X-Correlation-Id"] == "corr-risk"
        assert request.headers["X-Trace-Id"] == "trace-risk"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_concentration_evidence(_request())

    assert evidence.top_position_weight_current is not None
    assert str(evidence.top_position_weight_current) == "0.23014"
    assert evidence.top_issuer_weight_current is not None
    assert str(evidence.top_issuer_weight_current) == "0.245075"
    assert evidence.issuer_coverage_status == "complete"
    assert evidence.concentration_ref is not None
    assert evidence.concentration_ref.product_id == "lotus-risk:ConcentrationRiskReport:v1"
    assert evidence.concentration_ref.route == "/analytics/risk/concentration"
    assert evidence.concentration_ref.content_hash == "sha256:risk-concentration-fingerprint"
    assert evidence.concentration_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.concentration_diagnostic == "risk_issuer_coverage_complete"
    assert seen == [
        (
            "POST",
            "https://risk.example/analytics/risk/concentration",
            {
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "as_of_date": "2026-06-21",
                },
            },
        )
    ]


def test_lotus_risk_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(RiskSourceEntitlementDenied):
        adapter.fetch_concentration_evidence(_request())


def test_lotus_risk_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        adapter.fetch_concentration_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_risk_adapter_maps_missing_runtime_metadata_to_source_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"source_service": "lotus-risk"})

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(httpx.MockTransport(handler)).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_single_position_concentration_missing"


def test_lotus_risk_adapter_maps_missing_generated_at_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("generated_at")

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_generated_at_missing"


def test_lotus_risk_adapter_maps_missing_as_of_date_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("as_of_date")

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_as_of_date_missing"


def test_lotus_risk_adapter_maps_missing_content_hash_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("request_fingerprint")

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_content_hash_missing"


def test_lotus_risk_adapter_maps_naive_generated_at_to_source_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["generated_at"] = "2026-06-21T10:00:00"

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_generated_at_naive"


def test_lotus_risk_adapter_maps_malformed_concentration_weight_to_source_unavailable() -> None:
    payload = _payload()
    single_position = payload["single_position_concentration"]
    assert isinstance(single_position, dict)
    single_position["top_position_weight_current"] = "not-decimal"

    with pytest.raises(RiskSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_concentration_evidence(_request())

    assert exc_info.value.code == "risk_top_position_weight_malformed"


def test_lotus_risk_adapter_accepts_missing_source_weights_as_source_gap() -> None:
    payload = _payload()
    single_position = payload["single_position_concentration"]
    issuer_concentration = payload["issuer_concentration"]
    assert isinstance(single_position, dict)
    assert isinstance(issuer_concentration, dict)
    single_position.pop("top_position_weight_current")
    issuer_concentration.pop("top_issuer_weight_current")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.top_position_weight_current is None
    assert evidence.top_issuer_weight_current is None
    assert evidence.concentration_diagnostic == "risk_concentration_weights_missing"


def test_lotus_risk_adapter_marks_missing_issuer_coverage_diagnostic() -> None:
    payload = _payload()
    issuer_concentration = payload["issuer_concentration"]
    assert isinstance(issuer_concentration, dict)
    issuer_concentration.pop("coverage_status")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.issuer_coverage_status is None
    assert evidence.concentration_diagnostic == "risk_issuer_coverage_missing"


def test_lotus_risk_adapter_maps_stale_freshness_metadata() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["freshness"] = "STALE_SOURCE"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.concentration_ref is not None
    assert evidence.concentration_ref.freshness is EvidenceFreshness.STALE


@pytest.mark.parametrize(
    ("freshness_status", "expected"),
    [
        ("expired", EvidenceFreshness.EXPIRED),
        ("unavailable", EvidenceFreshness.UNAVAILABLE),
        ("current", EvidenceFreshness.CURRENT),
    ],
)
def test_lotus_risk_adapter_maps_declared_freshness_states(
    freshness_status: str,
    expected: EvidenceFreshness,
) -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["freshness_status"] = freshness_status

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.concentration_ref is not None
    assert evidence.concentration_ref.freshness is expected


def test_lotus_risk_adapter_marks_unknown_supportability_as_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {"state": "partial"}

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.concentration_ref is not None
    assert evidence.concentration_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_risk_adapter_requires_declared_freshness_for_ready_supportability() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    supportability = metadata["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.pop("freshness_bucket")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_concentration_evidence(_request())

    assert evidence.concentration_ref is not None
    assert evidence.concentration_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_risk_concentration_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        RiskConcentrationEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )


def test_risk_concentration_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        RiskConcentrationEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )
