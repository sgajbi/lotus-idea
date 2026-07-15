from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from copy import deepcopy

import pytest

from app.application.core_benchmark_assignment_runtime_evidence import (
    EvaluateCoreBenchmarkAssignmentReadiness,
    build_core_benchmark_assignment_runtime_execution,
    core_benchmark_assignment_runtime_execution_is_valid,
    evaluate_core_benchmark_assignment_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
)

NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
AS_OF = date(2026, 6, 21)


class RecordingSource:
    def __init__(self, evidence: CoreBenchmarkAssignmentEvidence | None = None) -> None:
        self.request: CoreBenchmarkAssignmentEvidenceRequest | None = None
        self.evidence = evidence or _evidence()

    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        self.request = request
        return self.evidence


def test_use_case_calls_port_with_exact_scope_and_builds_receipt_bound_evidence() -> None:
    source = RecordingSource()
    command = _command()

    result = evaluate_core_benchmark_assignment_readiness(command, core_source=source)
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)

    assert source.request == CoreBenchmarkAssignmentEvidenceRequest(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr",
        trace_id="trace",
    )
    assert core_benchmark_assignment_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_benchmark_assignment_source_ref_missing"
    ]
    assert payload["nonProofClaims"]["ideaPersistenceRequired"] is False
    assert "tenant-a" not in str(payload) and "portfolio-a" not in str(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("sourceReceipt", "sourceSystem"), "lotus-performance"),
        (("sourceReceipt", "asOfDate"), "2026-06-20"),
        (("sourceReceipt", "freshness"), "stale"),
        (("requestReceipt", "portfolioIdHash"), "sha256:tampered"),
        (("requestReceipt", "reportingCurrency"), "EUR"),
    ],
)
def test_validator_rejects_source_scope_and_digest_tampering(
    path: tuple[str, str], value: object
) -> None:
    payload = _valid_payload()
    payload["execution"][path[0]][path[1]] = value
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


def test_validator_rejects_unknown_or_inflated_claims() -> None:
    unknown = _valid_payload()
    unknown["productionCertified"] = True
    inflated = _valid_payload()
    inflated["nonProofClaims"]["performanceMethodologyCertified"] = True
    assert not core_benchmark_assignment_runtime_execution_is_valid(unknown)
    assert not core_benchmark_assignment_runtime_execution_is_valid(inflated)


@pytest.mark.parametrize(
    "failure_mode",
    [
        "identity_missing",
        "not_effective",
        "version_missing",
        "inactive",
        "stale",
        "future_source",
    ],
)
def test_unqualified_authoritative_evidence_cannot_clear_aggregate_blocker(
    failure_mode: str,
) -> None:
    evidence = _evidence_for_failure(failure_mode)
    result = evaluate_core_benchmark_assignment_readiness(
        _command(), core_source=RecordingSource(evidence)
    )
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)
    assert payload["aggregateBlockersSatisfied"] == []
    assert payload["execution"]["qualificationBlockers"]
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


def _valid_payload() -> dict[str, object]:
    result = evaluate_core_benchmark_assignment_readiness(_command(), core_source=RecordingSource())
    return deepcopy(
        build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)
    )


def _command() -> EvaluateCoreBenchmarkAssignmentReadiness:
    return EvaluateCoreBenchmarkAssignmentReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr",
        trace_id="trace",
    )


def _evidence() -> CoreBenchmarkAssignmentEvidence:
    return CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=_source_ref(),
        benchmark_identity_resolved=True,
        assignment_effective_for_as_of_date=True,
        assignment_status="active",
        assignment_version_present=True,
        assignment_diagnostic="core_benchmark_assignment_ready",
    )


def _evidence_for_failure(failure_mode: str) -> CoreBenchmarkAssignmentEvidence:
    evidence = _evidence()
    if failure_mode == "identity_missing":
        return replace(evidence, benchmark_identity_resolved=False)
    if failure_mode == "not_effective":
        return replace(evidence, assignment_effective_for_as_of_date=False)
    if failure_mode == "version_missing":
        return replace(evidence, assignment_version_present=False)
    if failure_mode == "inactive":
        return replace(evidence, assignment_status="inactive")
    if failure_mode == "stale":
        return replace(
            evidence,
            benchmark_assignment_ref=replace(_source_ref(), freshness=EvidenceFreshness.STALE),
        )
    if failure_mode == "future_source":
        return replace(
            evidence,
            benchmark_assignment_ref=replace(
                _source_ref(), generated_at_utc=NOW + timedelta(seconds=1)
            ),
        )
    raise AssertionError(f"unknown failure mode: {failure_mode}")


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:BenchmarkAssignment:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
        as_of_date=AS_OF,
        generated_at_utc=NOW,
        content_hash="sha256:source",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
