from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from typing import Any, Callable

import pytest

from app.application.core_missing_benchmark_runtime_evidence import (
    CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS,
    CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateCoreMissingBenchmark,
    build_core_missing_benchmark_runtime_execution,
    core_missing_benchmark_runtime_execution_is_valid,
    evaluate_core_missing_benchmark,
)
from app.application.runtime_evidence import sha256_json
from app.domain import EvidenceFreshness, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreSourceUnavailable,
)
from tests.support.core_missing_benchmark_runtime_evidence import (
    AuthoritativeCoreMissingBenchmarkSource,
    ready_benchmark_evidence,
)

NOW = datetime(2026, 7, 16, 13, 10, tzinfo=UTC)


def test_runtime_execution_qualifies_candidate_from_one_authoritative_fetch() -> None:
    source = AuthoritativeCoreMissingBenchmarkSource()

    payload = _payload(source=source)

    assert len(source.requests) == 1
    assert source.requests[0].reporting_currency == "USD"
    assert core_missing_benchmark_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS
    )
    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "candidate_created"
    assert evaluation["missingBenchmarkReviewRequired"] is True
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


def test_runtime_execution_accepts_truthful_ready_assignment_no_opportunity() -> None:
    source = AuthoritativeCoreMissingBenchmarkSource()
    source.evidence = ready_benchmark_evidence(_source_request())

    payload = _payload(source=source)

    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "not_eligible"
    assert evaluation["missingBenchmarkReviewRequired"] is False
    assert evaluation["candidateIdHash"] is None
    assert core_missing_benchmark_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("mutation", "diagnostic"),
    (
        (
            lambda evidence: replace(
                evidence,
                benchmark_identity_resolved=True,
                assignment_diagnostic=("core_benchmark_assignment_not_effective_for_as_of_date"),
            ),
            "core_benchmark_assignment_not_effective_for_as_of_date",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_identity_resolved=True,
                assignment_effective_for_as_of_date=True,
                assignment_status=None,
                assignment_diagnostic="core_benchmark_assignment_status_missing",
            ),
            "core_benchmark_assignment_status_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_identity_resolved=True,
                assignment_effective_for_as_of_date=True,
                assignment_status="inactive",
                assignment_diagnostic="core_benchmark_assignment_inactive",
            ),
            "core_benchmark_assignment_inactive",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_identity_resolved=True,
                assignment_effective_for_as_of_date=True,
                assignment_version_present=False,
                assignment_diagnostic="core_benchmark_assignment_version_missing",
            ),
            "core_benchmark_assignment_version_missing",
        ),
    ),
)
def test_runtime_execution_qualifies_each_reviewable_assignment_gap(
    mutation: Callable[[CoreBenchmarkAssignmentEvidence], CoreBenchmarkAssignmentEvidence],
    diagnostic: str,
) -> None:
    payload = _payload(source=AuthoritativeCoreMissingBenchmarkSource(evidence_mutation=mutation))

    assert payload["execution"]["sourceReceipt"]["assignmentDiagnostic"] == diagnostic
    assert core_missing_benchmark_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    (
        (
            lambda evidence: replace(evidence, benchmark_assignment_ref=None),
            "core_benchmark_assignment_source_ref_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    source_system=SourceSystem.LOTUS_PERFORMANCE,
                ),
            ),
            "core_benchmark_assignment_source_authority_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    route="/integration/portfolios/{portfolio_id}/benchmark",
                ),
            ),
            "core_benchmark_assignment_route_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    as_of_date=evidence.benchmark_assignment_ref.as_of_date - timedelta(days=1),
                ),
            ),
            "core_benchmark_assignment_as_of_date_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    generated_at_utc=NOW + timedelta(seconds=1),
                ),
            ),
            "core_benchmark_assignment_evidence_from_future",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    freshness=EvidenceFreshness.STALE,
                ),
            ),
            "core_benchmark_assignment_evidence_not_current",
        ),
        (
            lambda evidence: replace(
                evidence,
                benchmark_assignment_ref=replace(
                    evidence.benchmark_assignment_ref,
                    data_quality_status="incomplete",
                ),
            ),
            "core_benchmark_assignment_data_quality_incomplete",
        ),
        (
            lambda evidence: replace(evidence, entitlement_allowed=False),
            "core_benchmark_assignment_entitlement_denied",
        ),
        (
            lambda evidence: replace(
                evidence,
                assignment_diagnostic="core_benchmark_assignment_ready",
            ),
            "core_benchmark_assignment_diagnostic_mismatch",
        ),
    ),
)
def test_runtime_execution_fails_closed_on_untrusted_source_evidence(
    mutation: Callable[[CoreBenchmarkAssignmentEvidence], CoreBenchmarkAssignmentEvidence],
    expected_blocker: str,
) -> None:
    payload = _payload(source=AuthoritativeCoreMissingBenchmarkSource(evidence_mutation=mutation))

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


