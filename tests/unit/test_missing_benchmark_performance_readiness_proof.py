from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.missing_benchmark_performance_readiness_proof import (
    MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION,
    build_missing_benchmark_performance_readiness_proof_payload,
    missing_benchmark_performance_readiness_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidence,
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceUnavailable,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingPerformanceSource:
    error: Exception | None = None

    def fetch_benchmark_readiness_evidence(
        self, request: PerformanceBenchmarkReadinessEvidenceRequest
    ) -> PerformanceBenchmarkReadinessEvidence:
        if self.error is not None:
            raise self.error
        return _performance_readiness_evidence()


def test_missing_benchmark_performance_readiness_proof_accepts_missing_context() -> None:
    payload = build_missing_benchmark_performance_readiness_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        performance_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "sourceEvidenceCurrent": True,
            "performanceBenchmarkReadinessSourceRefPresent": True,
            "benchmarkContextAvailable": False,
            "benchmarkReadinessDiagnostic": "performance_benchmark_context_missing",
            "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
        },
    )

    assert payload["schemaVersion"] == MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["benchmarkReadinessEvaluated"] is True
    assert payload["benchmarkContextAvailable"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_performance_benchmark_readiness_source_ref_missing"
    ]
    assert (
        "opportunity_archetype_missing_benchmark_live_core_source_proof_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert missing_benchmark_performance_readiness_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_missing_benchmark_performance_readiness_proof_does_not_validate() -> None:
    payload = build_missing_benchmark_performance_readiness_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        performance_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "errorCode": "performance_source_unavailable",
            "sourceEvidenceCurrent": False,
            "performanceBenchmarkReadinessSourceRefPresent": False,
            "benchmarkContextAvailable": False,
            "benchmarkReadinessDiagnostic": "performance_source_unavailable",
            "sourceDiagnosticCodes": ["performance_source_unavailable"],
        },
    )

    assert (
        "missing_benchmark_performance_readiness_source_run_blocked" in (payload["proofBlockers"])
    )
    assert "source_error_performance_source_unavailable" in payload["proofBlockers"]
    assert (
        "missing_benchmark_performance_readiness_source_ref_missing" in (payload["proofBlockers"])
    )
    assert missing_benchmark_performance_readiness_proof_is_valid(payload) is False


def test_missing_benchmark_performance_readiness_proof_requires_source_ref() -> None:
    payload = build_missing_benchmark_performance_readiness_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        performance_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "sourceEvidenceCurrent": True,
            "performanceBenchmarkReadinessSourceRefPresent": False,
            "benchmarkContextAvailable": False,
            "benchmarkReadinessDiagnostic": "performance_benchmark_context_missing",
            "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
        },
    )

    assert (
        "missing_benchmark_performance_readiness_source_ref_missing" in (payload["proofBlockers"])
    )
    assert missing_benchmark_performance_readiness_proof_is_valid(payload) is False


def test_missing_benchmark_performance_readiness_proof_requires_timezone_aware_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_missing_benchmark_performance_readiness_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            live_performance_source_attempted=True,
            performance_summary={},
        )


def test_missing_benchmark_performance_readiness_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "missing-benchmark-performance-readiness-proof.json"

    monkeypatch.setattr(
        module,
        "LotusPerformanceUnderperformanceSourceAdapter",
        lambda _client: RecordingPerformanceSource(),
    )

    result = module.main(
        [
            "--performance-base-url",
            "http://localhost:8400",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--period-name",
            "1Y",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--correlation-id",
            "corr-123",
            "--trace-id",
            "trace-123",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "completed"
    assert payload["livePerformanceSourceAttempted"] is True
    assert payload["benchmarkReadinessEvaluated"] is True
    assert payload["benchmarkContextAvailable"] is False
    assert payload["sourceEvidenceCurrent"] is True
    assert (
        "opportunity_archetype_performance_benchmark_readiness_source_ref_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_missing_benchmark_performance_readiness_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "missing-benchmark-performance-readiness-proof.json"

    monkeypatch.setattr(
        module,
        "LotusPerformanceUnderperformanceSourceAdapter",
        lambda _client: RecordingPerformanceSource(
            error=PerformanceSourceUnavailable(code="performance_source_unavailable")
        ),
    )

    result = module.main(
        [
            "--performance-base-url",
            "http://localhost:8400",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 3
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "blocked"
    assert "source_error_performance_source_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _performance_readiness_evidence() -> PerformanceBenchmarkReadinessEvidence:
    return PerformanceBenchmarkReadinessEvidence(
        benchmark_context_available=False,
        performance_ref=SourceRef(
            product_id="lotus-performance:ReturnsSeriesBundle:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            product_version="v1",
            route="/integration/returns/series",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:performance-benchmark-readiness",
            data_quality_status="partial",
            freshness=EvidenceFreshness.CURRENT,
        ),
        performance_diagnostic="performance_benchmark_context_missing",
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_missing_benchmark_performance_readiness_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_missing_benchmark_performance_readiness_proof", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
