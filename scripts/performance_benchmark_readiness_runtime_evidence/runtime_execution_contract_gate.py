from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.application.performance_benchmark_readiness import (  # noqa: E402
    evaluate_performance_benchmark_readiness,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (  # noqa: E402
    PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS,
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED,
    build_performance_benchmark_readiness_runtime_execution,
    performance_benchmark_readiness_runtime_execution_is_valid,
)
from app.application.runtime_evidence import sha256_json  # noqa: E402
from tests.support.performance_benchmark_readiness_runtime_evidence import (  # noqa: E402
    NOW,
    AuthoritativePerformanceBenchmarkReadinessSource,
    performance_benchmark_readiness_command,
    performance_benchmark_readiness_evidence,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT
    / "scripts"
    / "performance_benchmark_readiness_runtime_evidence"
    / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "missing_benchmark_performance_readiness_proof.py",
    ROOT / "scripts" / "generate_missing_benchmark_performance_readiness_proof.py",
    ROOT / "scripts" / "missing_benchmark_performance_readiness_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_missing_benchmark_performance_readiness_proof.py",
)
FORBIDDEN_KEYS = {
    "bookId",
    "calculationId",
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
    "corr-performance",
    "trace-performance",
    "calculation-a",
}


def validate_performance_benchmark_readiness_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Performance benchmark-readiness generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                "retired Performance benchmark-readiness evidence path is prohibited: "
                f"{path.relative_to(ROOT)}"
            )

    candidate_source = AuthoritativePerformanceBenchmarkReadinessSource()
    review_required = _payload(candidate_source)
    if len(candidate_source.requests) != 1:
        errors.append("runtime evidence must perform exactly one Performance fetch")
    if not performance_benchmark_readiness_runtime_execution_is_valid(review_required):
        errors.append("authoritative Performance review-required fixture must validate")
    if review_required.get("aggregateBlockersSatisfied") != list(
        PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the Performance readiness blocker")
    if review_required.get("remainingCertificationBlockers") != list(
        PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    no_opportunity = _payload(
        AuthoritativePerformanceBenchmarkReadinessSource(
            evidence=performance_benchmark_readiness_evidence(
                benchmark_context_available=True,
                benchmark_id="BMK_BALANCED",
                benchmark_return_source="calculated",
                readiness_diagnostic="performance_benchmark_context_ready",
            )
        )
    )
    if not performance_benchmark_readiness_runtime_execution_is_valid(no_opportunity):
        errors.append("truthful Performance no-opportunity execution must validate")

    tampered = deepcopy(review_required)
    source_receipt = tampered["execution"]["sourceReceipt"]
    source_receipt["benchmarkContextAvailable"] = True
    source_receipt["receiptDigest"] = sha256_json(
        {key: value for key, value in source_receipt.items() if key != "receiptDigest"}
    )
    evaluation = tampered["execution"]["evaluationReceipt"]
    evaluation["sourceReceiptDigest"] = source_receipt["receiptDigest"]
    evaluation["evaluationDigest"] = sha256_json(
        {key: value for key, value in evaluation.items() if key != "evaluationDigest"}
    )
    if performance_benchmark_readiness_runtime_execution_is_valid(tampered):
        errors.append("recomputed-digest benchmark semantic tampering must fail closed")

    for payload in (review_required, no_opportunity, tampered):
        validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _payload(
    source: AuthoritativePerformanceBenchmarkReadinessSource,
) -> dict[str, object]:
    result = evaluate_performance_benchmark_readiness(
        performance_benchmark_readiness_command(),
        performance_source=source,
    )
    return build_performance_benchmark_readiness_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )


def main() -> int:
    errors = validate_performance_benchmark_readiness_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Performance benchmark-readiness runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
