from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from app.application.performance_underperformance_runtime_evidence import (
    PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_performance_underperformance_runtime_execution,
    build_performance_underperformance_runtime_execution,
    performance_underperformance_runtime_execution_is_valid,
)
from app.application.underperformance_signal import (
    evaluate_and_persist_underperformance_signal_from_performance,
)
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, InMemoryIdeaRepository
from app.ports.performance_sources import PerformanceUnderperformanceEvidence
from tests.support.performance_underperformance_runtime_evidence import (
    GENERATED_AT,
    FixedPerformanceUnderperformanceSource,
    performance_evidence,
    runtime_command,
    runtime_execution,
)


def test_runtime_execution_binds_performance_source_and_persistence_receipts() -> None:
    payload = runtime_execution()

    assert payload["schemaVersion"] == PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_live_performance_source_proof_missing"
    ]
    execution = payload["execution"]
    assert execution["sourceReceipt"]["productId"] == (
        "lotus-performance:ReturnsSeriesBundle:v1"
    )
    assert execution["persistenceReceipt"]["decision"] == "accepted"
    assert performance_underperformance_runtime_execution_is_valid(payload) is True


def test_runtime_execution_accepts_authoritative_repository_replay() -> None:
    repository = InMemoryIdeaRepository()

    accepted = runtime_execution(repository=repository)
    replayed = runtime_execution(repository=repository)

    assert accepted["execution"]["persistenceReceipt"]["decision"] == "accepted"
    assert replayed["execution"]["persistenceReceipt"]["decision"] == "replayed"
    assert performance_underperformance_runtime_execution_is_valid(replayed) is True


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("productionCertified",), True),
        (("execution", "unexpectedClaim"), True),
        (("execution", "sourceReceipt", "runtimeApproved"), True),
        (("execution", "persistenceReceipt", "candidateId"), "forged"),
        (("nonProofClaims", "benchmarkAssignmentCertified"), True),
    ),
)
def test_runtime_execution_rejects_unknown_or_inflated_claims(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert performance_underperformance_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("schemaVersion",), "lotus-idea.performance-underperformance.runtime-execution.v1"),
        (("repository",), "lotus-performance"),
        (("evidenceClass",), "source_contract"),
        (("proofFamily",), "risk_drawdown"),
        (("proofType",), "official_performance_calculation"),
        (("sourceAuthority",), "lotus-idea"),
        (("nonProofClaims",), {}),
        (("nonProofClaims", "officialPerformanceCalculationOwned"), "lotus-idea"),
        (("remainingCertificationBlockers",), []),
        (("evidenceRefs",), []),
    ),
)
def test_runtime_execution_rejects_authority_or_readiness_substitution(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert performance_underperformance_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("receipt_name", "field", "value"),
    (
        ("sourceReceipt", "contentHash", "sha256:forged"),
        ("sourceReceipt", "freshness", "stale"),
        ("persistenceReceipt", "sourceEvidenceHash", "sha256:" + "0" * 64),
        ("persistenceReceipt", "scopeFingerprint", "sha256:" + "1" * 64),
        ("persistenceReceipt", "decision", "conflict"),
    ),
)
def test_runtime_execution_rejects_forged_receipts(
    receipt_name: str,
    field: str,
    value: object,
) -> None:
    payload = deepcopy(runtime_execution())
    payload["execution"][receipt_name][field] = value

    assert performance_underperformance_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "evidence",
    (
        performance_evidence(freshness=EvidenceFreshness.STALE),
        performance_evidence(as_of_date=GENERATED_AT.date() + timedelta(days=1)),
    ),
)
def test_runtime_execution_rejects_stale_or_mismatched_source_identity(
    evidence: PerformanceUnderperformanceEvidence,
) -> None:
    payload = runtime_execution(evidence=evidence)

    assert payload["aggregateBlockersSatisfied"] == []
    assert performance_underperformance_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "evidence",
    (
        performance_evidence(active_return=Decimal("-0.001")),
        performance_evidence(benchmark_context_available=False),
    ),
)
def test_runtime_execution_rejects_non_candidate_or_missing_benchmark(
    evidence: PerformanceUnderperformanceEvidence,
) -> None:
    payload = runtime_execution(evidence=evidence)

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert performance_underperformance_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_in_memory_posture() -> None:
    payload = runtime_execution(durable_storage_backed=False)

    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
    assert performance_underperformance_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_non_persisting_conflict() -> None:
    command = runtime_command()
    result = evaluate_and_persist_underperformance_signal_from_performance(
        command,
        performance_source=FixedPerformanceUnderperformanceSource(performance_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None
    conflict = replace(
        result,
        persistence=replace(result.persistence, decision=CandidatePersistenceDecision.CONFLICT),
    )

    payload = build_performance_underperformance_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=conflict,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert performance_underperformance_runtime_execution_is_valid(payload) is False


def test_blocked_runtime_execution_preserves_source_and_storage_failures() -> None:
    payload = build_blocked_performance_underperformance_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=runtime_command(),
        error_code="",
        durable_storage_backed=False,
    )

    assert payload["execution"]["qualificationBlockers"] == [
        "source_error_performance_source_unavailable",
        "durable_repository_not_configured",
        "authoritative_source_receipt_missing",
        "persistence_receipt_missing",
    ]
    assert performance_underperformance_runtime_execution_is_valid(payload) is False


def test_runtime_execution_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_blocked_performance_underperformance_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            command=runtime_command(),
            error_code="performance_source_unavailable",
            durable_storage_backed=True,
        )
