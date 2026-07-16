from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.application.core_missing_benchmark_runtime_evidence import (
    core_missing_benchmark_runtime_execution_is_valid,
)
from app.ports.core_sources import CoreBenchmarkAssignmentEvidence
from scripts.core_missing_benchmark_runtime_evidence import generate_runtime_execution
from tests.support.core_missing_benchmark_runtime_evidence import (
    AuthoritativeCoreMissingBenchmarkSource,
)


def _ready_assignment(
    evidence: CoreBenchmarkAssignmentEvidence,
) -> CoreBenchmarkAssignmentEvidence:
    return replace(
        evidence,
        benchmark_identity_resolved=True,
        assignment_effective_for_as_of_date=True,
        assignment_diagnostic="core_benchmark_assignment_ready",
    )


@pytest.mark.parametrize(
    ("source", "expected_exit", "expected_status"),
    (
        (AuthoritativeCoreMissingBenchmarkSource(), 0, "completed"),
        (
            AuthoritativeCoreMissingBenchmarkSource(
                evidence_mutation=_ready_assignment,
            ),
            0,
            "completed",
        ),
    ),
)
def test_generator_routes_through_application_use_case_and_writes_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: AuthoritativeCoreMissingBenchmarkSource,
    expected_exit: int,
    expected_status: str,
) -> None:
    output = tmp_path / "core-missing-benchmark-runtime-execution.json"
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: source,
    )

    exit_code = generate_runtime_execution.main([*_arguments(), "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == expected_exit
    assert payload["execution"]["status"] == expected_status
    assert core_missing_benchmark_runtime_execution_is_valid(payload)
    assert len(source.requests) == 1
    serialized = json.dumps(payload)
    for raw_identifier in (
        "tenant-a",
        "book-a",
        "portfolio-a",
        "client-a",
        "evaluation-a",
        "corr-core",
        "trace-core",
    ):
        assert raw_identifier not in serialized


def test_generator_writes_blocked_source_failure_without_false_clearance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ports.core_sources import CoreSourceUnavailable

    source = AuthoritativeCoreMissingBenchmarkSource(
        error=CoreSourceUnavailable(code="core_benchmark_assignment_source_unavailable")
    )
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: source,
    )
    output = tmp_path / "blocked.json"

    exit_code = generate_runtime_execution.main([*_arguments(), "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 3
    assert payload["execution"]["status"] == "blocked"
    assert payload["aggregateBlockersSatisfied"] == []
    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


def _arguments() -> list[str]:
    return [
        "--core-query-control-plane-base-url",
        "http://localhost:8101",
        "--tenant-id",
        "tenant-a",
        "--book-id",
        "book-a",
        "--portfolio-id",
        "portfolio-a",
        "--client-id",
        "client-a",
        "--evaluation-id",
        "evaluation-a",
        "--as-of-date",
        "2026-07-16",
        "--reporting-currency",
        "USD",
        "--generated-at-utc",
        "2026-07-16T13:10:00Z",
        "--evaluated-at-utc",
        "2026-07-16T13:10:00Z",
        "--correlation-id",
        "corr-core",
        "--trace-id",
        "trace-core",
    ]
