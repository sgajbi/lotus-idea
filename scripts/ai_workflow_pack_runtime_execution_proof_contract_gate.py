from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
    REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
    REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS,
    ai_workflow_pack_runtime_execution_proof_is_valid,
    build_ai_workflow_pack_runtime_execution_proof_payload,
)

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
    "portfolioId",
    "prompt",
    "providerResponse",
    "rawPayload",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "traceId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "correlation_id",
    "holding_id",
    "portfolio_id",
    "raw prompt",
    "raw provider",
    "request-body",
    "response-body",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_ai_workflow_pack_runtime_execution_proof_contract(
    *,
    lotus_ai_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=lotus_ai_root,
    )
    if proof.get("schemaVersion") != AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION:
        errors.append(
            "AI workflow-pack runtime execution proof schema must be "
            f"{AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS
    ):
        errors.append(
            "AI workflow-pack runtime execution proof evidence refs must match the contract"
        )
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED
    ):
        errors.append(
            "AI workflow-pack runtime execution proof must clear only runtime execution blockers"
        )
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS
    ):
        errors.append("AI workflow-pack runtime execution proof must retain non-runtime blockers")
    proof_checks = proof.get("proofChecks")
    file_evidence_present = (
        isinstance(proof_checks, Mapping) and proof_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not ai_workflow_pack_runtime_execution_proof_is_valid(proof):
        errors.append(
            "AI workflow-pack runtime execution proof must validate against sibling "
            "lotus-ai truth when sibling evidence is present"
        )
    if (
        not file_evidence_present
        and proof.get("aiWorkflowPackRuntimeExecutionProofValid") is not False
    ):
        errors.append("missing sibling lotus-ai evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_ai_workflow_pack_runtime_execution_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("AI workflow-pack runtime execution proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
