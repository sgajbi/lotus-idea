from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.application.core_portfolio_state_runtime_evidence import (
    core_portfolio_state_runtime_execution_is_valid,
)
from app.ports.core_sources import (
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
    CoreSourceUnavailable,
)
from scripts.core_portfolio_state_runtime_evidence import generate_runtime_execution
from tests.support.core_portfolio_state_runtime_evidence import (
    AuthoritativeCorePortfolioStateSource,
)


class UnavailableCoreSource:
    def fetch_portfolio_state_evidence(self, request: CorePortfolioStateEvidenceRequest) -> object:
        raise CoreSourceUnavailable(code="core_portfolio_state_source_unavailable")


class MissingSnapshotIdentitySource(AuthoritativeCorePortfolioStateSource):
    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        evidence = super().fetch_portfolio_state_evidence(request)
        return replace(evidence, snapshot_id=None)


@pytest.mark.parametrize(
    ("source", "expected_exit", "expected_status"),
    [
        (AuthoritativeCorePortfolioStateSource(), 0, "completed"),
        (MissingSnapshotIdentitySource(), 3, "completed"),
        (UnavailableCoreSource(), 3, "blocked"),
    ],
)
def test_generator_routes_through_use_case_and_writes_truthful_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: object,
    expected_exit: int,
    expected_status: str,
) -> None:
    output = tmp_path / "core-portfolio-state-runtime-execution.json"
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: source,
    )

    exit_code = generate_runtime_execution.main(_args(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == expected_exit
    assert payload["execution"]["status"] == expected_status
    assert core_portfolio_state_runtime_execution_is_valid(payload) is (expected_exit == 0)
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "tenant-a" not in serialized
    assert "corr-secret" not in serialized
    assert "trace-secret" not in serialized


def test_generator_rejects_invalid_configuration_without_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "core-portfolio-state-runtime-execution.json"
    args = _args(output)
    args[args.index("2026-06-21")] = "not-a-date"

    assert generate_runtime_execution.main(args) == 2
    assert not output.exists()


def _args(output: Path) -> list[str]:
    return [
        "--core-query-control-plane-base-url",
        "http://localhost:8101",
        "--tenant-id",
        "tenant-a",
        "--portfolio-id",
        "PB_SG_GLOBAL_BAL_001",
        "--as-of-date",
        "2026-06-21",
        "--generated-at-utc",
        "2026-06-21T10:10:00Z",
        "--evaluated-at-utc",
        "2026-06-21T10:10:00Z",
        "--correlation-id",
        "corr-secret",
        "--trace-id",
        "trace-secret",
        "--output",
        str(output),
    ]
