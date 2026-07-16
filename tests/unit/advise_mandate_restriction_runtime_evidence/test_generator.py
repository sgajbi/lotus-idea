from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceUnavailable,
)
from tests.support.advise_mandate_restriction_runtime_evidence import (
    AuthoritativeAdviseMandateRestrictionSource,
)

ROOT = Path(__file__).resolve().parents[3]


def test_generator_writes_source_safe_qualified_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    source = AuthoritativeAdviseMandateRestrictionSource()
    monkeypatch.setattr(
        module,
        "LotusAdvisePolicyEvaluationSourceAdapter",
        lambda _client: source,
    )

    result = module.main(_arguments(output))

    assert result == 0
    assert len(source.requests) == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == (
        "lotus-idea.advise-mandate-restriction.runtime-execution.v2"
    )
    assert payload["execution"]["status"] == "completed"
    assert payload["execution"]["evaluationReceipt"]["outcome"] == "candidate_created"
    serialized = json.dumps(payload)
    for forbidden in (
        "tenant-a",
        "book-a",
        "portfolio-a",
        "client-a",
        "evaluation-a",
        "corr-advise",
        "trace-advise",
    ):
        assert forbidden not in serialized


def test_generator_writes_blocked_artifact_for_source_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generator()
    output = tmp_path / "runtime-execution.json"
    monkeypatch.setattr(
        module,
        "LotusAdvisePolicyEvaluationSourceAdapter",
        lambda _client: _UnavailableSource(),
    )

    result = module.main(_arguments(output))

    assert result == 3
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["execution"]["status"] == "blocked"
    assert payload["aggregateBlockersSatisfied"] == []
    assert "advise_temporal_identity_missing" in payload["execution"][
        "qualificationBlockers"
    ]
    assert "portfolio-a" not in json.dumps(payload)


def _arguments(output: Path) -> list[str]:
    return [
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
        "2026-07-15",
        "--generated-at-utc",
        "2026-07-15T10:10:00Z",
        "--evaluated-at-utc",
        "2026-07-15T10:10:00Z",
        "--correlation-id",
        "corr-advise",
        "--trace-id",
        "trace-advise",
        "--output",
        str(output),
    ]


def _load_generator() -> ModuleType:
    path = (
        ROOT
        / "scripts"
        / "advise_mandate_restriction_runtime_evidence"
        / "generate_runtime_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "advise_mandate_restriction_runtime_generator",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _UnavailableSource:
    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> object:
        raise AdviseSourceUnavailable(code="advise_temporal_identity_missing")

    def close(self) -> None:
        return None
