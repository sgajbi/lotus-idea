from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

import pytest

from app.application.performance_benchmark_readiness_runtime_evidence import (
    performance_benchmark_readiness_runtime_execution_is_valid,
)
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceUnavailable,
)
from scripts.performance_benchmark_readiness_runtime_evidence import (
    generate_runtime_execution,
)
from tests.support.performance_benchmark_readiness_runtime_evidence import (
    AuthoritativePerformanceBenchmarkReadinessSource,
    performance_benchmark_readiness_evidence,
)


def test_generator_invokes_one_use_case_fetch_and_closes_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "missing-benchmark-performance-readiness-proof.json"
    source = AuthoritativePerformanceBenchmarkReadinessSource(
        evidence=_generator_evidence()
    )
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusPerformanceUnderperformanceSourceAdapter",
        lambda _client: source,
    )

    result = generate_runtime_execution.main(_args(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert len(source.requests) == 1
    assert source.closed is True
    assert performance_benchmark_readiness_runtime_execution_is_valid(payload)
    serialized = json.dumps(payload)
    for raw_identifier in (
        "PB_SG_GLOBAL_BAL_001",
        "tenant-sensitive",
        "book-sensitive",
        "client-sensitive",
        "evaluation-sensitive",
        "correlation-sensitive",
        "trace-sensitive",
    ):
        assert raw_identifier not in serialized


def test_generator_accepts_truthful_no_opportunity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "missing-benchmark-performance-readiness-proof.json"
    source = AuthoritativePerformanceBenchmarkReadinessSource(
        evidence=performance_benchmark_readiness_evidence(
            benchmark_context_available=True,
            benchmark_id="BMK_BALANCED",
            benchmark_return_source="calculated",
            readiness_diagnostic="performance_benchmark_context_ready",
            response_portfolio_id="PB_SG_GLOBAL_BAL_001",
            producer_correlation_id="correlation-sensitive",
            producer_trace_id="trace-sensitive",
        )
    )
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusPerformanceUnderperformanceSourceAdapter",
        lambda _client: source,
    )

    result = generate_runtime_execution.main(_args(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["execution"]["evaluationReceipt"]["outcome"] == "no_opportunity"
    assert performance_benchmark_readiness_runtime_execution_is_valid(payload)


def test_generator_writes_blocked_artifact_for_stable_source_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "missing-benchmark-performance-readiness-proof.json"
    source = UnavailablePerformanceBenchmarkReadinessSource()
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusPerformanceUnderperformanceSourceAdapter",
        lambda _client: source,
    )

    result = generate_runtime_execution.main(_args(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 3
    assert len(source.requests) == 1
    assert source.closed is True
    assert payload["execution"]["sourceReceipt"] is None
    assert payload["execution"]["evaluationReceipt"] is None
    assert "performance_returns_series_pending" in payload["execution"]["qualificationBlockers"]
    assert not performance_benchmark_readiness_runtime_execution_is_valid(payload)


@dataclass
class UnavailablePerformanceBenchmarkReadinessSource:
    requests: list[PerformanceBenchmarkReadinessEvidenceRequest] = field(default_factory=list)
    closed: bool = False

    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        self.requests.append(request)
        raise PerformanceSourceUnavailable(code="performance_returns_series_pending")

    def close(self) -> None:
        self.closed = True


def _args(output: Path) -> list[str]:
    return [
        "--performance-base-url",
        "http://performance.test",
        "--tenant-id",
        "tenant-sensitive",
        "--book-id",
        "book-sensitive",
        "--portfolio-id",
        "PB_SG_GLOBAL_BAL_001",
        "--client-id",
        "client-sensitive",
        "--evaluation-id",
        "evaluation-sensitive",
        "--as-of-date",
        "2026-07-16",
        "--period-name",
        "1Y",
        "--reporting-currency",
        "USD",
        "--generated-at-utc",
        "2026-07-16T14:00:00Z",
        "--evaluated-at-utc",
        "2026-07-16T14:00:00Z",
        "--correlation-id",
        "correlation-sensitive",
        "--trace-id",
        "trace-sensitive",
        "--output",
        str(output),
    ]


def _generator_evidence() -> PerformanceBenchmarkReadinessEvidence:
    return performance_benchmark_readiness_evidence(
        response_portfolio_id="PB_SG_GLOBAL_BAL_001",
        producer_correlation_id="correlation-sensitive",
        producer_trace_id="trace-sensitive",
    )
