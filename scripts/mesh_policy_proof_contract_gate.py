from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.mesh_policy_proof import (
    MESH_POLICY_BLOCKERS_CLEARED,
    MESH_POLICY_PROOF_SCHEMA_VERSION,
    REMAINING_MESH_POLICY_BLOCKERS,
    REQUIRED_MESH_POLICY_EVIDENCE_REFS,
    build_mesh_policy_proof_payload,
    mesh_policy_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]

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


def validate_mesh_policy_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_mesh_policy_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != MESH_POLICY_PROOF_SCHEMA_VERSION:
        errors.append(f"mesh policy proof schema must be {MESH_POLICY_PROOF_SCHEMA_VERSION}")
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_MESH_POLICY_EVIDENCE_REFS:
        errors.append("mesh policy proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != MESH_POLICY_BLOCKERS_CLEARED:
        errors.append("mesh policy proof must clear only SLO, access, and evidence blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (REMAINING_MESH_POLICY_BLOCKERS):
        errors.append(
            "mesh policy proof must retain platform, product, discovery, and support blockers"
        )
    if not mesh_policy_proof_is_valid(proof):
        errors.append("mesh policy proof must validate against current repo policy contracts")
    _validate_forbidden_content(proof, errors)
    return errors


def _validate_forbidden_content(value: object, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text in FORBIDDEN_KEYS:
                errors.append(f"{next_path}: forbidden source-sensitive key is present")
            _validate_forbidden_content(nested, errors, next_path)
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def main() -> int:
    errors = validate_mesh_policy_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Mesh policy proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
