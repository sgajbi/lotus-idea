from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.core_sources import CoreSourceUnavailable
from tests.support.low_income_cashflow_runtime_evidence import AuthoritativeCoreLowIncomeSource

ROOT = Path(__file__).resolve().parents[3]


def test_generator_writes_source_safe_qualified_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: AuthoritativeCoreLowIncomeSource(),
    )

    result = module.main(_arguments(output))

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "lotus-idea.low-income-cashflow.runtime-execution.v2"
    assert payload["execution"]["status"] == "completed"
    assert payload["execution"]["evaluationReceipt"]["outcome"] == "candidate_created"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_live_core_cashflow_source_proof_missing"
    ]
    serialized = json.dumps(payload)
    for forbidden in ("PB_SG_GLOBAL_BAL_001", "tenant-a", "corr-a", "trace-a"):
        assert forbidden not in serialized


def test_generator_writes_blocked_artifact_for_source_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: _UnavailableSource(),
    )

    result = module.main(_arguments(output))

    assert result == 3
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["execution"]["status"] == "blocked"
    assert payload["aggregateBlockersSatisfied"] == []
    assert "core_cashflow_source_unavailable" in payload["execution"]["qualificationBlockers"]
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _arguments(output: Path) -> list[str]:
    return [
        "--core-query-base-url",
        "http://localhost:8100",
        "--tenant-id",
        "tenant-a",
        "--portfolio-id",
        "PB_SG_GLOBAL_BAL_001",
        "--as-of-date",
        "2026-06-21",
        "--horizon-days",
        "30",
        "--generated-at-utc",
        "2026-06-21T10:10:00Z",
        "--evaluated-at-utc",
        "2026-06-21T10:10:00Z",
        "--correlation-id",
        "corr-a",
        "--trace-id",
        "trace-a",
        "--output",
        str(output),
    ]


def _load_generator() -> ModuleType:
    path = (
        ROOT / "scripts" / "low_income_cashflow_runtime_evidence" / "generate_runtime_execution.py"
    )
    spec = importlib.util.spec_from_file_location("low_income_cashflow_runtime_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _UnavailableSource:
    def fetch_low_income_evidence(self, request: object) -> object:
        raise CoreSourceUnavailable(code="core_cashflow_source_unavailable")

    def close(self) -> None:
        return None
