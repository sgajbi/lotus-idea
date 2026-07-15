from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

import pytest

from app.application.high_volatility_runtime_evidence import (
    HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_high_volatility_runtime_execution,
    build_high_volatility_runtime_execution,
    high_volatility_runtime_execution_is_valid,
)
from app.application.high_volatility_signal import (
    evaluate_and_persist_high_volatility_signal_from_risk,
)
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, InMemoryIdeaRepository
from app.ports.risk_sources import RiskVolatilityEvidence
from scripts.high_volatility_runtime_evidence import generate_runtime_execution
from tests.support.high_volatility_runtime_evidence import (
    GENERATED_AT,
    FixedRiskVolatilitySource,
    risk_evidence,
    runtime_command,
    runtime_execution,
)


class DurableIdeaRepository(InMemoryIdeaRepository):
    durable_storage_backed = True


def test_runtime_execution_binds_risk_source_and_durable_persistence_receipts() -> None:
    payload = runtime_execution()

    assert payload["schemaVersion"] == HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_live_risk_volatility_source_proof_missing"
    ]
    execution = payload["execution"]
    assert execution["periodName"] == "YTD"
    assert execution["sourceReceipt"]["productId"] == "lotus-risk:RiskMetricsReport:v1"
    assert execution["persistenceReceipt"]["decision"] == "accepted"
    assert high_volatility_runtime_execution_is_valid(payload) is True


def test_runtime_execution_accepts_authoritative_repository_replay() -> None:
    repository = InMemoryIdeaRepository()
    first = runtime_execution(repository=repository)
    replay = runtime_execution(repository=repository)

    assert first["execution"]["persistenceReceipt"]["decision"] == "accepted"
    assert replay["execution"]["persistenceReceipt"]["decision"] == "replayed"
    assert high_volatility_runtime_execution_is_valid(replay) is True


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("productionCertified",), True),
        (("execution", "unexpectedClaim"), True),
        (("execution", "sourceReceipt", "runtimeApproved"), True),
        (("execution", "persistenceReceipt", "candidateId"), "forged"),
    ),
)
def test_runtime_execution_rejects_unknown_claims(path: tuple[str, ...], value: object) -> None:
    payload = deepcopy(runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert high_volatility_runtime_execution_is_valid(payload) is False


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

    assert high_volatility_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("schemaVersion",), "lotus-idea.high-volatility.runtime-execution.v1"),
        (("repository",), "lotus-risk"),
        (("evidenceClass",), "source_contract"),
        (("proofFamily",), "portfolio_risk"),
        (("proofType",), "calculation"),
        (("sourceAuthority",), "lotus-core"),
        (("generatedAtUtc",), "not-a-timestamp"),
        (("execution",), None),
        (("nonProofClaims",), None),
        (("nonProofClaims", "officialRiskCalculationOwned"), "lotus-idea"),
        (("nonProofClaims", "drawdownRuntimeCertified"), True),
        (("remainingCertificationBlockers",), []),
        (("evidenceRefs",), []),
        (("aggregateBlockersSatisfied",), []),
        (("execution", "status"), "blocked"),
        (("execution", "qualificationBlockers"), ["untrusted"]),
        (("execution", "evaluatedAtUtc"), "not-a-timestamp"),
        (("execution", "asOfDate"), "not-a-date"),
        (("execution", "periodName"), ""),
        (("execution", "requestFingerprint"), "sha256:invalid"),
        (("execution", "sourceReceipt"), None),
        (("execution", "persistenceReceipt"), None),
        (("execution", "sourceReceipt", "productId"), "lotus-risk:Other:v1"),
        (("execution", "sourceReceipt", "asOfDate"), "2026-06-20"),
        (("execution", "sourceReceipt", "productVersion"), ""),
        (("execution", "sourceReceipt", "generatedAtUtc"), "2026-06-21T10:01:00Z"),
        (("execution", "persistenceReceipt", "candidateFamily"), "concentration"),
        (("execution", "persistenceReceipt", "sourceEvidenceHash"), "invalid"),
        (("execution", "persistenceReceipt", "persistedAtUtc"), "2026-06-21T10:11:00Z"),
    ),
)
def test_runtime_execution_rejects_contract_and_authority_drift(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_in_memory_posture() -> None:
    payload = runtime_execution(durable_storage_backed=False)

    assert payload["aggregateBlockersSatisfied"] == []
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_blocked_runtime_execution_preserves_source_and_storage_failures() -> None:
    payload = build_blocked_high_volatility_runtime_execution(
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
    assert payload["aggregateBlockersSatisfied"] == []
    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_runtime_execution_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_blocked_high_volatility_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            command=runtime_command(),
            error_code="risk_source_unavailable",
            durable_storage_backed=True,
        )


def test_runtime_execution_rejects_non_persisting_conflict_result() -> None:
    command = runtime_command()
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        command,
        risk_source=FixedRiskVolatilitySource(risk_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None
    conflict = replace(
        result,
        persistence=replace(result.persistence, decision=CandidatePersistenceDecision.CONFLICT),
    )

    payload = build_high_volatility_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=conflict,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_persisted_candidate_identity_drift() -> None:
    command = runtime_command()
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        command,
        risk_source=FixedRiskVolatilitySource(risk_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None and result.persistence.record is not None
    drifted_record = replace(
        result.persistence.record,
        candidate=replace(
            result.persistence.record.candidate,
            candidate_id=f"{result.persistence.record.candidate.candidate_id}_drift",
        ),
    )
    drifted = replace(result, persistence=replace(result.persistence, record=drifted_record))

    payload = build_high_volatility_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=drifted,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert high_volatility_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "evidence",
    (
        risk_evidence(freshness=EvidenceFreshness.STALE),
        risk_evidence(as_of_date=GENERATED_AT.date() + timedelta(days=1)),
    ),
)
def test_runtime_execution_rejects_stale_or_mismatched_source_identity(
    evidence: RiskVolatilityEvidence,
) -> None:
    payload = runtime_execution(evidence=evidence)

    assert payload["aggregateBlockersSatisfied"] == []
    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_below_threshold_non_candidate() -> None:
    payload = runtime_execution(evidence=risk_evidence(volatility=Decimal("8")))

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert high_volatility_runtime_execution_is_valid(payload) is False


def test_runtime_execution_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(generate_runtime_execution, "get_idea_repository", DurableIdeaRepository)
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusRiskVolatilitySourceAdapter",
        lambda _client: FixedRiskVolatilitySource(risk_evidence()),
    )

    result = generate_runtime_execution.main(
        [
            "--risk-base-url",
            "http://risk.test",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:00:00Z",
            "--correlation-id",
            "sensitive-correlation",
            "--trace-id",
            "sensitive-trace",
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    assert result == 0
    assert high_volatility_runtime_execution_is_valid(payload) is True
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "sensitive-correlation" not in serialized
    assert "sensitive-trace" not in serialized


def test_runtime_execution_cli_fails_closed_without_durable_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(generate_runtime_execution, "get_idea_repository", InMemoryIdeaRepository)
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusRiskVolatilitySourceAdapter",
        lambda _client: FixedRiskVolatilitySource(risk_evidence()),
    )

    result = generate_runtime_execution.main(
        [
            "--risk-base-url",
            "http://risk.test",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:00:00Z",
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 3
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
