# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
import sys


from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
    REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
    AIRuntimeExecutionReceipt,
    ai_workflow_pack_runtime_execution_proof_is_valid,
    build_ai_workflow_pack_runtime_execution_proof_payload,
)

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

FORBIDDEN_KEYS = {
    "accountId",
    "account_id",
    "candidateId",
    "candidate_id",
    "clientId",
    "client_id",
    "correlationId",
    "correlation_id",
    "holdingId",
    "holding_id",
    "portfolioId",
    "portfolio_id",
    "prompt",
    "providerResponse",
    "provider_response",
    "rawPayload",
    "raw_payload",
    "requestBody",
    "request_body",
    "responseBody",
    "response_body",
    "sourcePayload",
    "source_payload",
    "traceId",
    "trace_id",
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


def validate_ai_workflow_pack_runtime_execution_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        receipt=_contract_receipt(),
    )
    if proof.get("schemaVersion") != AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION:
        errors.append(
            "AI workflow-pack runtime execution proof schema must be "
            f"{AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION}"
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
    if not ai_workflow_pack_runtime_execution_proof_is_valid(proof):
        errors.append("AI workflow-pack runtime execution proof contract must validate")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _contract_receipt() -> AIRuntimeExecutionReceipt:
    return AIRuntimeExecutionReceipt(
        service="lotus-ai",
        service_version="contract-test",
        endpoint_path="/platform/workflow-packs/execute",
        workflow_pack_id="idea_explanation.pack",
        workflow_pack_version="v1",
        registration_ref="idea_explanation.pack@v1",
        run_id="wpr_contract_test",
        request_id="req_contract_test",
        caller_app="lotus-idea",
        workflow_surface="idea-explanation-evidence",
        environment="DEVELOPMENT",
        caller_identity_class="INTERNAL_SERVICE",
        task_id="explain.v1",
        runtime_state="COMPLETED",
        review_state="AWAITING_REVIEW",
        supportability_status="ACTION_REQUIRED",
        review_required=True,
        execution_status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        provider_mode="stub",
        provider_id="stub-text-provider",
        model_id=None,
        model_version=None,
        stubbed=True,
        human_review_required=True,
        client_ready_publication="BLOCKED",
        downstream_authority="BLOCKED",
        completed_at_utc="2026-06-26T00:00:00Z",
    )


def main() -> int:
    errors = validate_ai_workflow_pack_runtime_execution_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("AI workflow-pack runtime execution proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
