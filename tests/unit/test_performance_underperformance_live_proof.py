from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.performance_underperformance_live_proof import (
    PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_SCHEMA_VERSION,
    build_performance_underperformance_live_proof_payload,
    performance_underperformance_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.performance_sources import (
    PerformanceOpportunitySourcePort,
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingPerformanceSource(PerformanceOpportunitySourcePort):
    error: Exception | None = None

    def fetch_underperformance_evidence(
        self, request: PerformanceUnderperformanceEvidenceRequest
    ) -> PerformanceUnderperformanceEvidence:
        if self.error is not None:
            raise self.error
        return _performance_evidence()


def test_performance_underperformance_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_performance_underperformance_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "benchmarkContextAvailable": True,
            "sourceDiagnosticCodes": ["performance_benchmark_context_ready"],
            "reasonCodes": ["underperformance_attention"],
            "unsupportedReasons": [],
        },
    )

    assert payload["schemaVersion"] == PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["benchmarkContextAvailable"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_live_performance_source_proof_missing"
    ]
    assert (
        "opportunity_archetype_benchmark_assignment_source_ref_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert performance_underperformance_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_performance_underperformance_live_proof_does_not_validate() -> None:
    payload = build_performance_underperformance_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "evaluationOutcome": "blocked",
            "sourceEvidenceCurrent": False,
            "benchmarkContextAvailable": False,
            "errorCode": "performance_source_unavailable",
            "sourceDiagnosticCodes": ["performance_source_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "live_performance_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_performance_source_unavailable" in payload["proofBlockers"]
    assert "performance_source_evidence_not_current" in payload["proofBlockers"]
    assert "performance_benchmark_context_missing" in payload["proofBlockers"]
    assert "no_underperformance_candidate_generated" in payload["proofBlockers"]
    assert performance_underperformance_live_proof_is_valid(payload) is False


def test_performance_underperformance_live_proof_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_performance_underperformance_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            live_performance_source_attempted=True,
            evaluation_summary={},
        )


def test_performance_underperformance_live_proof_rejects_missing_benchmark_context() -> None:
    payload = build_performance_underperformance_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_performance_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "benchmarkContextAvailable": False,
            "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
            "reasonCodes": ["underperformance_attention"],
            "unsupportedReasons": [],
        },
    )

    assert "performance_benchmark_context_missing" in payload["proofBlockers"]
    assert performance_underperformance_live_proof_is_valid(payload) is False


def test_performance_underperformance_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "performance-underperformance-live-proof.json"

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
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["benchmarkContextAvailable"] is True
    assert (
        "opportunity_archetype_live_performance_source_proof_missing"
        in payload["aggregateBlockersCleared"]
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_performance_underperformance_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "performance-underperformance-live-proof.json"

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


def _performance_evidence() -> PerformanceUnderperformanceEvidence:
    return PerformanceUnderperformanceEvidence(
        source_reported_active_return=Decimal("-0.018"),
        benchmark_context_available=True,
        performance_ref=SourceRef(
            product_id="lotus-performance:ReturnsSeriesBundle:v1",
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            product_version="v1",
            route="/integration/returns/series",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:performance-returns-series",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        performance_diagnostic="performance_benchmark_context_ready",
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_performance_underperformance_live_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_performance_underperformance_live_proof", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
