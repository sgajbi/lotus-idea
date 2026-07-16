from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.application.core_missing_benchmark_runtime_evidence import (  # noqa: E402
    CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS,
    CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateCoreMissingBenchmark,
    build_core_missing_benchmark_runtime_execution,
    core_missing_benchmark_runtime_execution_is_valid,
    evaluate_core_missing_benchmark,
)
from app.application.runtime_evidence import sha256_json  # noqa: E402
from app.ports.core_sources import CoreBenchmarkAssignmentEvidenceRequest  # noqa: E402
from tests.support.core_missing_benchmark_runtime_evidence import (  # noqa: E402
    AuthoritativeCoreMissingBenchmarkSource,
    ready_benchmark_evidence,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT / "scripts" / "core_missing_benchmark_runtime_evidence" / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "missing_benchmark_live_proof.py",
    ROOT / "scripts" / "generate_missing_benchmark_live_proof.py",
    ROOT / "scripts" / "missing_benchmark_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_missing_benchmark_live_proof.py",
)
FORBIDDEN_KEYS = {
    "bookId",
    "clientId",
    "correlationId",
    "evaluationId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "tenantId",
    "traceId",
}
FORBIDDEN_TEXT = {
    "tenant-a",
    "book-a",
    "portfolio-a",
    "client-a",
    "evaluation-a",
    "corr-core",
    "trace-core",
}
NOW = datetime(2026, 7, 16, 13, 10, tzinfo=UTC)


def validate_core_missing_benchmark_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Core missing-benchmark generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                f"retired missing-benchmark evidence path is prohibited: {path.relative_to(ROOT)}"
            )

    command = _command()
    candidate = _payload(command, AuthoritativeCoreMissingBenchmarkSource())
    if not core_missing_benchmark_runtime_execution_is_valid(candidate):
        errors.append("authoritative Core missing-benchmark candidate fixture must validate")
    if candidate.get("aggregateBlockersSatisfied") != list(
        CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the missing-benchmark Core blocker")
    if candidate.get("remainingCertificationBlockers") != list(
        CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    source = AuthoritativeCoreMissingBenchmarkSource()
    source.evidence = ready_benchmark_evidence(_request_for(command))
    no_opportunity = _payload(command, source)
    if not core_missing_benchmark_runtime_execution_is_valid(no_opportunity):
        errors.append("truthful ready-assignment no-opportunity execution must validate")

    tampered = deepcopy(candidate)
    tampered["execution"]["sourceReceipt"]["assignmentDiagnostic"] = (
        "core_benchmark_assignment_ready"
    )
    source_receipt = tampered["execution"]["sourceReceipt"]
    source_receipt["receiptDigest"] = sha256_json(
        {key: value for key, value in source_receipt.items() if key != "receiptDigest"}
    )
    if core_missing_benchmark_runtime_execution_is_valid(tampered):
        errors.append("recomputed-digest assignment semantic tampering must fail closed")

    for payload in (candidate, no_opportunity, tampered):
        validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _payload(
    command: EvaluateCoreMissingBenchmark,
    source: AuthoritativeCoreMissingBenchmarkSource,
) -> dict[str, Any]:
    result = evaluate_core_missing_benchmark(command, core_source=source)
    return build_core_missing_benchmark_runtime_execution(generated_at_utc=NOW, result=result)


def _command() -> EvaluateCoreMissingBenchmark:
    return EvaluateCoreMissingBenchmark(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=date(2026, 7, 16),
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _request_for(
    command: EvaluateCoreMissingBenchmark,
) -> CoreBenchmarkAssignmentEvidenceRequest:
    return CoreBenchmarkAssignmentEvidenceRequest(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
        as_of_date=command.as_of_date,
        evaluated_at_utc=command.evaluated_at_utc,
        reporting_currency=command.reporting_currency,
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )


def main() -> int:
    errors = validate_core_missing_benchmark_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Core missing-benchmark runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
