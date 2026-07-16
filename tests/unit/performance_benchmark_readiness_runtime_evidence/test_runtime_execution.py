from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
from typing import Any, Callable

import pytest

from app.application.performance_benchmark_readiness import (
    evaluate_performance_benchmark_readiness,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (
    PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS,
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED,
    build_performance_benchmark_readiness_runtime_execution,
    performance_benchmark_readiness_runtime_execution_is_valid,
)
from app.application.runtime_evidence import sha256_json
from app.domain import EvidenceFreshness
from app.ports.performance_sources import PerformanceBenchmarkReadinessEvidence
from app.ports.performance_sources import (
    PerformanceBenchmarkReadinessEvidenceRequest,
    PerformanceSourceUnavailable,
)
from tests.support.performance_benchmark_readiness_runtime_evidence import (
    NOW,
    AuthoritativePerformanceBenchmarkReadinessSource,
    performance_benchmark_readiness_command,
    performance_benchmark_readiness_evidence,
    performance_benchmark_readiness_runtime_execution,
)


def test_runtime_execution_qualifies_review_required_from_one_performance_fetch() -> None:
    source = AuthoritativePerformanceBenchmarkReadinessSource()

    payload = performance_benchmark_readiness_runtime_execution(source=source)

    assert len(source.requests) == 1
    assert performance_benchmark_readiness_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS
    )
    execution = payload["execution"]
    assert isinstance(execution, dict)
    evaluation = execution["evaluationReceipt"]
    assert evaluation["outcome"] == "review_required"
    assert evaluation["benchmarkReviewRequired"] is True
    serialized = json.dumps(payload)
    for raw_identifier in (
        "tenant-a",
        "book-a",
        "portfolio-a",
        "client-a",
        "evaluation-a",
        "corr-performance",
        "trace-performance",
        "calculation-a",
    ):
        assert raw_identifier not in serialized


def test_runtime_execution_accepts_truthful_no_opportunity() -> None:
    source = AuthoritativePerformanceBenchmarkReadinessSource(
        evidence=performance_benchmark_readiness_evidence(
            benchmark_context_available=True,
            benchmark_id="BMK_BALANCED",
            benchmark_return_source="calculated",
            readiness_diagnostic="performance_benchmark_context_ready",
        )
    )

    payload = performance_benchmark_readiness_runtime_execution(source=source)

    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "no_opportunity"
    assert evaluation["benchmarkReviewRequired"] is False
    assert performance_benchmark_readiness_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    (
        (
            lambda evidence: replace(evidence, response_portfolio_id="other"),
            "performance_benchmark_readiness_portfolio_scope_mismatch",
        ),
        (
            lambda evidence: replace(evidence, producer_correlation_id="other"),
            "performance_benchmark_readiness_correlation_mismatch",
        ),
        (
            lambda evidence: replace(evidence, producer_trace_id="other"),
            "performance_benchmark_readiness_trace_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                performance_ref=replace(
                    evidence.performance_ref,
                    as_of_date=NOW.date() - timedelta(days=1),
                ),
            ),
            "performance_benchmark_readiness_as_of_date_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                performance_ref=replace(
                    evidence.performance_ref,
                    generated_at_utc=NOW + timedelta(seconds=1),
                ),
            ),
            "performance_benchmark_readiness_evidence_from_future",
        ),
        (
            lambda evidence: replace(
                evidence,
                performance_ref=replace(
                    evidence.performance_ref,
                    freshness=EvidenceFreshness.STALE,
                ),
            ),
            "performance_benchmark_readiness_evidence_not_current",
        ),
        (
            lambda evidence: replace(
                evidence,
                performance_ref=replace(
                    evidence.performance_ref,
                    data_quality_status="unknown",
                ),
            ),
            "performance_benchmark_readiness_data_quality_unsupported",
        ),
        (
            lambda evidence: replace(evidence, calculation_hash="sha256:" + "f" * 64),
            "performance_benchmark_readiness_content_hash_mismatch",
        ),
        (
            lambda evidence: replace(evidence, missing_point_count=1),
            "performance_benchmark_readiness_coverage_invalid",
        ),
        (
            lambda evidence: replace(
                evidence,
                readiness_diagnostic="performance_benchmark_context_ready",
            ),
            "performance_benchmark_readiness_diagnostic_mismatch",
        ),
    ),
)
def test_runtime_execution_fails_closed_on_source_scope_time_hash_or_count_drift(
    mutation: Callable[
        [PerformanceBenchmarkReadinessEvidence],
        PerformanceBenchmarkReadinessEvidence,
    ],
    expected_blocker: str,
) -> None:
    source = AuthoritativePerformanceBenchmarkReadinessSource(
        evidence=mutation(performance_benchmark_readiness_evidence())
    )

    payload = performance_benchmark_readiness_runtime_execution(source=source)

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not performance_benchmark_readiness_runtime_execution_is_valid(payload)


