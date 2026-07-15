from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from typing import Any

import pytest

from app.application.risk_concentration_runtime_evidence import (
    RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    risk_concentration_runtime_execution_is_valid,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository
from app.ports.risk_sources import RiskConcentrationEvidence
from tests.support.risk_concentration_runtime_evidence import (
    GENERATED_AT,
    risk_evidence,
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


def test_runtime_execution_rejects_in_memory_posture() -> None:
    payload = runtime_execution(durable_storage_backed=False)

    assert payload["aggregateBlockersSatisfied"] == []
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]
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
