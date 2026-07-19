# ruff: noqa: E402
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.persistence import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # type: ignore[import-not-found,no-redef]  # noqa: F401


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
    REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS,
    build_durable_repository_proof_payload,
    durable_repository_proof_is_valid,
)
from app.application.durable_repository_proof.contract import (
    TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY,
    TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH,
)
from app.domain.proof_evidence import CIExecutionReceipt
from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT_SHA = "a" * 40

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
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


def validate_durable_repository_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        source_commit_sha=SOURCE_COMMIT_SHA,
        ci_execution_receipt=_contract_receipt(),
    )
    if proof.get("schemaVersion") != DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION:
        errors.append(
            f"durable repository proof schema must be {DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS:
        errors.append("durable repository proof evidence refs must match the governed contract")
    if not durable_repository_proof_is_valid(proof):
        errors.append("durable repository proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _contract_receipt() -> CIExecutionReceipt:
    return CIExecutionReceipt(
        repository=TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY,
        workflow_path=TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH,
        workflow_name=TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME,
        job_name=TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME,
        run_id=1,
        run_attempt=1,
        source_commit_sha=SOURCE_COMMIT_SHA,
        source_ref=TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF,
        conclusion="success",
        completed_at_utc="2026-06-21T10:00:00+00:00",
        artifact_name=TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
        artifact_sha256=f"sha256:{'b' * 64}",
        assertions=REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    )


def main() -> int:
    errors = validate_durable_repository_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Durable repository proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