def test_source_failure_preserves_stable_error_and_cannot_qualify() -> None:
    payload = _payload(
        source=AuthoritativeCoreMissingBenchmarkSource(
            error=CoreSourceUnavailable(code="core_benchmark_assignment_pending")
        )
    )

    assert payload["execution"]["status"] == "blocked"
    assert "core_benchmark_assignment_pending" in payload["execution"]["qualificationBlockers"]
    assert payload["execution"]["sourceReceipt"] is None
    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


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
    payload = deepcopy(_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = True

    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("receipt_name", "field", "value"),
    (
        ("requestReceipt", "portfolioIdHash", "sha256:" + "f" * 64),
        ("sourceReceipt", "asOfDate", "2026-07-15"),
        ("sourceReceipt", "assignmentDiagnostic", "core_benchmark_assignment_ready"),
        ("sourceReceipt", "assignmentStatus", "inactive"),
        ("evaluationReceipt", "outcome", "not_eligible"),
        ("evaluationReceipt", "missingBenchmarkReviewRequired", False),
    ),
)
def test_contract_rejects_semantic_tampering_even_with_recomputed_digest(
    receipt_name: str,
    field: str,
    value: object,
) -> None:
    payload = deepcopy(_payload())
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
        evaluation["sourceRefsDigest"] = sha256_json([dict(receipt)])
        evaluation["evaluationDigest"] = sha256_json(
            {key: item for key, item in evaluation.items() if key != "evaluationDigest"}
        )

    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


def test_contract_rejects_malformed_request_as_of_date() -> None:
    payload = deepcopy(_payload())
    request = payload["execution"]["requestReceipt"]
    request["asOfDate"] = "not-a-date"
    request["requestDigest"] = sha256_json(
        {key: item for key, item in request.items() if key != "requestDigest"}
    )

    assert not core_missing_benchmark_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "invalid_command",
    (
        lambda: replace(_command(), tenant_id=""),
        lambda: replace(_command(), book_id=" "),
        lambda: replace(_command(), correlation_id=None),
        lambda: replace(_command(), trace_id=""),
        lambda: replace(_command(), reporting_currency="US"),
        lambda: replace(_command(), evaluated_at_utc=datetime(2026, 7, 16, 13, 10)),
    ),
)
def test_command_rejects_incomplete_scope_and_time(
    invalid_command: Callable[[], EvaluateCoreMissingBenchmark],
) -> None:
    with pytest.raises(ValueError):
        invalid_command()


def _payload(
    *,
    source: AuthoritativeCoreMissingBenchmarkSource | None = None,
) -> dict[str, Any]:
    result = evaluate_core_missing_benchmark(
        _command(),
        core_source=source or AuthoritativeCoreMissingBenchmarkSource(),
    )
    return build_core_missing_benchmark_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )


def _command() -> EvaluateCoreMissingBenchmark:
    return EvaluateCoreMissingBenchmark(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=NOW.date(),
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _source_request() -> CoreBenchmarkAssignmentEvidenceRequest:
    command = _command()
    return CoreBenchmarkAssignmentEvidenceRequest(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
        as_of_date=command.as_of_date,
        evaluated_at_utc=command.evaluated_at_utc,
        reporting_currency=command.reporting_currency,
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )
