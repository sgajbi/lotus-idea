from __future__ import annotations

from app.application.durable_repository_proof import REQUIRED_DURABLE_REPOSITORY_ASSERTIONS
from app.application.durable_repository_proof.contract import (
    TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY,
    TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH,
)
from app.domain.proof_evidence import CIExecutionReceipt


SOURCE_COMMIT_SHA = "a" * 40


def valid_durable_repository_ci_execution_receipt() -> CIExecutionReceipt:
    return CIExecutionReceipt(
        repository=TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY,
        workflow_path=TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH,
        workflow_name=TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME,
        job_name=TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME,
        run_id=29308821849,
        run_attempt=1,
        source_commit_sha=SOURCE_COMMIT_SHA,
        source_ref=TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF,
        conclusion="success",
        completed_at_utc="2026-06-21T10:00:00+00:00",
        artifact_name=TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
        artifact_sha256=f"sha256:{'b' * 64}",
        assertions=REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    )
