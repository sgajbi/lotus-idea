from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pytest

from app.application.risk_concentration_runtime_evidence import (
    RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_risk_concentration_runtime_execution,
    build_risk_concentration_runtime_execution,
    risk_concentration_runtime_execution_is_valid,
)
from app.application.concentration_risk_signal import (
    evaluate_and_persist_concentration_risk_signal_from_risk,
)
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, InMemoryIdeaRepository
from app.ports.risk_sources import RiskConcentrationEvidence
from tests.support.risk_concentration_runtime_evidence import (
    GENERATED_AT,
    risk_evidence,
    runtime_command,
    runtime_execution,
    FixedRiskConcentrationSource,
)
from scripts.risk_concentration_runtime_evidence import generate_runtime_execution


class DurableIdeaRepository(InMemoryIdeaRepository):
    durable_storage_backed = True


def test_runtime_execution_binds_risk_source_and_durable_persistence_receipts() -> None:
    payload = runtime_execution()

    assert payload["schemaVersion"] == RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_live_risk_source_proof_missing"
    ]
    execution = payload["execution"]
    assert isinstance(execution, dict)
    assert execution["durableStorageBacked"] is True
    assert execution["qualificationBlockers"] == []
    assert execution["sourceReceipt"]["sourceSystem"] == "lotus-risk"
    assert execution["persistenceReceipt"]["decision"] == "accepted"
    assert risk_concentration_runtime_execution_is_valid(payload) is True


def test_runtime_execution_accepts_authoritative_repository_replay() -> None:
    repository = InMemoryIdeaRepository()
    first = runtime_execution(repository=repository)
    replay = runtime_execution(repository=repository)

    assert first["execution"]["persistenceReceipt"]["decision"] == "accepted"
    assert replay["execution"]["persistenceReceipt"]["decision"] == "replayed"
    assert risk_concentration_runtime_execution_is_valid(replay) is True


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

    assert risk_concentration_runtime_execution_is_valid(payload) is False


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
    receipt_name: str, field: str, value: object
) -> None:
    payload = deepcopy(runtime_execution())
    payload["execution"][receipt_name][field] = value

    assert risk_concentration_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("schemaVersion",), "lotus-idea.risk-concentration.runtime-execution.v1"),
        (("repository",), "lotus-risk"),
        (("evidenceClass",), "source_contract"),
        (("proofFamily",), "portfolio_risk"),
        (("proofType",), "calculation"),
        (("sourceAuthority",), "lotus-core"),
        (("generatedAtUtc",), "not-a-timestamp"),
        (("execution",), None),
        (("nonProofClaims",), None),
        (("nonProofClaims", "officialRiskCalculationOwned"), "lotus-idea"),
        (("nonProofClaims", "deploymentCertified"), True),
        (("remainingCertificationBlockers",), []),
        (("evidenceRefs",), []),
        (("aggregateBlockersSatisfied",), []),
        (("execution", "status"), "blocked"),
        (("execution", "qualificationBlockers"), ["untrusted"]),
        (("execution", "evaluatedAtUtc"), "not-a-timestamp"),
        (("execution", "asOfDate"), "not-a-date"),
        (("execution", "requestFingerprint"), "sha256:invalid"),
        (("execution", "sourceReceipt"), None),
        (("execution", "persistenceReceipt"), None),
        (("execution", "sourceReceipt", "productId"), "lotus-risk:Other:v1"),
        (("execution", "sourceReceipt", "asOfDate"), "2026-06-20"),
        (("execution", "sourceReceipt", "productVersion"), ""),
        (("execution", "sourceReceipt", "generatedAtUtc"), "2026-06-21T10:01:00Z"),
        (("execution", "persistenceReceipt", "candidateFamily"), "underperformance"),
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

    assert risk_concentration_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_in_memory_posture() -> None:
    payload = runtime_execution(durable_storage_backed=False)

    assert payload["aggregateBlockersSatisfied"] == []
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
    assert risk_concentration_runtime_execution_is_valid(payload) is False


def test_blocked_runtime_execution_preserves_source_and_storage_failures() -> None:
    payload = build_blocked_risk_concentration_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=runtime_command(),
        error_code="",
        durable_storage_backed=False,
    )

    assert payload["execution"]["status"] == "blocked"
    assert payload["execution"]["qualificationBlockers"] == [
        "source_error_risk_source_unavailable",
        "durable_repository_not_configured",
        "authoritative_source_receipt_missing",
        "persistence_receipt_missing",
    ]
    assert payload["aggregateBlockersSatisfied"] == []
    assert risk_concentration_runtime_execution_is_valid(payload) is False


def test_runtime_execution_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_blocked_risk_concentration_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            command=runtime_command(),
            error_code="risk_source_unavailable",
            durable_storage_backed=True,
        )


def test_runtime_execution_rejects_non_persisting_conflict_result() -> None:
    command = runtime_command()
    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        command,
        risk_source=FixedRiskConcentrationSource(risk_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None
    conflict = replace(
        result,
        persistence=replace(
            result.persistence,
            decision=CandidatePersistenceDecision.CONFLICT,
        ),
    )

    payload = build_risk_concentration_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=conflict,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert risk_concentration_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_persisted_candidate_identity_drift() -> None:
    command = runtime_command()
    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        command,
        risk_source=FixedRiskConcentrationSource(risk_evidence()),
        repository=InMemoryIdeaRepository(),
    )
    assert result.persistence is not None
    assert result.persistence.record is not None
    drifted_record = replace(
        result.persistence.record,
        candidate=replace(
            result.persistence.record.candidate,
            candidate_id=f"{result.persistence.record.candidate.candidate_id}_drift",
        ),
    )
    drifted = replace(
        result,
        persistence=replace(result.persistence, record=drifted_record),
    )

    payload = build_risk_concentration_runtime_execution(
        generated_at_utc=GENERATED_AT,
        command=command,
        result=drifted,
        durable_storage_backed=True,
    )

    assert "persistence_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert risk_concentration_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "evidence",
    (
        risk_evidence(freshness=EvidenceFreshness.STALE),
        risk_evidence(as_of_date=GENERATED_AT.date() + timedelta(days=1)),
    ),
)
def test_runtime_execution_rejects_stale_or_mismatched_source_identity(
    evidence: RiskConcentrationEvidence,
) -> None:
    payload = runtime_execution(evidence=evidence)

    assert payload["aggregateBlockersSatisfied"] == []
    assert risk_concentration_runtime_execution_is_valid(payload) is False


def test_runtime_execution_cli_uses_authoritative_use_case_and_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(generate_runtime_execution, "get_idea_repository", DurableIdeaRepository)
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusRiskConcentrationSourceAdapter",
        lambda _client: FixedRiskConcentrationSource(risk_evidence()),
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
    assert risk_concentration_runtime_execution_is_valid(payload) is True
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
        "LotusRiskConcentrationSourceAdapter",
        lambda _client: FixedRiskConcentrationSource(risk_evidence()),
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
    assert payload["aggregateBlockersSatisfied"] == []
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
