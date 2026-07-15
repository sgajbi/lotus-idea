from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from app.application.drawdown_review_signal import (
    evaluate_and_persist_drawdown_review_signal_from_risk,
)
from app.application.risk_drawdown_runtime_evidence import (
    RISK_DRAWDOWN_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_risk_drawdown_runtime_execution,
    build_risk_drawdown_runtime_execution,
    risk_drawdown_runtime_execution_is_valid,
)
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, InMemoryIdeaRepository
from app.ports.risk_sources import RiskDrawdownEvidence
from tests.support.risk_drawdown_runtime_evidence import (
    GENERATED_AT,
    FixedRiskDrawdownSource,
    risk_evidence,
    runtime_command,
    runtime_execution,
)


def test_runtime_execution_binds_drawdown_source_and_durable_persistence_receipts() -> None:
    payload = runtime_execution()

    assert payload["schemaVersion"] == RISK_DRAWDOWN_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_drawdown_source_proof_missing"
    ]
    execution = payload["execution"]
    assert execution["periodName"] == "YTD"
    assert execution["sourceReceipt"]["productId"] == (
        "lotus-risk:DrawdownAnalyticsReport:v1"
    )
    assert execution["persistenceReceipt"]["decision"] == "accepted"
    assert risk_drawdown_runtime_execution_is_valid(payload) is True


def test_runtime_execution_accepts_authoritative_repository_replay() -> None:
    repository = InMemoryIdeaRepository()
    first = runtime_execution(repository=repository)
    replay = runtime_execution(repository=repository)

    assert first["execution"]["persistenceReceipt"]["decision"] == "accepted"
    assert replay["execution"]["persistenceReceipt"]["decision"] == "replayed"
    assert risk_drawdown_runtime_execution_is_valid(replay) is True


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("productionCertified",), True),
        (("execution", "unexpectedClaim"), True),
        (("execution", "sourceReceipt", "runtimeApproved"), True),
        (("execution", "persistenceReceipt", "candidateId"), "forged"),
        (("nonProofClaims", "volatilityRuntimeCertified"), True),
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

    assert risk_drawdown_runtime_execution_is_valid(payload) is False


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

    assert risk_drawdown_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "evidence",
    (
        risk_evidence(freshness=EvidenceFreshness.STALE),
        risk_evidence(as_of_date=GENERATED_AT.date() + timedelta(days=1)),
    ),
)
def test_runtime_execution_rejects_stale_or_mismatched_source_identity(
    evidence: RiskDrawdownEvidence,
) -> None:
    payload = runtime_execution(evidence=evidence)

    assert payload["aggregateBlockersSatisfied"] == []
    assert risk_drawdown_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_non_candidate_outcome() -> None:
    payload = runtime_execution(evidence=risk_evidence(max_drawdown=Decimal("-0.02")))

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert risk_drawdown_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_in_memory_posture() -> None:
    payload = runtime_execution(durable_storage_backed=False)

    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert risk_drawdown_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_non_persisting_conflict_result() -> None:
    command = runtime_command()
    result = evaluate_and_persist_drawdown_review_signal_from_risk(
        command,
        risk_source=FixedRiskDrawdownSource(risk_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None
    conflict = replace(
        result,
        persistence=replace(result.persistence, decision=CandidatePersistenceDecision.CONFLICT),
    )

    payload = build_risk_drawdown_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=conflict,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert risk_drawdown_runtime_execution_is_valid(payload) is False


def test_blocked_runtime_execution_preserves_source_and_storage_failures() -> None:
    payload = build_blocked_risk_drawdown_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=runtime_command(),
        error_code="",
        durable_storage_backed=False,
    )

    assert payload["execution"]["qualificationBlockers"] == [
        "source_error_risk_source_unavailable",
        "durable_repository_not_configured",
        "authoritative_source_receipt_missing",
        "persistence_receipt_missing",
    ]
    assert risk_drawdown_runtime_execution_is_valid(payload) is False


def test_runtime_execution_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_blocked_risk_drawdown_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            command=runtime_command(),
            error_code="risk_source_unavailable",
            durable_storage_backed=True,
        )
