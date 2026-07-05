from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.drawdown_review_signals as drawdown_review_signals_api
import app.api.high_volatility_signals as high_volatility_signals_api
import app.api.underperformance_signals as underperformance_signals_api
from app.main import app
from app.runtime.source_ingestion_state import (
    PerformanceUnderperformanceSourceRuntimeBlocker,
    RiskDrawdownSourceRuntimeBlocker,
    RiskVolatilitySourceRuntimeBlocker,
)


OperationEventCall = tuple[str, str, str, bool, str | None]


def test_drawdown_review_source_api_emits_blocked_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = capture_foundation_events(monkeypatch, drawdown_review_signals_api)
    monkeypatch.setattr(
        drawdown_review_signals_api,
        "_build_risk_drawdown_source_runtime_from_environment",
        lambda: RiskDrawdownSourceRuntimeBlocker("lotus_risk_base_url_not_configured"),
    )

    response = TestClient(app).post(
        "/api/v1/idea-signals/drawdown-review/evaluate-from-source",
        json=signal_source_payload(),
        headers=source_signal_headers(),
    )

    assert response.status_code == 503
    assert events == [
        (
            "signal_evaluation",
            "blocked",
            "lotus-risk",
            False,
            "lotus_risk_base_url_not_configured",
        )
    ]


def test_high_volatility_source_api_emits_blocked_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = capture_foundation_events(monkeypatch, high_volatility_signals_api)
    monkeypatch.setattr(
        high_volatility_signals_api,
        "_build_risk_volatility_source_runtime_from_environment",
        lambda: RiskVolatilitySourceRuntimeBlocker("lotus_risk_base_url_not_configured"),
    )

    response = TestClient(app).post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=signal_source_payload(),
        headers=source_signal_headers(),
    )

    assert response.status_code == 503
    assert events == [
        (
            "signal_evaluation",
            "blocked",
            "lotus-risk",
            False,
            "lotus_risk_base_url_not_configured",
        )
    ]


def test_underperformance_source_api_emits_blocked_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = capture_foundation_events(monkeypatch, underperformance_signals_api)
    monkeypatch.setattr(
        underperformance_signals_api,
        "_build_performance_underperformance_source_runtime_from_environment",
        lambda: PerformanceUnderperformanceSourceRuntimeBlocker(
            "lotus_performance_base_url_not_configured"
        ),
    )

    response = TestClient(app).post(
        "/api/v1/idea-signals/underperformance/evaluate-from-source",
        json=signal_source_payload(),
        headers=source_signal_headers(),
    )

    assert response.status_code == 503
    assert events == [
        (
            "signal_evaluation",
            "blocked",
            "lotus-performance",
            False,
            "lotus_performance_base_url_not_configured",
        )
    ]


def capture_foundation_events(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
) -> list[OperationEventCall]:
    events: list[OperationEventCall] = []

    def capture_foundation_event(
        operation: Any,
        outcome: Any,
        *,
        source_authority: str = "lotus-idea",
        durable_storage_backed: bool = False,
        error_code: str | None = None,
    ) -> None:
        events.append(
            (operation.value, outcome.value, source_authority, durable_storage_backed, error_code)
        )

    monkeypatch.setattr(module, "emit_foundation_operation_event", capture_foundation_event)
    return events


def source_signal_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
    }


def signal_source_payload() -> dict[str, str]:
    return {
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "asOfDate": "2026-06-21",
        "periodName": "YTD",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
    }
