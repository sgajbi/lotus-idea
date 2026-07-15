from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.manage_sources import ManageMandateHealthEvidenceRequest, ManageSourceUnavailable
from tests.support.manage_mandate_runtime_evidence import AuthoritativeManageMandateSource

ROOT = Path(__file__).resolve().parents[3]


def test_generator_writes_source_safe_qualified_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    source = AuthoritativeManageMandateSource()
    monkeypatch.setattr(module, "LotusManageMandateHealthSourceAdapter", lambda _client: source)

    result = module.main(_arguments(output))

    assert result == 0
    assert len(source.requests) == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "lotus-idea.manage-mandate.runtime-execution.v2"
    assert payload["execution"]["status"] == "completed"
    assert payload["execution"]["evaluationReceipt"]["outcome"] == "candidate_created"
    serialized = json.dumps(payload)
    for forbidden in ("PB_SG_GLOBAL_BAL_001", "tenant-a", "corr-manage", "trace-manage"):
        assert forbidden not in serialized


def test_generator_writes_blocked_artifact_for_source_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(
        module,
        "LotusManageMandateHealthSourceAdapter",
        lambda _client: _UnavailableSource(),
    )

    result = module.main(_arguments(output))

    assert result == 3
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["execution"]["status"] == "blocked"
    assert payload["aggregateBlockersSatisfied"] == []
    assert "manage_temporal_identity_missing" in payload["execution"]["qualificationBlockers"]
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _arguments(output: Path) -> list[str]:
    return [
        "--manage-base-url",
        "http://localhost:8350",
        "--tenant-id",
        "tenant-a",
        "--portfolio-id",
        "PB_SG_GLOBAL_BAL_001",
        "--as-of-date",
        "2026-06-28",
        "--generated-at-utc",
        "2026-06-28T10:10:00Z",
        "--evaluated-at-utc",
        "2026-06-28T10:10:00Z",
        "--correlation-id",
        "corr-manage",
        "--trace-id",
        "trace-manage",
        "--output",
        str(output),
    ]


def _load_generator() -> ModuleType:
    path = ROOT / "scripts" / "manage_mandate_runtime_evidence" / "generate_runtime_execution.py"
    spec = importlib.util.spec_from_file_location("manage_mandate_runtime_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _UnavailableSource:
    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> object:
        raise ManageSourceUnavailable(code="manage_temporal_identity_missing")

    def close(self) -> None:
        return None
