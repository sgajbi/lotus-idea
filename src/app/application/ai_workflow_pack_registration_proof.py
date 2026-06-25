from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV = "LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF"
AI_WORKFLOW_PACK_REGISTRATION_PROOF_SCHEMA_VERSION = (
    "lotus-idea.ai-workflow-pack-registration-proof.v1"
)

AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS_CLEARED = ("workflow_pack_runtime_contract_not_certified",)

REMAINING_AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS = (
    "certified_ai_lineage_store_missing",
    "lotus_ai_runtime_execution_missing",
    "model_risk_operations_dashboard_not_certified",
    "model_risk_operations_alerts_not_certified",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_AI_WORKFLOW_PACK_EVIDENCE_REFS = (
    "../lotus-ai/src/app/services/workflow_pack_phase1_specs.py",
    "../lotus-ai/src/app/services/workflow_pack_registry_seed.py",
    "../lotus-ai/src/app/services/workflow_pack_bindings.py",
    "../lotus-ai/src/app/services/workflow_pack_queue_policy_catalog.py",
    "../lotus-ai/src/app/services/ai_surface_supportability.py",
    "../lotus-ai/tests/unit/test_workflow_pack_registry.py",
    "../lotus-ai/tests/unit/test_workflow_pack_bindings.py",
    "../lotus-ai/tests/unit/test_workflow_pack_queue_policy_catalog.py",
    "../lotus-ai/tests/unit/test_workflow_pack_runtime_status.py",
    "../lotus-ai/tests/integration/test_workflow_pack_registry_api_contract.py",
    "src/app/application/ai_governance.py",
    "src/app/domain/ai_lineage_persistence.py",
    "tests/unit/test_ai_governance.py",
    "make ai-workflow-pack-registration-proof-contract-gate",
    "lotus-ai make check",
    "lotus-ai PR Merge Gate / Lint Typecheck Security",
)


def build_ai_workflow_pack_registration_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path | None = None,
) -> dict[str, Any]:
    lotus_ai_root = lotus_ai_root or repository_root.parent / "lotus-ai"
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_AI_WORKFLOW_PACK_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        lotus_ai_root=lotus_ai_root,
        evidence_refs=evidence_refs,
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    phase1_spec_declares_idea_authority = _phase1_spec_declares_idea_authority(lotus_ai_root)
    registry_seed_declares_idea_registration = _registry_seed_declares_idea_registration(
        lotus_ai_root
    )
    binding_registry_includes_idea_pack = _text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_pack_bindings.py",
        ("IDEA_EXPLANATION_V1_SPEC", "_build_execution_binding_from_spec"),
    )
    queue_policy_includes_idea_pack = _text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_pack_queue_policy_catalog.py",
        ("_review_support_idea_explanation_policy", "queue-policy.idea-explanation.v1"),
    )
    supportability_surface_includes_idea_pack = _text_file_contains_all(
        lotus_ai_root / "src/app/services/ai_surface_supportability.py",
        ("idea_explanation.pack@v1", "lotus-idea"),
    )
    tests_cover_idea_pack = _tests_cover_idea_pack(lotus_ai_root)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and phase1_spec_declares_idea_authority
        and registry_seed_declares_idea_registration
        and binding_registry_includes_idea_pack
        and queue_policy_includes_idea_pack
        and supportability_surface_includes_idea_pack
        and tests_cover_idea_pack
    )
    return {
        "schemaVersion": AI_WORKFLOW_PACK_REGISTRATION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_ai_idea_workflow_pack_registration_contract",
        "proofScope": "source_safe_workflow_pack_registration_only",
        "aiWorkflowPackRegistrationProofValid": proof_valid,
        "aggregateBlockersCleared": AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "phase1SpecDeclaresIdeaAuthority": phase1_spec_declares_idea_authority,
            "registrySeedDeclaresIdeaRegistration": registry_seed_declares_idea_registration,
            "bindingRegistryIncludesIdeaPack": binding_registry_includes_idea_pack,
            "queuePolicyIncludesIdeaPack": queue_policy_includes_idea_pack,
            "supportabilitySurfaceIncludesIdeaPack": supportability_surface_includes_idea_pack,
            "testsCoverIdeaPack": tests_cover_idea_pack,
        },
        "remainingCertificationBlockers": REMAINING_AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS,
        "workflowPackId": "idea_explanation.pack@v1",
        "workflowAuthorityOwner": "lotus-idea",
        "aiCapabilityOwner": "lotus-ai",
        "workflowPackRegistrationContractCertified": proof_valid,
        "workflowPackRuntimeExecutionCertified": False,
        "lotusAiRuntimeExecuted": False,
        "modelRiskDashboardCertified": False,
        "modelRiskAlertsCertified": False,
        "workbenchProductProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def ai_workflow_pack_registration_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != AI_WORKFLOW_PACK_REGISTRATION_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "lotus_ai_idea_workflow_pack_registration_contract":
        return False
    if payload.get("proofScope") != "source_safe_workflow_pack_registration_only":
        return False
    if payload.get("aiWorkflowPackRegistrationProofValid") is not True:
        return False
    if payload.get("workflowPackId") != "idea_explanation.pack@v1":
        return False
    if payload.get("workflowAuthorityOwner") != "lotus-idea":
        return False
    if payload.get("aiCapabilityOwner") != "lotus-ai":
        return False
    if payload.get("workflowPackRegistrationContractCertified") is not True:
        return False
    if payload.get("workflowPackRuntimeExecutionCertified") is not False:
        return False
    if payload.get("lotusAiRuntimeExecuted") is not False:
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
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_AI_WORKFLOW_PACK_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_WORKFLOW_PACK_REGISTRATION_BLOCKERS
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
            "phase1SpecDeclaresIdeaAuthority",
            "registrySeedDeclaresIdeaRegistration",
            "bindingRegistryIncludesIdeaPack",
            "queuePolicyIncludesIdeaPack",
            "supportabilitySurfaceIncludesIdeaPack",
            "testsCoverIdeaPack",
        )
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    lotus_ai_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("make ", "lotus-ai make ", "lotus-ai PR Merge Gate /")):
            continue
        if ref.startswith("../lotus-ai/"):
            path = lotus_ai_root / ref.removeprefix("../lotus-ai/")
        else:
            path = repository_root / ref
        if not path.is_file():
            return False
    return True


