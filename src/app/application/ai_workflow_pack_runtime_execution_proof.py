from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    read_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
    text_file_contains_all,
)

AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV = "LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF"
AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION = (
    "lotus-idea.ai-workflow-pack-runtime-execution-proof.v1"
)

AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED = ("lotus_ai_runtime_execution_missing",)

REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS = (
    "certified_ai_lineage_store_missing",
    "workflow_pack_runtime_contract_not_certified",
    "model_risk_operations_dashboard_not_certified",
    "model_risk_operations_alerts_not_certified",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS = (
    "../lotus-ai/src/app/providers/idea_explanation_stub.py",
    "../lotus-ai/src/app/services/idea_explanation_guardrails.py",
    "../lotus-ai/src/app/services/workflow_pack_execution.py",
    "../lotus-ai/src/app/providers/stub_text_provider.py",
    "../lotus-ai/src/app/repositories/memory_caller_policy_repository.py",
    "../lotus-ai/alembic/versions/0034_seed_lotus_idea_caller_policy.py",
    "../lotus-ai/tests/support/workflow_pack_fixtures.py",
    "../lotus-ai/tests/unit/test_idea_explanation_guardrails.py",
    "../lotus-ai/tests/unit/test_workflow_pack_execution.py",
    "../lotus-ai/tests/unit/test_workflow_pack_bindings.py",
    "../lotus-ai/tests/unit/test_access_control_authorization.py",
    "../lotus-ai/tests/unit/test_sqlalchemy_caller_policy_repository.py",
    "src/app/application/ai_governance.py",
    "tests/unit/test_ai_governance.py",
    "make ai-workflow-pack-runtime-execution-proof-contract-gate",
    "lotus-ai make check",
    "lotus-ai PR Merge Gate / Lint Typecheck Security",
)


def build_ai_workflow_pack_runtime_execution_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path | None = None,
) -> dict[str, Any]:
    lotus_ai_root = lotus_ai_root or repository_root.parent / "lotus-ai"
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS)
    file_evidence_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={"../lotus-ai/": lotus_ai_root},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ", "lotus-ai make ", "lotus-ai PR Merge Gate /"),
    )
    make_target_evidence_present = required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    idea_provider_stub_implemented = _idea_provider_stub_implemented(lotus_ai_root)
    idea_guardrails_implemented = _idea_guardrails_implemented(lotus_ai_root)
    workflow_execution_invokes_idea_guardrails = text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_pack_execution.py",
        (
            "validate_idea_explanation_payload",
            'request.pack_id == "idea_explanation.pack"',
            "request.task_request.context.payload",
        ),
    )
    stub_provider_routes_idea_pack = text_file_contains_all(
        lotus_ai_root / "src/app/providers/stub_text_provider.py",
        (
            "build_idea_explanation_stub_result",
            'request.task_id == "explain.v1"',
            "idea_explanation_result",
        ),
    )
    caller_policy_authorizes_idea_without_control_privilege = (
        _caller_policy_authorizes_idea_without_control_privilege(lotus_ai_root)
    )
    tests_cover_idea_runtime_execution = _tests_cover_idea_runtime_execution(lotus_ai_root)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and idea_provider_stub_implemented
        and idea_guardrails_implemented
        and workflow_execution_invokes_idea_guardrails
        and stub_provider_routes_idea_pack
        and caller_policy_authorizes_idea_without_control_privilege
        and tests_cover_idea_runtime_execution
    )
    return {
        "schemaVersion": AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_ai_idea_workflow_pack_runtime_execution",
        "proofScope": "source_safe_runtime_execution_proof_only",
        "aiWorkflowPackRuntimeExecutionProofValid": proof_valid,
        "aggregateBlockersCleared": AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "ideaProviderStubImplemented": idea_provider_stub_implemented,
            "ideaGuardrailsImplemented": idea_guardrails_implemented,
            "workflowExecutionInvokesIdeaGuardrails": workflow_execution_invokes_idea_guardrails,
            "stubProviderRoutesIdeaPack": stub_provider_routes_idea_pack,
            "callerPolicyAuthorizesIdeaWithoutControlPrivilege": (
                caller_policy_authorizes_idea_without_control_privilege
            ),
            "testsCoverIdeaRuntimeExecution": tests_cover_idea_runtime_execution,
        },
        "remainingCertificationBlockers": (REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS),
        "workflowPackId": "idea_explanation.pack@v1",
        "workflowAuthorityOwner": "lotus-idea",
        "aiCapabilityOwner": "lotus-ai",
        "workflowPackRuntimeExecutionCertified": proof_valid,
        "lotusAiRuntimeExecuted": proof_valid,
        "deterministicStubExecution": proof_valid,
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
    if payload.get("proofScope") != "source_safe_runtime_execution_proof_only":
        return False
    if payload.get("aiWorkflowPackRuntimeExecutionProofValid") is not True:
        return False
    if payload.get("workflowPackId") != "idea_explanation.pack@v1":
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
    if payload.get("providerRolloutCertified") is not False:
        return False
    if payload.get("modelRiskDashboardCertified") is not False:
        return False
    if payload.get("modelRiskAlertsCertified") is not False:
        return False
    if payload.get("workbenchProductProofCertified") is not False:
        return False
    if payload.get("clientReadyPublicationAuthorized") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "makeTargetEvidencePresent",
            "ideaProviderStubImplemented",
            "ideaGuardrailsImplemented",
            "workflowExecutionInvokesIdeaGuardrails",
            "stubProviderRoutesIdeaPack",
            "callerPolicyAuthorizesIdeaWithoutControlPrivilege",
            "testsCoverIdeaRuntimeExecution",
        )
    )


