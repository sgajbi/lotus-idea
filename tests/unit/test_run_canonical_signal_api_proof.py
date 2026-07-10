from __future__ import annotations

from datetime import UTC, datetime
from email.message import Message
from io import BytesIO
import json
from urllib.error import HTTPError
from collections.abc import Mapping

import pytest

from scripts.run_canonical_signal_api_proof import (
    API_PROOF_CASES,
    _aggregate_payload,
    _run_cases,
)


def test_api_proof_preserves_route_contract_observations_without_raw_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "outcome": "not_eligible",
        "family": "high_cash",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }

    import scripts.run_canonical_signal_api_proof as proof_module

    def fake_post_json(
        *,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, dict[str, object]]:
        del payload, headers, timeout_seconds
        matching_case = next(case for case in API_PROOF_CASES if case.path in url)
        return 200, {
            **response,
            "family": matching_case.family,
            "sourceAuthority": matching_case.source_authority,
        }

    monkeypatch.setattr(proof_module, "_post_json", fake_post_json)
    summaries = _run_cases(
        base_url="http://idea.dev.lotus",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date="2026-04-10",
        evaluated_at="2026-07-10T00:00:00Z",
        correlation_id="corr-api-proof",
        trace_id="trace-api-proof",
        timeout_seconds=5.0,
    )

    assert len(summaries) == len(API_PROOF_CASES)
    assert summaries[0]["responseValid"] is True
    assert "candidate" not in summaries[0]["responseObservation"]
    assert all(summary["statusCode"] == 200 for summary in summaries)


def test_api_proof_fails_closed_without_persisting_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.run_canonical_signal_api_proof as proof_module

    def fail(
        *,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> tuple[int, dict[str, object]]:
        del url, payload, headers, timeout_seconds
        raise HTTPError(
            url="http://idea.dev.lotus/api/v1/idea-signals/high-cash/evaluate-from-source",
            code=503,
            msg="source unavailable",
            hdrs=Message(),
            fp=BytesIO(b"sensitive response body"),
        )

    monkeypatch.setattr(proof_module, "_post_json", fail)
    summaries = _run_cases(
        base_url="http://idea.dev.lotus",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date="2026-04-10",
        evaluated_at="2026-07-10T00:00:00Z",
        correlation_id="corr-api-proof",
        trace_id="trace-api-proof",
        timeout_seconds=5.0,
    )

    assert all(summary["responseValid"] is False for summary in summaries)
    assert all(summary["errorCode"] == "http_status_503" for summary in summaries)
    assert all("sensitive response body" not in json.dumps(summary) for summary in summaries)


def test_api_proof_aggregate_preserves_non_promotion_boundary() -> None:
    payload = _aggregate_payload(
        generated_at=datetime(2026, 7, 10, tzinfo=UTC),
        evaluated_at=datetime(2026, 7, 10, tzinfo=UTC),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date="2026-04-10",
        idea_base_url="http://idea.dev.lotus",
        correlation_id="corr-api-proof",
        trace_id="trace-api-proof",
        summaries=[{"responseValid": True}],
    )

    assert payload["certificationReady"] is True
    assert payload["portfolioScope"] == "governed_canonical"
    assert "portfolioId" not in payload
    assert payload["supportedFeaturePromoted"] is False
    assert "no_data_mesh_certification" in payload["nonProofBoundaries"]
