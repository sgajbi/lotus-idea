from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.durable_repository_proof import (
    REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    build_durable_repository_ci_execution_receipt,
)
from app.domain.proof_evidence import CIExecutionReceipt


ROOT = Path(__file__).resolve().parents[3]
TEST_CASES = (
    (
        "tests.integration.test_postgres_runtime_integration",
        "test_postgres_migration_rollback_and_reapply_restores_runtime_contract",
    ),
    (
        "tests.integration.test_postgres_runtime_integration",
        "test_postgres_runtime_provider_persists_api_state_across_reloaded_connections",
    ),
    (
        "tests.integration.persistence.test_candidate_persistence_runtime",
        "test_postgres_runtime_serializes_candidate_identity_and_idempotency_races",
    ),
    (
        "tests.integration.test_postgres_review_queue_runtime",
        "test_postgres_review_queue_preserves_snapshot_across_future_insert_and_rejects_stale_token",
    ),
)


def test_builds_digest_bound_receipt_from_governed_postgres_tests(tmp_path: Path) -> None:
    receipt = _build(_write_report(tmp_path))

    assert receipt.artifact_sha256.startswith("sha256:")
    assert len(receipt.artifact_sha256) == 71
    assert receipt.assertions == REQUIRED_DURABLE_REPOSITORY_ASSERTIONS


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_rejects_nonpassing_governed_postgres_test(tmp_path: Path, outcome: str) -> None:
    report = _write_report(tmp_path, outcome=outcome)

    with pytest.raises(ValueError, match="did not pass"):
        _build(report)


def test_rejects_report_missing_governed_test(tmp_path: Path) -> None:
    report = _write_report(tmp_path, omitted_test=TEST_CASES[-1])

    with pytest.raises(ValueError, match="must contain each governed"):
        _build(report)


def test_rejects_malformed_aggregate_failed_or_invalid_count_report(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.xml"
    malformed.write_text("not xml", encoding="utf-8")
    with pytest.raises(ValueError, match="unavailable or malformed"):
        _build(malformed)

    with pytest.raises(ValueError, match="contains failed tests"):
        _build(_write_report(tmp_path, failures="1"))

    with pytest.raises(ValueError, match="invalid failures count"):
        _build(_write_report(tmp_path, failures="invalid"))


def test_accepts_explicit_canonical_artifact_digest(tmp_path: Path) -> None:
    receipt = _build(_write_report(tmp_path), artifact_sha256=f"sha256:{'c' * 64}")

    assert receipt.artifact_sha256 == f"sha256:{'c' * 64}"


def test_rejects_malformed_artifact_digest(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="artifact SHA-256"):
        _build(_write_report(tmp_path), artifact_sha256="not-a-digest")


def test_receipt_cli_writes_observed_execution_identity(tmp_path: Path) -> None:
    report = _write_report(tmp_path)
    output = tmp_path / "receipt.json"

    result = _load_generator_script().main(_cli_args(report, output))

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source_commit_sha"] == "a" * 40
    assert payload["artifact_sha256"] == f"sha256:{'d' * 64}"


def test_receipt_cli_rejects_naive_completion_time(tmp_path: Path) -> None:
    args = _cli_args(_write_report(tmp_path), tmp_path / "receipt.json")
    args[args.index("--completed-at-utc") + 1] = "2026-06-21T10:00:00"

    assert _load_generator_script().main(args) == 2


def _build(report: Path, artifact_sha256: str | None = None) -> CIExecutionReceipt:
    return build_durable_repository_ci_execution_receipt(
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
        completed_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        artifact_sha256=artifact_sha256,
    )


def _write_report(
    tmp_path: Path,
    *,
    outcome: str | None = None,
    failures: str = "0",
    omitted_test: tuple[str, str] | None = None,
) -> Path:
    cases = []
    for index, (class_name, test_name) in enumerate(TEST_CASES):
        if (class_name, test_name) == omitted_test:
            continue
        outcome_element = f"<{outcome} />" if outcome and index == 0 else ""
        cases.append(
            f'<testcase classname="{class_name}" name="{test_name}">{outcome_element}</testcase>'
        )
    report = tmp_path / f"report-{outcome or failures}.xml"
    report.write_text(
        '<testsuites failures="{failures}" errors="0"><testsuite failures="{failures}" '
        'errors="0">{cases}</testsuite></testsuites>'.format(
            failures=failures,
            cases="".join(cases),
        ),
        encoding="utf-8",
    )
    return report


def _cli_args(report: Path, output: Path) -> list[str]:
    return [
        "--test-report",
        str(report),
        "--repository",
        "sgajbi/lotus-idea",
        "--workflow-path",
        ".github/workflows/main-releasability.yml",
        "--workflow-name",
        "Main Releasability Gate",
        "--job-name",
        "Main Releasability / PostgreSQL Runtime Proof",
        "--run-id",
        "123",
        "--run-attempt",
        "1",
        "--source-commit-sha",
        "a" * 40,
        "--source-ref",
        "refs/heads/main",
        "--conclusion",
        "success",
        "--completed-at-utc",
        "2026-06-21T10:00:00Z",
        "--artifact-sha256",
        "d" * 64,
        "--output",
        str(output),
    ]


def _load_generator_script() -> ModuleType:
    path = ROOT / "scripts" / "persistence" / "generate_ci_execution_receipt.py"
    spec = importlib.util.spec_from_file_location("generate_persistence_ci_receipt", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
