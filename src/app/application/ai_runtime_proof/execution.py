from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Any

from app.ports.lotus_ai_runtime import LotusAIWorkflowRuntime


AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV = "LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF"
AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION = (
    "lotus-idea.ai-workflow-pack-runtime-execution-proof.v2"
)

AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED = ("lotus_ai_runtime_execution_missing",)

REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS = (
    "lotus_ai_live_provider_execution_missing",
    "certified_ai_lineage_store_missing",
    "workflow_pack_runtime_contract_not_certified",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

_CALLER_APP = "lotus-idea"
_WORKFLOW_PACK_ID = "idea_explanation.pack"
_WORKFLOW_PACK_VERSION = "v1"
_WORKFLOW_SURFACE = "idea-explanation-evidence"
_TASK_ID = "explain.v1"
_ENVIRONMENT = "DEVELOPMENT"
_CALLER_IDENTITY_CLASS = "INTERNAL_SERVICE"
_EVIDENCE_CONTENT_HASH = "sha256:" + hashlib.sha256(
    b"lotus-idea-ai-runtime-proof-redacted-evidence-v1"
).hexdigest()


class InvalidAIRuntimeExecutionReceipt(ValueError):
    """Raised when an execution response cannot substantiate bounded runtime proof."""


@dataclass(frozen=True)
class AIRuntimeExecutionReceipt:
    service: str
    service_version: str
    endpoint_path: str
    workflow_pack_id: str
    workflow_pack_version: str
    registration_ref: str
    run_id: str
    request_id: str
    caller_app: str
    workflow_surface: str
    environment: str
    caller_identity_class: str
    task_id: str
    runtime_state: str
    review_state: str
    supportability_status: str
    review_required: bool
    execution_status: str
    output_label: str
    provider_mode: str
    provider_id: str
    model_id: str | None
    model_version: str | None
    stubbed: bool
    human_review_required: bool
    client_ready_publication: str
    downstream_authority: str
    completed_at_utc: str


def execute_ai_workflow_pack_runtime_proof(
    *,
    runtime: LotusAIWorkflowRuntime,
    generated_at_utc: datetime,
) -> dict[str, Any]:
    request = _runtime_proof_request(generated_at_utc)
    response = runtime.execute_workflow_pack(request, caller_app=_CALLER_APP)
    receipt = _map_runtime_execution_receipt(response)
    return build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=generated_at_utc,
        receipt=receipt,
    )