def _required_make_target_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    try:
        makefile_text = (repository_root / "Makefile").read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        target = f"{ref.removeprefix('make ')}:"
        if target not in makefile_text:
            return False
    return True


def _phase1_spec_declares_idea_authority(lotus_ai_root: Path) -> bool:
    return _text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_pack_phase1_specs.py",
        (
            "IDEA_EXPLANATION_V1_SPEC",
            'pack_id="idea_explanation.pack"',
            'pack_family="idea_explanation"',
            'owner_repository="lotus-idea"',
            'owner_service="lotus-idea"',
            'primary_use_case="governed_idea_explanation"',
            'workflow_authority_owner="lotus-idea"',
            '"lotus-idea"',
            '"lotus-gateway"',
            '"redacted_evidence_packet"',
            '"explanation_request"',
            '"supportability"',
        ),
    )


def _registry_seed_declares_idea_registration(lotus_ai_root: Path) -> bool:
    return _text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_pack_registry_seed.py",
        (
            "IDEA_EXPLANATION_V1_SPEC",
            "WorkflowPackExecutionMode.REVIEW_GATED",
            "WorkflowPackActivationState.PILOT",
            "repo://lotus-idea/src/app/domain/ai_governance.py",
            "_idea_explanation_v1_definition_refs",
            "src/app/application/ai_governance.py",
            "src/app/api/ai_governance.py",
            "tests/unit/test_ai_governance.py",
            "cannot create suitability approval",
            "client-ready publication",
            "supported-feature promotion",
        ),
    )


def _tests_cover_idea_pack(lotus_ai_root: Path) -> bool:
    registry_text = _read_text(lotus_ai_root / "tests/unit/test_workflow_pack_registry.py")
    binding_text = _read_text(lotus_ai_root / "tests/unit/test_workflow_pack_bindings.py")
    queue_policy_text = _read_text(
        lotus_ai_root / "tests/unit/test_workflow_pack_queue_policy_catalog.py"
    )
    runtime_status_text = _read_text(
        lotus_ai_root / "tests/unit/test_workflow_pack_runtime_status.py"
    )
    integration_text = _read_text(
        lotus_ai_root / "tests/integration/test_workflow_pack_registry_api_contract.py"
    )
    return (
        "idea_explanation.pack" in registry_text
        and "lotus-idea" in registry_text
        and "idea_explanation.pack" in binding_text
        and "queue-policy.idea-explanation.v1" in queue_policy_text
        and "idea_explanation.pack@v1" in runtime_status_text
        and "idea_explanation.pack" in integration_text
        and "default_registration_ref" in integration_text
    )


def _text_file_contains_all(path: Path, fragments: tuple[str, ...]) -> bool:
    text = _read_text(path)
    return bool(text) and all(fragment in text for fragment in fragments)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _is_timezone_aware_datetime_text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None
