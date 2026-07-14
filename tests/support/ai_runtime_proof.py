from __future__ import annotations

from app.application.ai_runtime_proof import AIRuntimeExecutionReceipt


def ai_runtime_execution_receipt() -> AIRuntimeExecutionReceipt:
    return AIRuntimeExecutionReceipt(
        service="lotus-ai",
        service_version="0.1.0",
        endpoint_path="/platform/workflow-packs/execute",
        workflow_pack_id="idea_explanation.pack",
        workflow_pack_version="v1",
        registration_ref="idea_explanation.pack@v1",
        run_id="wpr_runtime_proof_001",
        request_id="req_runtime_proof_001",
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
        completed_at_utc="2026-07-14T00:00:00Z",
    )


def lotus_ai_runtime_execution_response() -> dict[str, object]:
    return {
        "service": "lotus-ai",
        "version": "0.1.0",
        "eligibility": {
            "pack_id": "idea_explanation.pack",
            "requested_version": "v1",
            "allowed": True,
            "caller_app": "lotus-idea",
            "environment": "DEVELOPMENT",
            "caller_identity_class": "INTERNAL_SERVICE",
        },
        "execution": {
            "status": "COMPLETED",
            "task_id": "explain.v1",
            "output_label": "EXPLANATION_ONLY",
            "result": {
                "structured_output": {
                    "evidence_content_hash": (
                        "sha256:5f0d86edd763490148f0feb3009586582250775692d892238f1a28107ad2ff7d"
                    ),
                    "human_review_required": True,
                    "client_ready_publication": "BLOCKED",
                    "downstream_authority": "BLOCKED",
                }
            },
            "audit": {
                "workflow_pack_run_id": "wpr_runtime_proof_001",
                "provider_mode": "stub",
                "provider_id": "stub-text-provider",
                "model_id": None,
                "model_version": None,
                "stubbed": True,
            },
        },
        "workflow_pack_run": {
            "run_id": "wpr_runtime_proof_001",
            "pack_id": "idea_explanation.pack",
            "pack_version": "v1",
            "registration_ref": "idea_explanation.pack@v1",
            "task_id": "explain.v1",
            "request_id": "req_runtime_proof_001",
            "caller_app": "lotus-idea",
            "workflow_surface": "idea-explanation-evidence",
            "runtime_state": "COMPLETED",
            "review_state": "AWAITING_REVIEW",
            "supportability_status": "ACTION_REQUIRED",
            "review_required": True,
            "completed_at": "2026-07-14T00:00:00Z",
        },
    }


__all__ = ["ai_runtime_execution_receipt", "lotus_ai_runtime_execution_response"]