def build_ai_workflow_pack_runtime_execution_proof_payload(
    *,
    generated_at_utc: datetime,
    receipt: AIRuntimeExecutionReceipt,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    receipt_payload = asdict(receipt)
    receipt_valid = _receipt_is_valid(receipt)
    receipt_digest = _sha256(receipt_payload)
    proof_valid = timezone_aware_generated_at_utc and receipt_valid
    return {
        "schemaVersion": AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_ai_idea_workflow_pack_runtime_execution",
        "proofScope": "actual_deterministic_stub_runtime_execution",
        "aiWorkflowPackRuntimeExecutionProofValid": proof_valid,
        "aggregateBlockersCleared": AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
        "evidenceRefs": (
            f"lotus-ai:workflow-pack-run:{receipt.run_id}",
            f"lotus-ai:task-request:{receipt.request_id}",
        ),
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "actualRuntimeReceiptValid": receipt_valid,
            "workflowPackIdentityBound": (
                receipt.workflow_pack_id == _WORKFLOW_PACK_ID
                and receipt.workflow_pack_version == _WORKFLOW_PACK_VERSION
            ),
            "callerIdentityBound": receipt.caller_app == _CALLER_APP,
            "executionCompleted": (
                receipt.runtime_state == "COMPLETED"
                and receipt.execution_status == "COMPLETED"
            ),
            "humanReviewEnforced": (
                receipt.review_required
                and receipt.human_review_required
                and receipt.review_state == "AWAITING_REVIEW"
            ),
            "consequenceBearingActionsBlocked": (
                receipt.client_ready_publication == "BLOCKED"
                and receipt.downstream_authority == "BLOCKED"
            ),
            "deterministicStubObserved": receipt.stubbed,
        },
        "runtimeReceipt": receipt_payload,
        "runtimeReceiptSha256": receipt_digest,
        "remainingCertificationBlockers": REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
        "workflowPackId": f"{_WORKFLOW_PACK_ID}@{_WORKFLOW_PACK_VERSION}",
        "workflowAuthorityOwner": "lotus-idea",
        "aiCapabilityOwner": "lotus-ai",
        "workflowPackRuntimeExecutionCertified": proof_valid,
        "lotusAiRuntimeExecuted": proof_valid,
        "deterministicStubExecution": proof_valid and receipt.stubbed,
        "liveProviderExecuted": proof_valid and not receipt.stubbed,
        "providerRolloutCertified": False,
        "modelRiskDashboardCertified": False,
        "modelRiskAlertsCertified": False,
        "workbenchProductProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def build_unavailable_ai_workflow_pack_runtime_execution_proof_payload(
    *,
    generated_at_utc: datetime,
) -> dict[str, Any]:
    return {
        "schemaVersion": AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_ai_idea_workflow_pack_runtime_execution",
        "proofScope": "runtime_unavailable_non_proof",
        "aiWorkflowPackRuntimeExecutionProofValid": False,
        "aggregateBlockersCleared": (),
        "evidenceRefs": (),
        "proofChecks": {"actualRuntimeReceiptValid": False},
        "runtimeReceipt": None,
        "runtimeReceiptSha256": None,
        "remainingCertificationBlockers": (
            "lotus_ai_runtime_execution_missing",
            *REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
        ),
        "workflowPackId": f"{_WORKFLOW_PACK_ID}@{_WORKFLOW_PACK_VERSION}",
        "workflowAuthorityOwner": "lotus-idea",
        "aiCapabilityOwner": "lotus-ai",
        "workflowPackRuntimeExecutionCertified": False,
        "lotusAiRuntimeExecuted": False,
        "deterministicStubExecution": False,
        "liveProviderExecuted": False,
        "providerRolloutCertified": False,
        "modelRiskDashboardCertified": False,
        "modelRiskAlertsCertified": False,
        "workbenchProductProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def ai_workflow_pack_runtime_execution_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "lotus_ai_idea_workflow_pack_runtime_execution":
        return False
    if payload.get("proofScope") != "actual_deterministic_stub_runtime_execution":
        return False
    if payload.get("aiWorkflowPackRuntimeExecutionProofValid") is not True:
        return False
    if payload.get("workflowPackId") != f"{_WORKFLOW_PACK_ID}@{_WORKFLOW_PACK_VERSION}":
        return False
    if payload.get("workflowAuthorityOwner") != "lotus-idea":
        return False
    if payload.get("aiCapabilityOwner") != "lotus-ai":
        return False
    if payload.get("workflowPackRuntimeExecutionCertified") is not True:
        return False
    if payload.get("lotusAiRuntimeExecuted") is not True:
        return False
    if payload.get("deterministicStubExecution") is not True:
        return False
    if payload.get("liveProviderExecuted") is not False:
        return False
    if any(
        payload.get(field_name) is not False
        for field_name in (
            "providerRolloutCertified",
            "modelRiskDashboardCertified",
            "modelRiskAlertsCertified",
            "workbenchProductProofCertified",
            "clientReadyPublicationAuthorized",
            "supportedFeaturePromoted",
            "proofClosed",
        )
    ):
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS
    ):
        return False
    receipt_payload = payload.get("runtimeReceipt")
    if not isinstance(receipt_payload, Mapping):
        return False
    try:
        receipt = AIRuntimeExecutionReceipt(**dict(receipt_payload))
    except TypeError:
        return False
    if not _receipt_is_valid(receipt):
        return False
    if payload.get("runtimeReceiptSha256") != _sha256(asdict(receipt)):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        f"lotus-ai:workflow-pack-run:{receipt.run_id}",
        f"lotus-ai:task-request:{receipt.request_id}",
    ):
        return False
    proof_checks = payload.get("proofChecks")
    return isinstance(proof_checks, Mapping) and all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "actualRuntimeReceiptValid",
            "workflowPackIdentityBound",
            "callerIdentityBound",
            "executionCompleted",
            "humanReviewEnforced",
            "consequenceBearingActionsBlocked",
            "deterministicStubObserved",
        )
    )


