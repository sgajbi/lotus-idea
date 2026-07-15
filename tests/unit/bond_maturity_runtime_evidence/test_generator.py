from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.application.bond_maturity_runtime_evidence import (
    bond_maturity_runtime_execution_is_valid,
)
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreSourceUnavailable,
)
from scripts.bond_maturity_runtime_evidence import generate_runtime_execution
from tests.support.bond_maturity_runtime_evidence import (
    AuthoritativeCoreBondMaturitySource,
)


class UnavailableCoreSource(AuthoritativeCoreBondMaturitySource):
    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        raise CoreSourceUnavailable(code="core_maturity_source_unavailable")


class UnknownReconciliationSource(AuthoritativeCoreBondMaturitySource):
    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        evidence = super().fetch_bond_maturity_evidence(request)
        return replace(evidence, reconciliation_status="UNKNOWN")


@pytest.mark.parametrize(
    ("source", "expected_exit", "expected_status", "opportunity_detected"),
    [
        (AuthoritativeCoreBondMaturitySource(), 0, "completed", True),
        (AuthoritativeCoreBondMaturitySource(opportunity_detected=False), 0, "completed", False),
        (UnknownReconciliationSource(), 3, "completed", True),
        (UnavailableCoreSource(), 3, "blocked", False),
    ],
)
def test_generator_routes_through_use_case_and_writes_truthful_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: AuthoritativeCoreBondMaturitySource,
    expected_exit: int,
    expected_status: str,
    opportunity_detected: bool,
) -> None:
    output = tmp_path / "bond-maturity-live-proof.json"
    monkeypatch.setattr(
        generate_runtime_execution,
        "LotusCoreHighCashSourceAdapter",
        lambda _client: source,
    )

    exit_code = generate_runtime_execution.main(_args(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == expected_exit
    assert payload["execution"]["status"] == expected_status
    assert payload["execution"]["opportunityDetected"] is opportunity_detected
    assert bond_maturity_runtime_execution_is_valid(payload) is (expected_exit == 0)
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "tenant-a" not in serialized
    assert "corr-secret" not in serialized
    assert "trace-secret" not in serialized


def test_generator_rejects_invalid_configuration_without_artifact(tmp_path: Path) -> None:
    output = tmp_path / "bond-maturity-live-proof.json"
    args = _args(output)
    args[args.index("2026-06-21")] = "not-a-date"

    assert generate_runtime_execution.main(args) == 2
    assert not output.exists()


def _args(output: Path) -> list[str]:
    return [
        "--core-query-base-url",
        "http://localhost:8000",
        "--tenant-id",
        "tenant-a",
        "--portfolio-id",
        "PB_SG_GLOBAL_BAL_001",
        "--as-of-date",
        "2026-06-21",
        "--maturity-window-days",
        "30",
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
