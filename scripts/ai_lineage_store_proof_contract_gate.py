# ruff: noqa: E402
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.ai_lineage_store_proof import (
    AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
    REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS,
    ai_lineage_store_proof_is_valid,
    build_ai_lineage_store_proof_payload,
)
from app.application.ai_lineage_store_proof.contract import (
    REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY,
    TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH,
)
from app.domain.proof_evidence import CIExecutionReceipt


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "prompt",
    "providerResponse",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "postgresql://",
    "request-body",
    "response-body",
    "/source/",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_ai_lineage_store_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        ci_execution_receipt=_contract_receipt(),
    )
    if proof.get("schemaVersion") != AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION:
        errors.append(
            f"AI lineage store proof schema must be {AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS:
        errors.append("AI lineage store proof evidence refs must match the governed contract")
    if not ai_lineage_store_proof_is_valid(proof):
        errors.append("AI lineage store proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _contract_receipt() -> CIExecutionReceipt:
    return CIExecutionReceipt(
        repository=TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY,
        workflow_path=TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH,
        workflow_name=TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME,
        job_name=TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME,
        run_id=1,
        run_attempt=1,
        source_commit_sha="a" * 40,
        source_ref=TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF,
        conclusion="success",
        completed_at_utc="2026-06-21T10:00:00+00:00",
        artifact_name=TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
        artifact_sha256=f"sha256:{'b' * 64}",
        assertions=REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    )


def main() -> int:
    errors = validate_ai_lineage_store_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("AI lineage store proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
