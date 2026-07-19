# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.workbench.read_path_source_contract import (  # noqa: E402
    REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
    REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS,
    REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS,
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    build_workbench_read_path_source_contract_proof_payload,
    workbench_read_path_source_contract_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

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
    "candidateId",
    "clientId",
    "portfolioId",
    "request-body",
    "response-body",
    "/source/",
}

_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_workbench_read_path_source_contract() -> list[str]:
    errors: list[str] = []
    proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append("Workbench read-path source-contract schema must be v2")
    if proof.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("Workbench read-path proof must be source_contract evidence")
    if tuple(proof.get("localEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS
    ):
        errors.append("Workbench read-path local evidence refs must match the contract")
    if tuple(proof.get("declaredRouteRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS
    ):
        errors.append("Workbench read-path route declarations must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("Workbench read-path source-contract proof must clear no blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    ):
        errors.append("Workbench read-path proof must retain runtime/product blockers")
    if not workbench_read_path_source_contract_proof_is_valid(proof):
        errors.append("Workbench read-path source-contract proof must validate")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_workbench_read_path_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Workbench read-path source-contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
