from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.ai_lineage_store_proof import REQUIRED_AI_LINEAGE_STORE_ASSERTIONS
from app.application.ai_lineage_store_proof.ci_receipt import (
    build_postgres_ci_execution_receipt,
)
from app.domain.proof_evidence import CIExecutionReceipt


def test_builds_digest_bound_receipt_from_governed_postgres_test(tmp_path: Path) -> None:
    report = _write_report(tmp_path)

    receipt = build_postgres_ci_execution_receipt(
        test_report_path=report,
        repository="sgajbi/lotus-idea",
        workflow_path=".github/workflows/main-releasability.yml",
        workflow_name="Main Releasability Gate",
        job_name="Main Releasability / PostgreSQL Runtime Proof",
        run_id=123,
        run_attempt=2,
        source_commit_sha="a" * 40,
        source_ref="refs/heads/main",
        conclusion="success",
        completed_at_utc=datetime(2026, 7, 14, 4, 0, tzinfo=UTC),
    )

    assert receipt.run_id == 123
    assert receipt.run_attempt == 2
    assert receipt.artifact_sha256.startswith("sha256:")
    assert len(receipt.artifact_sha256) == 71
    assert receipt.assertions == REQUIRED_AI_LINEAGE_STORE_ASSERTIONS


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_rejects_nonpassing_governed_postgres_test(tmp_path: Path, outcome: str) -> None:
    report = _write_report(tmp_path, outcome=outcome)

    with pytest.raises(ValueError, match="did not pass"):
        _build(report)


def test_rejects_report_without_governed_postgres_test(tmp_path: Path) -> None:
    report = _write_report(tmp_path, test_name="test_unrelated")

    with pytest.raises(ValueError, match="must contain the governed AI lineage test once"):
        _build(report)


def test_rejects_malformed_or_aggregate_failed_report(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.xml"
    malformed.write_text("not xml", encoding="utf-8")
    with pytest.raises(ValueError, match="unavailable or malformed"):
        _build(malformed)

    report = _write_report(tmp_path, failures="1")
    with pytest.raises(ValueError, match="contains failed tests"):
        _build(report)


def _build(report: Path) -> CIExecutionReceipt:
    return build_postgres_ci_execution_receipt(
        test_report_path=report,
        repository="sgajbi/lotus-idea",
        workflow_path=".github/workflows/main-releasability.yml",
        workflow_name="Main Releasability Gate",
        job_name="Main Releasability / PostgreSQL Runtime Proof",
        run_id=123,
        run_attempt=1,
        source_commit_sha="a" * 40,
        source_ref="refs/heads/main",
        conclusion="success",
        completed_at_utc=datetime(2026, 7, 14, 4, 0, tzinfo=UTC),
    )


def _write_report(
    tmp_path: Path,
    *,
    outcome: str | None = None,
    test_name: str = "test_postgres_runtime_provider_persists_ai_explanation_lineage",
    failures: str = "0",
) -> Path:
    outcome_element = f"<{outcome} />" if outcome else ""
    report = tmp_path / f"report-{outcome or test_name}.xml"
    report.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites tests="1" failures="{failures}" errors="0">
  <testsuite name="pytest" tests="1" failures="{failures}" errors="0">
    <testcase classname="tests.integration.test_postgres_runtime_integration"
              name="{test_name}">{outcome_element}</testcase>
  </testsuite>
</testsuites>
""".format(failures=failures, test_name=test_name, outcome_element=outcome_element),
        encoding="utf-8",
    )
    return report
