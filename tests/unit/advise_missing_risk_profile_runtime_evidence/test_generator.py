from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from tests.support.advise_missing_risk_profile_runtime_evidence import (
    AuthoritativeAdviseMissingRiskProfileSource,
)

ROOT = Path(__file__).resolve().parents[3]


def test_generator_invokes_one_source_fetch_and_writes_closed_v2_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    source = AuthoritativeAdviseMissingRiskProfileSource()
    monkeypatch.setattr(module, "LotusAdvisePolicyEvaluationSourceAdapter", lambda _client: source)
    output = tmp_path / "runtime-execution.json"

    result = module.main(
        [
            "--advise-base-url",
            "http://localhost:8340",
            "--tenant-id",
            "tenant-a",
            "--book-id",
            "book-a",
            "--portfolio-id",
            "portfolio-a",
            "--client-id",
            "client-a",
            "--evaluation-id",
            "evaluation-a",
            "--as-of-date",
            "2026-07-16",
            "--generated-at-utc",
            "2026-07-16T11:10:00Z",
            "--evaluated-at-utc",
            "2026-07-16T11:10:00Z",
            "--correlation-id",
            "corr-advise",
            "--trace-id",
            "trace-advise",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert len(source.requests) == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == (
        "lotus-idea.advise-missing-risk-profile.runtime-execution.v2"
    )
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["execution"]["qualificationBlockers"] == []


def _load_generator() -> ModuleType:
    path = (
        ROOT
        / "scripts"
        / "advise_missing_risk_profile_runtime_evidence"
        / "generate_runtime_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "generate_advise_missing_risk_profile_runtime_execution",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
