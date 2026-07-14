from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.application.ci_execution_evidence import (
    canonical_artifact_sha256,
    require_successful_junit_tests,
)
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
    require_successful_junit_tests(
        test_report_path=test_report_path,
        governed_tests=_GOVERNED_POSTGRES_TESTS,
        missing_test_message=(
            "PostgreSQL test report must contain each governed durable repository test once"
        ),
        failed_test_message="Governed durable repository PostgreSQL test did not pass",
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
        artifact_name=TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
        artifact_sha256=canonical_artifact_sha256(
            artifact_sha256,
            fallback_path=test_report_path,
        ),
        assertions=REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    )