def test_runtime_execution_accepts_source_declared_partial_coverage() -> None:
    source = AuthoritativePerformanceBenchmarkReadinessSource(
        evidence=performance_benchmark_readiness_evidence(
            requested_point_count=120,
            returned_point_count=117,
            missing_point_count=3,
            coverage_ratio=Decimal("0.975"),
            data_quality_status="partial",
        )
    )

    payload = performance_benchmark_readiness_runtime_execution(source=source)

    assert performance_benchmark_readiness_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "path",
    (
        ("unexpected",),
        ("execution", "unexpected"),
        ("execution", "requestReceipt", "unexpected"),
        ("execution", "sourceReceipt", "unexpected"),
        ("execution", "evaluationReceipt", "unexpected"),
        ("nonProofClaims", "unexpected"),
    ),
)
def test_contract_rejects_unknown_fields(path: tuple[str, ...]) -> None:
    payload = deepcopy(performance_benchmark_readiness_runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = True

    assert not performance_benchmark_readiness_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("receipt_name", "field", "value"),
    (
        ("requestReceipt", "portfolioIdHash", "sha256:" + "f" * 64),
        ("sourceReceipt", "benchmarkContextAvailable", True),
        ("sourceReceipt", "requestedPointCount", 119),
        ("sourceReceipt", "readinessDiagnostic", "performance_benchmark_context_ready"),
        ("evaluationReceipt", "outcome", "no_opportunity"),
        ("evaluationReceipt", "sourceRefCount", 2),
    ),
)
def test_contract_rejects_recomputed_digest_semantic_tampering(
    receipt_name: str,
    field: str,
    value: object,
) -> None:
    payload = deepcopy(performance_benchmark_readiness_runtime_execution())
    receipt = payload["execution"][receipt_name]
    receipt[field] = value
    digest_key = {
        "requestReceipt": "requestDigest",
        "sourceReceipt": "receiptDigest",
        "evaluationReceipt": "evaluationDigest",
    }[receipt_name]
    receipt[digest_key] = sha256_json(
        {key: item for key, item in receipt.items() if key != digest_key}
    )
    if receipt_name == "sourceReceipt":
        evaluation = payload["execution"]["evaluationReceipt"]
        evaluation["sourceReceiptDigest"] = receipt["receiptDigest"]
        evaluation["benchmarkContextDigest"] = sha256_json(
            {
                key: receipt[key]
                for key in (
                    "benchmarkContextAvailable",
                    "benchmarkIdHash",
                    "benchmarkReturnSource",
                    "readinessDiagnostic",
                )
            }
        )
        evaluation["evaluationDigest"] = sha256_json(
            {key: item for key, item in evaluation.items() if key != "evaluationDigest"}
        )

    assert not performance_benchmark_readiness_runtime_execution_is_valid(payload)


def test_blocked_source_execution_preserves_stable_error_without_receipts() -> None:
    source = _UnavailablePerformanceSource()
    result = evaluate_performance_benchmark_readiness(
        performance_benchmark_readiness_command(),
        performance_source=source,
    )

    payload = build_performance_benchmark_readiness_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert len(source.requests) == 1
    assert payload["execution"]["status"] == "blocked"
    assert payload["execution"]["sourceReceipt"] is None
    assert payload["execution"]["evaluationReceipt"] is None
    assert payload["execution"]["qualificationBlockers"] == [
        "performance_benchmark_readiness_source_execution_blocked",
        "performance_returns_series_pending",
    ]
    assert not performance_benchmark_readiness_runtime_execution_is_valid(payload)


class _UnavailablePerformanceSource:
    def __init__(self) -> None:
        self.requests: list[PerformanceBenchmarkReadinessEvidenceRequest] = []

    def fetch_benchmark_readiness_evidence(
        self,
        request: PerformanceBenchmarkReadinessEvidenceRequest,
    ) -> PerformanceBenchmarkReadinessEvidence:
        self.requests.append(request)
        raise PerformanceSourceUnavailable(code="performance_returns_series_pending")
