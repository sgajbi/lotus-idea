from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.missing_benchmark_signals as missing_benchmark_signals_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBenchmarkAssignmentSourcePort,
    CoreSourceUnavailable,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    CoreBenchmarkAssignmentSourceRuntime,
    CoreBenchmarkAssignmentSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingCoreBenchmarkAssignmentSource(CoreBenchmarkAssignmentSourcePort):
    seen_request: CoreBenchmarkAssignmentEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0
    close_error: Exception | None = None

    def fetch_benchmark_assignment_evidence(
        self,
        request: CoreBenchmarkAssignmentEvidenceRequest,
    ) -> CoreBenchmarkAssignmentEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _core_benchmark_assignment_evidence()

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


def test_missing_benchmark_source_api_fetches_core_evidence_without_persistence(
    monkeypatch: Any,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    source = RecordingCoreBenchmarkAssignmentSource()
    runtime = CoreBenchmarkAssignmentSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-missing-benchmark-source-api"
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["sourceRefs"][0] == {
        "productId": "lotus-core:BenchmarkAssignment:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert source.seen_request == CoreBenchmarkAssignmentEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        reporting_currency="USD",
        correlation_id="corr-missing-benchmark-source-api",
        trace_id="trace-missing-benchmark-source-api",
    )
    assert source.close_count == 1
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert "route" not in response.text
    assert "contentHash" not in response.text


def test_missing_benchmark_source_api_requires_portfolio_entitlement(
    monkeypatch: Any,
) -> None:
    runtime_called = False

    def fail_if_called() -> CoreBenchmarkAssignmentSourceRuntime:
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("source runtime must not be built after entitlement denial")

    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        fail_if_called,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_OTHER"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime_called is False
    assert PORTFOLIO_ID not in response.text


def test_missing_benchmark_source_api_blocks_when_core_runtime_is_not_configured(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        lambda: CoreBenchmarkAssignmentSourceRuntimeBlocker(
            "lotus_core_base_url_not_configured",
            core_base_url_configured=False,
            core_query_base_url_configured=False,
            core_query_control_plane_base_url_configured=False,
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": (
            "Core source runtime is not configured for missing-benchmark source evaluation."
        ),
    }
    assert PORTFOLIO_ID not in response.text
    assert "lotus_core_base_url_not_configured" not in response.text


def test_missing_benchmark_source_api_returns_blocked_posture_for_core_unavailable(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBenchmarkAssignmentSource(
        error=CoreSourceUnavailable(code="core_benchmark_assignment_pending")
    )
    runtime = CoreBenchmarkAssignmentSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "blocked"
    assert payload["candidate"] is None
    assert payload["unsupportedReasons"] == ["source_unavailable"]
    assert source.close_count == 1
    assert PORTFOLIO_ID not in response.text


def test_missing_benchmark_source_api_emits_bounded_operation_events(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBenchmarkAssignmentSource()
    runtime = CoreBenchmarkAssignmentSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    events: list[tuple[str, str, str, bool, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append(
            (
                args[0].value,
                args[1].value,
                kwargs["source_authority"],
                kwargs.get("durable_storage_backed", False),
                kwargs.get("error_code"),
            )
        )

    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "emit_foundation_operation_event",
        capture_event,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert events == [("signal_evaluation", "accepted", "lotus-core", False, None)]


def test_missing_benchmark_source_api_suppresses_runtime_close_failure(
    monkeypatch: Any,
) -> None:
    source = RecordingCoreBenchmarkAssignmentSource(
        close_error=RuntimeError(f"close {PORTFOLIO_ID}")
    )
    runtime = CoreBenchmarkAssignmentSourceRuntime(
        core_source=source,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    events: list[tuple[str, str, str | None]] = []

    def capture_event(*args: Any, **kwargs: Any) -> None:
        events.append((args[0].value, args[1].value, kwargs.get("error_code")))

    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "_build_core_benchmark_assignment_source_runtime_from_environment",
        lambda: runtime,
    )
    monkeypatch.setattr(
        missing_benchmark_signals_api,
        "emit_foundation_operation_event",
        capture_event,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
        json=missing_benchmark_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "candidate_created"
    assert source.close_count == 1
    assert ("signal_evaluation", "suppressed", "runtime_cleanup_failed") in events
    assert "close " not in response.text
    assert PORTFOLIO_ID not in response.text


def test_missing_benchmark_signal_api_returns_review_candidate() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=missing_benchmark_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_benchmark"
    assert payload["reasonCodes"] == ["missing_benchmark", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-core:BenchmarkAssignment:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_missing_benchmark_signal_api_reports_ready_assignment_not_eligible() -> None:
    client = TestClient(app)
    payload = missing_benchmark_payload()
    payload["benchmarkIdentityResolved"] = True
    payload["assignmentEffectiveForAsOfDate"] = True
    payload["assignmentStatus"] = "ACTIVE"
    payload["assignmentVersionPresent"] = True

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "missing_benchmark",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_missing_benchmark_signal_api_reports_stale_source_blocker() -> None:
    client = TestClient(app)
    payload = missing_benchmark_payload()
    payload["benchmarkAssignmentRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_benchmark",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-core",
        "supportedFeaturePromoted": False,
    }


def test_missing_benchmark_signal_api_rejects_wrong_source_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = TestClient(app)
    payload = missing_benchmark_payload()
    payload["benchmarkAssignmentRef"] = {
        **payload["benchmarkAssignmentRef"],
        "productId": "lotus-performance:ReturnsSeriesBundle:v1",
        "sourceSystem": "lotus-performance",
        "route": "/performance/returns/series",
        "contentHash": "sha256:wrong-missing-benchmark-source",
    }
    events: list[tuple[str, str, str, str | None]] = []

    def capture(operation: Any, outcome: Any, **kwargs: Any) -> None:
        events.append(
            (
                operation.value,
                outcome.value,
                kwargs["source_authority"],
                kwargs.get("error_code"),
            )
        )

    monkeypatch.setattr(missing_benchmark_signals_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "ReturnsSeriesBundle" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-core",
            "source_ref_contract_mismatch",
        )
    ]


def test_missing_benchmark_signal_api_requires_signal_permission() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/idea-signals/missing-benchmark/evaluate",
        json=missing_benchmark_payload(),
        headers={
            "X-Caller-Subject": "viewer-001",
            "X-Caller-Roles": "viewer",
            "X-Caller-Capabilities": "idea.review.queue.read",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def source_evaluation_headers(
    *,
    portfolio_ids: str = PORTFOLIO_ID,
) -> dict[str, str]:
    return {
        **evaluate_headers(),
        "X-Correlation-Id": "corr-missing-benchmark-source-api",
        "X-Trace-Id": "trace-missing-benchmark-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
    }


def missing_benchmark_source_payload(
    *,
    portfolio_id: str = PORTFOLIO_ID,
) -> dict[str, str]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "reportingCurrency": "usd",
    }


def missing_benchmark_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "benchmarkAssignmentRef": {
            "productId": "lotus-core:BenchmarkAssignment:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/benchmark-assignment",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:benchmark-assignment-gap",
            "dataQualityStatus": "complete",
            "freshness": "current",
        },
        "benchmarkIdentityResolved": False,
        "assignmentEffectiveForAsOfDate": False,
        "assignmentStatus": "ACTIVE",
        "assignmentVersionPresent": True,
        "entitlementAllowed": True,
    }


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _core_benchmark_assignment_evidence() -> CoreBenchmarkAssignmentEvidence:
    return CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=_source_ref("lotus-core:BenchmarkAssignment:v1"),
        benchmark_identity_resolved=False,
        assignment_effective_for_as_of_date=False,
        assignment_status="ACTIVE",
        assignment_version_present=True,
        assignment_diagnostic="core_benchmark_assignment_benchmark_identity_missing",
    )
