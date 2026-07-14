from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from app.application.durable_repository_proof.contract import (
    REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
)
from app.domain.proof_evidence import CIExecutionReceipt


_GOVERNED_POSTGRES_TESTS = (
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
_BARE_SHA256 = re.compile(r"[0-9a-f]{64}")
_CANONICAL_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def build_durable_repository_ci_execution_receipt(
    *,
    test_report_path: Path,
    repository: str,
    workflow_path: str,
    workflow_name: str,
    job_name: str,
    run_id: int,
    run_attempt: int,
    source_commit_sha: str,
    source_ref: str,
    conclusion: str,
    completed_at_utc: datetime,
    artifact_sha256: str | None = None,
) -> CIExecutionReceipt:
    _require_successful_durable_repository_tests(test_report_path)
    return CIExecutionReceipt(
        repository=repository,
        workflow_path=workflow_path,
        workflow_name=workflow_name,
        job_name=job_name,
        run_id=run_id,
        run_attempt=run_attempt,
        source_commit_sha=source_commit_sha,
        source_ref=source_ref,
        conclusion=conclusion,
        completed_at_utc=completed_at_utc.isoformat(),
        artifact_name=TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
        artifact_sha256=_canonical_artifact_sha256(
            artifact_sha256,
            fallback_path=test_report_path,
        ),
        assertions=REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    )


def _require_successful_durable_repository_tests(test_report_path: Path) -> None:
    try:
        root = ET.parse(test_report_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("PostgreSQL test report is unavailable or malformed") from exc
    cases = tuple(root.iter("testcase"))
    for class_name, test_name in _GOVERNED_POSTGRES_TESTS:
        matching = [
            case
            for case in cases
            if case.get("classname") == class_name and case.get("name") == test_name
        ]
        if len(matching) != 1:
            raise ValueError(
                "PostgreSQL test report must contain each governed durable repository test once"
            )
        if any(matching[0].find(outcome) is not None for outcome in ("failure", "error", "skipped")):
            raise ValueError(f"Governed durable repository PostgreSQL test did not pass: {test_name}")
    if any(_count(root, field) for field in ("failures", "errors")):
        raise ValueError("PostgreSQL runtime proof report contains failed tests")


def _canonical_artifact_sha256(value: str | None, *, fallback_path: Path) -> str:
    if value is None:
        return f"sha256:{hashlib.sha256(fallback_path.read_bytes()).hexdigest()}"
    if _BARE_SHA256.fullmatch(value) is not None:
        return f"sha256:{value}"
    if _CANONICAL_SHA256.fullmatch(value) is not None:
        return value
    raise ValueError("artifact SHA-256 must be 64 lowercase hex characters")


def _count(root: ET.Element, field: str) -> int:
    values = [
        element.get(field, "0")
        for element in root.iter()
        if element.tag in {"testsuite", "testsuites"}
    ]
    try:
        return max((int(value) for value in values), default=0)
    except ValueError as exc:
        raise ValueError(f"PostgreSQL test report has invalid {field} count") from exc
