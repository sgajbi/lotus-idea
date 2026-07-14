from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from app.application.ai_lineage_store_proof.contract import (
    REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
)
from app.domain.proof_evidence import CIExecutionReceipt


_AI_LINEAGE_TEST_CLASS = "tests.integration.test_postgres_runtime_integration"
_AI_LINEAGE_TEST_NAME = "test_postgres_runtime_provider_persists_ai_explanation_lineage"
_BARE_SHA256 = re.compile(r"[0-9a-f]{64}")
_CANONICAL_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def build_postgres_ci_execution_receipt(
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
    _require_successful_ai_lineage_test(test_report_path)
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
        artifact_name=TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
        artifact_sha256=_canonical_artifact_sha256(
            artifact_sha256,
            fallback_path=test_report_path,
        ),
        assertions=REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    )


def _canonical_artifact_sha256(value: str | None, *, fallback_path: Path) -> str:
    if value is None:
        return f"sha256:{hashlib.sha256(fallback_path.read_bytes()).hexdigest()}"
    if _BARE_SHA256.fullmatch(value) is not None:
        return f"sha256:{value}"
    if _CANONICAL_SHA256.fullmatch(value) is not None:
        return value
    raise ValueError("artifact SHA-256 must be 64 lowercase hex characters")


def _require_successful_ai_lineage_test(test_report_path: Path) -> None:
    try:
        root = ET.parse(test_report_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("PostgreSQL test report is unavailable or malformed") from exc
    matching = [
        case
        for case in root.iter("testcase")
        if case.get("classname") == _AI_LINEAGE_TEST_CLASS
        and case.get("name") == _AI_LINEAGE_TEST_NAME
    ]
    if len(matching) != 1:
        raise ValueError("PostgreSQL test report must contain the governed AI lineage test once")
    if any(matching[0].find(outcome) is not None for outcome in ("failure", "error", "skipped")):
        raise ValueError("Governed AI lineage PostgreSQL test did not pass")
    if any(_count(root, field) for field in ("failures", "errors")):
        raise ValueError("PostgreSQL runtime proof report contains failed tests")


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
