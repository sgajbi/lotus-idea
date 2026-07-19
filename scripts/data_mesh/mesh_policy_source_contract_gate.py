# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.data_mesh.mesh_policy_source_contract import (  # noqa: E402
    MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
    MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION,
    REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS,
    REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS,
    build_mesh_policy_source_contract_payload,
    mesh_policy_source_contract_is_valid,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content  # noqa: E402
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]  # noqa: E402

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "contentHash",
    "correlationId",
    "holdingId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "content_hash",
    "correlation_id",
    "holding_id",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}


def validate_mesh_policy_source_contract() -> list[str]:
    errors: list[str] = []
    proof = build_mesh_policy_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION:
        errors.append(
            f"mesh policy source-contract schema must be {MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        errors.append("mesh policy source-contract evidence refs must match the contract")
    if tuple(proof.get("sourceContractBlockersSatisfied") or ()) != (
        MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    ):
        errors.append("mesh policy source contract must not satisfy certification blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS
    ):
        errors.append("mesh policy source contract must retain every certification blocker")
    if not mesh_policy_source_contract_is_valid(proof):
        errors.append("mesh policy source contract must validate against current policy sources")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_mesh_policy_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Mesh policy source-contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