def _runtime_proof_request(generated_at_utc: datetime) -> dict[str, object]:
    correlation_suffix = generated_at_utc.strftime("%Y%m%dT%H%M%S%fZ")
    return {
        "pack_id": _WORKFLOW_PACK_ID,
        "version": _WORKFLOW_PACK_VERSION,
        "environment": _ENVIRONMENT,
        "caller_identity_class": _CALLER_IDENTITY_CLASS,
        "workflow_surface": _WORKFLOW_SURFACE,
        "task_request": {
            "task_id": _TASK_ID,
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": {
                "caller_app": _CALLER_APP,
                "correlation_id": f"lotus-idea-runtime-proof-{correlation_suffix}",
                "tenant_id": "tenant-sg-001",
            },
            "context": {
                "summary": "Execute a review-gated runtime proof from synthetic redacted evidence.",
                "payload": _runtime_proof_payload(),
                "source_refs": ["lotus-idea:runtime-proof:redacted-evidence:v1"],
            },
            "expected_output_label": "EXPLANATION_ONLY",
        },
    }


def _runtime_proof_payload() -> dict[str, object]:
    return {
        "redacted_evidence_packet": {
            "candidate_id": "runtime-proof-candidate",
            "family": "RUNTIME_PROOF",
            "lifecycle_status": "READY_FOR_REVIEW",
            "review_posture": "ADVISOR_REVIEW_REQUIRED",
            "evidence_packet_id": "runtime-proof-evidence",
            "evidence_content_hash": _EVIDENCE_CONTENT_HASH,
            "supportability": "READY",
            "score_policy_version": "runtime-proof-score-policy.v1",
            "score": "0.50",
            "source_signal_count": 1,
            "reason_codes": ["RUNTIME_PROOF_ONLY"],
            "source_refs": [
                {
                    "source_system": "lotus-idea",
                    "product_id": "runtime-proof-evidence",
                    "product_version": "v1",
                    "source_id": "synthetic-runtime-proof",
                    "content_hash": _EVIDENCE_CONTENT_HASH,
                }
            ],
        },
        "explanation_request": {
            "request_id": "runtime-proof-request",
            "workflow_pack_id": "lotus-ai:idea-explanation:v1",
            "workflow_pack_version": "v1",
            "purpose": "unsupported_claim_verification",
            "evaluation_ref": "idea-explanation-eval-pack.v1",
            "audience": "advisor",
            "requested_outputs": ["unsupported_claim_check"],
        },
        "supportability": {
            "human_review_required": True,
            "client_ready_publication": "BLOCKED",
            "forbidden_actions": [
                "approve_suitability",
                "contact_client",
                "invent_missing_evidence",
                "make_final_recommendation",
                "place_orders",
            ],
            "unsupported_claims": [
                "client_ready_publication",
                "final_investment_recommendation",
                "suitability_approval",
                "trade_or_order_action",
            ],
        },
    }


