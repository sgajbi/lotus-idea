from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.application.ai_lineage_store_proof.contract import (
    REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
)
from app.application.ci_execution_evidence import (
    canonical_artifact_sha256,
    require_successful_junit_tests,
)
from app.domain.proof_evidence import CIExecutionReceipt


_AI_LINEAGE_TEST_CLASS = "tests.integration.test_postgres_runtime_integration"
_AI_LINEAGE_TEST_NAME = "test_postgres_runtime_provider_persists_ai_explanation_lineage"


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
    require_successful_junit_tests(
        test_report_path=test_report_path,
        governed_tests=((_AI_LINEAGE_TEST_CLASS, _AI_LINEAGE_TEST_NAME),),
        missing_test_message=(
            "PostgreSQL test report must contain the governed AI lineage test once"
        ),
        failed_test_message="Governed AI lineage PostgreSQL test did not pass",
    )
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
        artifact_sha256=canonical_artifact_sha256(
            artifact_sha256,
            fallback_path=test_report_path,
        ),
        assertions=REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    )
