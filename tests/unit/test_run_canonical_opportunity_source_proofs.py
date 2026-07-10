from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from scripts.run_canonical_opportunity_source_proofs import (
    PROOF_CASES,
    _aggregate_payload,
    _proof_command,
    _run_proofs,
)


def test_proof_command_keeps_source_adapter_arguments_explicit() -> None:
    args = argparse.Namespace(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date="2026-04-10",
        risk_base_url="http://risk.dev.lotus",
        performance_base_url="http://performance.dev.lotus",
        period_name="1Y",
        reporting_currency="USD",
        timeout_seconds="5.0",
        correlation_id="corr-canonical-proof",
        trace_id="trace-canonical-proof",
    )

    command = _proof_command(
        case=PROOF_CASES[0],
        args=args,
        generated_at=datetime(2026, 7, 10, tzinfo=UTC),
        evaluated_at=datetime(2026, 7, 10, tzinfo=UTC),
        output_path=Path("output/opportunity/risk.json"),
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )

    assert command[0].endswith("python.exe") or command[0].endswith("python")
    assert "--risk-base-url" in command
    assert "http://risk.dev.lotus" in command
    assert "--performance-base-url" not in command
    assert "--portfolio-id" in command


def test_run_proofs_fails_closed_when_a_child_is_blocked_or_artifact_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        returncode = 3
        stdout = ""
        stderr = "source unavailable"

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        output_index = args[0].index("--output") + 1
        Path(args[0][output_index]).write_text(json.dumps({"invalid": True}), encoding="utf-8")
        return Completed()

    monkeypatch.setattr(
        "scripts.run_canonical_opportunity_source_proofs.subprocess.run",
        fake_run,
    )
    args = argparse.Namespace(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date="2026-04-10",
        risk_base_url="http://risk.dev.lotus",
        performance_base_url="http://performance.dev.lotus",
        period_name="1Y",
        reporting_currency=None,
        timeout_seconds="5.0",
        correlation_id="corr-canonical-proof",
        trace_id="trace-canonical-proof",
        source_revision="test-revision",
        source_tree_dirty=False,
    )

    summaries = _run_proofs(
        cases=PROOF_CASES,
        args=args,
        generated_at=datetime(2026, 7, 10, tzinfo=UTC),
        evaluated_at=datetime(2026, 7, 10, tzinfo=UTC),
        output_directory=tmp_path,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
    )
    payload = _aggregate_payload(
        generated_at=datetime(2026, 7, 10, tzinfo=UTC),
        evaluated_at=datetime(2026, 7, 10, tzinfo=UTC),
        portfolio_id=args.portfolio_id,
        as_of_date=args.as_of_date,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        source_revision=args.source_revision,
        source_tree_dirty=args.source_tree_dirty,
        summaries=summaries,
    )

    assert len(summaries) == 3
    assert all(summary["exitCode"] == 3 for summary in summaries)
    assert all(summary["artifactValid"] is False for summary in summaries)
    assert all("stderr" not in summary and "stdout" not in summary for summary in summaries)
    assert all(summary["processOutputSuppressed"] is True for summary in summaries)
    assert payload["certificationReady"] is False
    assert payload["portfolioScope"] == "governed_canonical"
    assert "portfolioId" not in payload
    assert payload["supportedFeaturePromoted"] is False
