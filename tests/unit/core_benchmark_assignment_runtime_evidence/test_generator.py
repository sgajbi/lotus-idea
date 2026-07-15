from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.core_benchmark_assignment_runtime_evidence import (
    core_benchmark_assignment_runtime_execution_is_valid,
)
from app.ports.core_sources import CoreBenchmarkAssignmentEvidenceRequest, CoreSourceUnavailable
from scripts.core_benchmark_assignment_runtime_evidence import generate_runtime_execution
from tests.support.core_benchmark_assignment_runtime_evidence import (
    AuthoritativeCoreBenchmarkAssignmentSource,
)


class UnavailableCoreSource:
    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> object:
        raise CoreSourceUnavailable(code="core_benchmark_assignment_source_unavailable")


@pytest.mark.parametrize(
    ("source", "expected_exit", "expected_status"),
    [
        (AuthoritativeCoreBenchmarkAssignmentSource(), 0, "completed"),
        (UnavailableCoreSource(), 3, "blocked"),
    ],
)
def test_generator_routes_through_application_use_case_and_writes_truthful_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: object,
    expected_exit: int,
    expected_status: str,
) -> None:
    output = tmp_path / "core-benchmark-assignment-runtime-execution.json"
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: source,
    )

    exit_code = generate_runtime_execution.main(
        [
            "--core-query-control-plane-base-url",
            "http://localhost:8101",
            "--tenant-id",
            "tenant-a",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--reporting-currency",
            "USD",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--correlation-id",
            "corr-secret",
            "--trace-id",
            "trace-secret",
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == expected_exit
    assert payload["execution"]["status"] == expected_status
    assert core_benchmark_assignment_runtime_execution_is_valid(payload) is (expected_exit == 0)
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "tenant-a" not in serialized
    assert "corr-secret" not in serialized
    assert "trace-secret" not in serialized