def _idea_provider_stub_implemented(lotus_ai_root: Path) -> bool:
    return text_file_contains_all(
        lotus_ai_root / "src/app/providers/idea_explanation_stub.py",
        (
            "build_idea_explanation_stub_result",
            '"state": "REVIEW_REQUIRED"',
            '"client_ready_publication": "BLOCKED"',
            '"downstream_authority": "BLOCKED"',
            "advisor_and_reviewer_use_only",
            "human_review_required",
        ),
    )


def _idea_guardrails_implemented(lotus_ai_root: Path) -> bool:
    return text_file_contains_all(
        lotus_ai_root / "src/app/services/idea_explanation_guardrails.py",
        (
            "validate_idea_explanation_payload",
            "redacted_evidence_packet",
            "evidence_content_hash",
            "sha256:",
            "requested_outputs",
            "_FORBIDDEN_REQUESTED_OUTPUTS",
            "_FORBIDDEN_TECHNICAL_KEYS",
            "client_ready_publication",
            "human_review_required",
            "forbidden_actions",
        ),
    )


def _caller_policy_authorizes_idea_without_control_privilege(lotus_ai_root: Path) -> bool:
    memory_policy_text = read_text(
        lotus_ai_root / "src/app/repositories/memory_caller_policy_repository.py"
    )
    migration_text = read_text(
        lotus_ai_root / "alembic/versions/0034_seed_lotus_idea_caller_policy.py"
    )
    return (
        'caller_app="lotus-idea"' in memory_policy_text
        and 'allowed_task_ids=["explain.v1"]' in memory_policy_text
        and "allow_live_provider=False" in memory_policy_text
        and "allow_provider_control=False" in memory_policy_text
        and 'restricted_tenant_ids=["tenant-sg-001"]' in memory_policy_text
        and "'lotus-idea'" in migration_text
        and "'[\"explain.v1\"]'" in migration_text
        and "'RESTRICTED'" in migration_text
        and "'[\"tenant-sg-001\"]'" in migration_text
        and "false" in migration_text.lower()
    )


def _tests_cover_idea_runtime_execution(lotus_ai_root: Path) -> bool:
    guardrail_text = read_text(lotus_ai_root / "tests/unit/test_idea_explanation_guardrails.py")
    execution_text = read_text(lotus_ai_root / "tests/unit/test_workflow_pack_execution.py")
    binding_text = read_text(lotus_ai_root / "tests/unit/test_workflow_pack_bindings.py")
    access_control_text = read_text(
        lotus_ai_root / "tests/unit/test_access_control_authorization.py"
    )
    sqlalchemy_policy_text = read_text(
        lotus_ai_root / "tests/unit/test_sqlalchemy_caller_policy_repository.py"
    )
    fixture_text = read_text(lotus_ai_root / "tests/support/workflow_pack_fixtures.py")
    return (
        "validate_idea_explanation_payload(idea_explanation_payload())" in guardrail_text
        and "test_execute_workflow_pack_records_review_gated_idea_explanation_output"
        in execution_text
        and 'workflow_authority_owner == "lotus-idea"' in execution_text
        and "client_ready_publication" in execution_text
        and "test_validate_workflow_pack_execution_binding_runs_idea_explanation_guardrails"
        in execution_text
        and "test_get_workflow_pack_execution_binding_returns_idea_explanation_binding"
        in binding_text
        and "binding.validate_task_request_payload(payload=idea_explanation_payload())"
        in binding_text
        and 'caller_app="lotus-idea"' in access_control_text
        and "allow_live_provider is False" in sqlalchemy_policy_text
        and "idea_explanation_workflow_pack_execution_request_json" in fixture_text
    )
