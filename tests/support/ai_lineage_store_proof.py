from __future__ import annotations

from app.application.ai_lineage_store_proof import REQUIRED_AI_LINEAGE_STORE_ASSERTIONS
from app.application.ai_lineage_store_proof.contract import (
    TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY,
    TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH,
)
from app.domain.proof_evidence import CIExecutionReceipt


def valid_ai_lineage_ci_execution_receipt() -> CIExecutionReceipt:
    return CIExecutionReceipt(
        repository=TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY,
        workflow_path=TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH,
        workflow_name=TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME,
        job_name=TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME,
        run_id=29304186222,
        run_attempt=1,
        source_commit_sha="9d40aae14a50abb20d359c4a9f3e57558f29f22c",
        source_ref=TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF,
        conclusion="success",
        completed_at_utc="2026-06-21T10:00:00+00:00",
        artifact_name=TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
        artifact_sha256=f"sha256:{'a' * 64}",
        assertions=REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    )
