from __future__ import annotations

from typing import Any

import app.api.idea_signals as idea_signals_api
from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.support.http import managed_test_client


def test_high_cash_persist_api_rejects_malformed_source_digest_before_side_effects(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests()
    evaluator_called = False

    def fail_if_evaluated(*args: Any, **kwargs: Any) -> None:
        nonlocal evaluator_called
        evaluator_called = True
        raise AssertionError("request validation must run before signal evaluation")

    monkeypatch.setattr(
        idea_signals_api,
        "evaluate_and_persist_high_cash_signal_command",
        fail_if_evaluated,
    )

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json={
            "asOfDate": "2026-06-21",
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "sourceReportedCashWeight": "0.18",
            "sourceEvidence": {
                "portfolioStateRef": {
                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                    "sourceSystem": "lotus-core",
                    "productVersion": "v1",
                    "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
                    "asOfDate": "2026-06-21",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "x",
                    "dataQualityStatus": "complete",
                    "freshness": "current",
                }
            },
            "accessScope": {
                "tenantId": "tenant-a",
                "bookId": "book-advisor-001",
                "portfolioId": "PB_SG_GLOBAL_BAL_001",
                "clientId": "client-001",
            },
        },
        headers={
            "X-Caller-Subject": "signal-ingestion-worker",
            "X-Caller-Capabilities": "idea.candidate.persist",
            "X-Correlation-Id": "corr-invalid-source-digest",
            "Idempotency-Key": "persist-high-cash-api-invalid-digest-001",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Request validation failed. Correct the request fields and retry.",
    }
    assert evaluator_called is False
    assert get_idea_repository().snapshot().candidate_records == {}
    assert "contentHash" not in response.text