def _map_runtime_execution_receipt(response: Mapping[str, object]) -> AIRuntimeExecutionReceipt:
    eligibility = _object(response, "eligibility")
    execution = _object(response, "execution")
    audit = _object(execution, "audit")
    result = _object(execution, "result")
    structured_output = _object(result, "structured_output")
    workflow_run = _object(response, "workflow_pack_run")
    receipt = AIRuntimeExecutionReceipt(
        service=_text(response, "service"),
        service_version=_text(response, "version"),
        endpoint_path="/platform/workflow-packs/execute",
        workflow_pack_id=_text(workflow_run, "pack_id"),
        workflow_pack_version=_text(workflow_run, "pack_version"),
        registration_ref=_text(workflow_run, "registration_ref"),
        run_id=_text(workflow_run, "run_id"),
        request_id=_text(workflow_run, "request_id"),
        caller_app=_text(workflow_run, "caller_app"),
        workflow_surface=_text(workflow_run, "workflow_surface"),
        environment=_text(eligibility, "environment"),
        caller_identity_class=_text(eligibility, "caller_identity_class"),
        task_id=_text(workflow_run, "task_id"),
        runtime_state=_text(workflow_run, "runtime_state"),
        review_state=_text(workflow_run, "review_state"),
        supportability_status=_text(workflow_run, "supportability_status"),
        review_required=_boolean(workflow_run, "review_required"),
        execution_status=_text(execution, "status"),
        output_label=_text(execution, "output_label"),
        provider_mode=_text(audit, "provider_mode"),
        provider_id=_text(audit, "provider_id"),
        model_id=_optional_text(audit, "model_id"),
        model_version=_optional_text(audit, "model_version"),
        stubbed=_boolean(audit, "stubbed"),
        human_review_required=_boolean(structured_output, "human_review_required"),
        client_ready_publication=_text(structured_output, "client_ready_publication"),
        downstream_authority=_text(structured_output, "downstream_authority"),
        completed_at_utc=_text(workflow_run, "completed_at"),
    )
    if _text(eligibility, "pack_id") != receipt.workflow_pack_id:
        raise InvalidAIRuntimeExecutionReceipt("eligibility pack identity does not match run")
    if _text(eligibility, "requested_version") != receipt.workflow_pack_version:
        raise InvalidAIRuntimeExecutionReceipt("eligibility version does not match run")
    if _text(eligibility, "caller_app") != receipt.caller_app:
        raise InvalidAIRuntimeExecutionReceipt("eligibility caller does not match run")
    if _boolean(eligibility, "allowed") is not True:
        raise InvalidAIRuntimeExecutionReceipt("workflow-pack execution was not eligible")
    if _text(audit, "workflow_pack_run_id") != receipt.run_id:
        raise InvalidAIRuntimeExecutionReceipt("task audit run identity does not match run")
    if _text(structured_output, "evidence_content_hash") != _EVIDENCE_CONTENT_HASH:
        raise InvalidAIRuntimeExecutionReceipt("runtime output is not bound to proof evidence")
    if not _receipt_is_valid(receipt):
        raise InvalidAIRuntimeExecutionReceipt("runtime execution receipt failed policy validation")
    return receipt


def _receipt_is_valid(receipt: AIRuntimeExecutionReceipt) -> bool:
    return (
        receipt.service == "lotus-ai"
        and bool(receipt.service_version)
        and receipt.endpoint_path == "/platform/workflow-packs/execute"
        and receipt.workflow_pack_id == _WORKFLOW_PACK_ID
        and receipt.workflow_pack_version == _WORKFLOW_PACK_VERSION
        and bool(receipt.registration_ref)
        and bool(receipt.run_id)
        and bool(receipt.request_id)
        and receipt.caller_app == _CALLER_APP
        and receipt.workflow_surface == _WORKFLOW_SURFACE
        and receipt.environment == _ENVIRONMENT
        and receipt.caller_identity_class == _CALLER_IDENTITY_CLASS
        and receipt.task_id == _TASK_ID
        and receipt.runtime_state == "COMPLETED"
        and receipt.review_state == "AWAITING_REVIEW"
        and receipt.supportability_status == "ACTION_REQUIRED"
        and receipt.review_required
        and receipt.execution_status == "COMPLETED"
        and receipt.output_label == "EXPLANATION_ONLY"
        and bool(receipt.provider_mode)
        and bool(receipt.provider_id)
        and receipt.stubbed
        and receipt.human_review_required
        and receipt.client_ready_publication == "BLOCKED"
        and receipt.downstream_authority == "BLOCKED"
        and _is_timezone_aware_datetime_text(receipt.completed_at_utc)
    )


def _object(mapping: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = mapping.get(field_name)
    if not isinstance(value, Mapping):
        raise InvalidAIRuntimeExecutionReceipt(f"{field_name} must be an object")
    return value


def _text(mapping: Mapping[str, object], field_name: str) -> str:
    value = mapping.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidAIRuntimeExecutionReceipt(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(mapping: Mapping[str, object], field_name: str) -> str | None:
    value = mapping.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InvalidAIRuntimeExecutionReceipt(f"{field_name} must be non-empty text or null")
    return value.strip()


def _boolean(mapping: Mapping[str, object], field_name: str) -> bool:
    value = mapping.get(field_name)
    if not isinstance(value, bool):
        raise InvalidAIRuntimeExecutionReceipt(f"{field_name} must be boolean")
    return value


def _is_timezone_aware_datetime_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _sha256(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
