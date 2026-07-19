# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.observability import OperationOutcome  # noqa: E402
from app.domain.ai_action_policy import (  # noqa: E402
    AI_ACTION_POLICY_VERSION,
    AIActionPolicyReason,
)
from app.domain.ai_output_integrity import AI_OUTPUT_INTEGRITY_VERSION  # noqa: E402
from app.domain.ai_execution_provenance import (  # noqa: E402
    AI_EXECUTION_PROVENANCE_POLICY_VERSION,
)
from app.domain.ai_explanation import AI_CLAIM_GROUNDING_POLICY_VERSION  # noqa: E402
from app.domain.ai_metadata_policy import (  # noqa: E402
    AI_METADATA_ENVELOPE_VERSION,
    AI_METADATA_MAX_FIELDS,
    AI_METADATA_MAX_KEY_LENGTH,
    AI_METADATA_MAX_VALUE_LENGTH,
)

try:
    from scripts.operations_contract_validators import (  # noqa: E402
        validate_operations_contract_payload,
        validate_required_labels,
        validate_required_operations,
    )
except ModuleNotFoundError:
    from operations_contract_validators import (  # type: ignore[import-not-found,no-redef] # noqa: E402
        validate_operations_contract_payload,
        validate_required_labels,
        validate_required_operations,
    )


CONTRACT_PATH = Path("contracts/observability/lotus-idea-ai-model-risk-operations.v1.json")
EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
REQUIRED_DASHBOARD_CONTROLS = {
    "ai-explanation-readiness-posture",
    "ai-output-verifier-posture",
    "ai-lineage-durability-posture",
}
REQUIRED_ALERT_CANDIDATES = {
    "ai-explanation-unsupported-claim-block-rate",
    "ai-explanation-readiness-remains-blocked",
}
REQUIRED_NON_PROOF_BOUNDARIES = {
    "This contract is not lotus-ai runtime execution proof.",
    "This contract is not certified AI lineage-store proof.",
    "This contract is not Gateway or Workbench proof.",
    "This contract is not supported-feature promotion.",
}


def _load_contract(repository_root: Path, contract_path: Path) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("AI model-risk operations contract must be a JSON object")
    return payload


def validate_ai_model_risk_operations_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    payload = _load_contract(repository_root, contract_path)
    return validate_ai_model_risk_operations_contract_payload(
        payload,
        repository_root=repository_root,
    )


# fmt: off
def validate_ai_model_risk_operations_contract_payload(
    payload: dict[str, Any], *, repository_root: Path = ROOT
) -> list[str]:
    return validate_operations_contract_payload(payload, repository_root=repository_root, validators=OPERATIONS_CONTRACT_VALIDATORS)
# fmt: on


def _validate_header(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "contract_id": "lotus-idea-ai-model-risk-operations",
        "contract_version": "1.4.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_internal_foundation",
        "supportability_status": "not_certified",
        "supported_feature_promoted": False,
        "dashboard_source_contract_valid": True,
        "alert_rules_source_contract_valid": True,
        "action_content_policy_version": AI_ACTION_POLICY_VERSION,
        "claim_grounding_policy_version": AI_CLAIM_GROUNDING_POLICY_VERSION,
        "output_integrity_version": AI_OUTPUT_INTEGRITY_VERSION,
        "execution_provenance_policy_version": AI_EXECUTION_PROVENANCE_POLICY_VERSION,
        "metadata_envelope_version": AI_METADATA_ENVELOPE_VERSION,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"AI model-risk operations contract {key} must be {value!r}")
    return errors


def _validate_source_of_truth(
    payload: dict[str, Any],
    *,
    repository_root: Path,
) -> list[str]:
    source_of_truth = payload.get("source_of_truth")
    required_keys = {
        "ai_readiness_source",
        "ai_api_source",
        "action_policy_source",
        "claim_grounding_policy_source",
        "output_integrity_source",
        "execution_provenance_source",
        "metadata_policy_source",
        "data_lifecycle_contract",
        "operation_metric_contract",
        "contract_gate",
        "proof_contract_gate",
        "dashboard",
        "alert_rules",
        "model_risk_runbook",
        "operations_doc",
        "ai_governance_doc",
        "operations_runbook",
        "rfc_slice_09",
        "rfc_slice_15",
    }
    if not isinstance(source_of_truth, dict):
        return ["AI model-risk operations contract source_of_truth must be an object"]

    errors: list[str] = []
    missing = sorted(required_keys - set(source_of_truth))
    if missing:
        errors.append(
            "AI model-risk operations contract source_of_truth missing keys: " + ", ".join(missing)
        )
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str):
            errors.append(
                f"AI model-risk operations contract source_of_truth.{key} must be a string path"
            )
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"AI model-risk operations contract source_of_truth.{key} path must stay relative"
            )
            continue
        if not (repository_root / path).exists():
            errors.append(f"AI model-risk operations contract source_of_truth.{key} path missing")
    return errors


def _validate_action_content_policy(payload: dict[str, Any]) -> list[str]:
    policy = payload.get("action_content_policy")
    expected = {
        "input_posture": "untrusted_provider_content",
        "accepted_label_posture": "canonical_server_owned",
        "unsupported_script_posture": "fail_closed_ambiguous",
        "blocked_reasons": sorted(
            reason.value
            for reason in AIActionPolicyReason
            if reason is not AIActionPolicyReason.ALLOWED
        ),
        "raw_rejected_label_persisted": False,
        "raw_rejected_label_returned": False,
    }
    if policy != expected:
        return ["AI model-risk action_content_policy must match code-owned safety posture"]
    return []


def _validate_output_content_integrity(payload: dict[str, Any]) -> list[str]:
    expected = {
        "algorithm": "sha256",
        "canonicalization": "unicode_nfc_line_endings_order_preserving",
        "content_scope": [
            "explanation_text",
            "ordered_claim_id_text_and_source_bindings",
            "ordered_action_type_and_submitted_label",
            "workflow_pack_evaluator_and_policy_metadata",
        ],
        "persisted_content": "digest_and_version_only",
        "retention_policy_ref": "lotus-idea:regulated-advisory-evidence:seven-year:v1",
        "access_posture": "governed_evaluation_replay_or_authorized_lineage_store",
        "pre_v1_migration_posture": "explicitly_unverifiable_no_retroactive_claim",
    }
    if payload.get("output_content_integrity") != expected:
        return ["AI model-risk output_content_integrity must match code-owned audit posture"]
    return []


def _validate_claim_grounding(payload: dict[str, Any]) -> list[str]:
    expected = {
        "submitted_narrative_posture": "attested_input_not_advisor_visible",
        "accepted_narrative_posture": "server_rendered_from_verified_claims",
        "claim_identity_posture": "unique_and_order_preserving",
        "source_binding_posture": "redacted_evidence_source_products_only",
        "provider_output_binding": "digest_only_no_raw_provider_narrative_persistence",
        "advisor_projection": ("claim_text_plus_source_product_version_freshness_and_quality"),
        "unsupported_or_blocked_grounding_returned": False,
    }
    if payload.get("claim_grounding") != expected:
        return ["AI model-risk claim_grounding must match code-owned evidence posture"]
    return []


def _validate_execution_provenance(payload: dict[str, Any]) -> list[str]:
    expected = {
        "production_like_policy": "verified_lotus_ai_attestation_required",
        "local_test_policy": "unattested_fixture_allowed_non_production_only",
        "fallback_policy": "deterministic_fallback_allowed_without_ai_execution",
        "producer_attestation_available": True,
        "producer_contract": {
            "issue_ref": "sgajbi/lotus-ai#113",
            "main_commit_sha": "162df803a7a835813dc17116be674842f12aa544",
            "main_releasability_run_id": "29153879884",
        },
        "consumer_attestation_verification_available": True,
        "consumer_mainline_evidence": {
            "main_commit_sha": "f496c4429178eaa5679767bc8f1c3102e17d5eb2",
            "main_releasability_run_id": "29179489433",
        },
        "live_runtime_execution_certified": False,
        "remaining_certification_issue_ref": "sgajbi/lotus-idea#340",
        "unattested_output_clears_runtime_proof": False,
        "pre_attestation_migration_posture": "explicitly_unverifiable",
    }
    if payload.get("execution_provenance") != expected:
        return ["AI model-risk execution_provenance must match code-owned trust posture"]
    return []


def _validate_provider_safe_metadata(payload: dict[str, Any]) -> list[str]:
    expected = {
        "classification": "non_sensitive_operational_routing",
        "maximum_fields": AI_METADATA_MAX_FIELDS,
        "maximum_key_length": AI_METADATA_MAX_KEY_LENGTH,
        "maximum_value_length": AI_METADATA_MAX_VALUE_LENGTH,
        "allowed_fields": {
            "channel": {
                "allowed_values": ["advisor-workbench"],
                "allowed_purposes": [
                    "advisor_rationale_draft",
                    "meeting_preparation_draft",
                    "missing_evidence_check",
                    "unsupported_claim_verification",
                ],
            },
            "audience": {
                "allowed_values": ["internal_advisor_review"],
                "allowed_purposes": [
                    "advisor_rationale_draft",
                    "meeting_preparation_draft",
                ],
            },
        },
        "unknown_field_posture": "reject_before_candidate_lookup_or_provider_call",
        "unapproved_value_posture": "reject_before_candidate_lookup_or_provider_call",
        "provider_forwarding": "approved_envelope_only",
        "raw_values_persisted": False,
        "raw_values_logged": False,
        "retained_projection": "sorted_approved_field_names_only",
    }
    if payload.get("provider_safe_metadata") != expected:
        return ["AI model-risk provider_safe_metadata must match code-owned boundary policy"]
    return []


def _validate_dashboard_controls(payload: dict[str, Any]) -> list[str]:
    controls = payload.get("model_risk_dashboard_controls")
    if not isinstance(controls, list):
        return ["AI model-risk operations contract dashboard controls must be a list"]

    errors: list[str] = []
    observed: set[str] = set()
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            errors.append(f"dashboard controls[{index}] must be an object")
            continue
        control_id = control.get("control_id")
        if not isinstance(control_id, str) or not control_id.strip():
            errors.append(f"dashboard controls[{index}].control_id is required")
            continue
        observed.add(control_id)
        if not control.get("operator_question"):
            errors.append(f"{control_id}: operator_question is required")
        if control.get("implemented_metric_family") != EXPECTED_METRIC_NAME:
            errors.append(f"{control_id}: implemented_metric_family must be {EXPECTED_METRIC_NAME}")
        if control.get("source_contract_status") != "valid":
            errors.append(f"{control_id}: source_contract_status must be valid")
        if not control.get("required_endpoint"):
            errors.append(f"{control_id}: required_endpoint is required")
        errors.extend(validate_required_operations(control_id, control.get("required_operations")))
        errors.extend(validate_required_labels(control_id, control.get("required_labels")))
    missing = sorted(REQUIRED_DASHBOARD_CONTROLS - observed)
    extra = sorted(observed - REQUIRED_DASHBOARD_CONTROLS)
    if missing:
        errors.append(
            "AI model-risk operations contract missing dashboard controls: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "AI model-risk operations contract contains unsupported dashboard controls: "
            + ", ".join(extra)
        )
    return errors


def _validate_alert_candidates(payload: dict[str, Any]) -> list[str]:
    alerts = payload.get("model_risk_alert_candidates")
    if not isinstance(alerts, list):
        return ["AI model-risk operations contract alert candidates must be a list"]

    errors: list[str] = []
    observed: set[str] = set()
    valid_outcomes = {outcome.value for outcome in OperationOutcome}
    for index, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            errors.append(f"alert candidates[{index}] must be an object")
            continue
        alert_id = alert.get("alert_id")
        if not isinstance(alert_id, str) or not alert_id.strip():
            errors.append(f"alert candidates[{index}].alert_id is required")
            continue
        observed.add(alert_id)
        if alert.get("implemented_metric_family") != EXPECTED_METRIC_NAME:
            errors.append(f"{alert_id}: implemented_metric_family must be {EXPECTED_METRIC_NAME}")
        if alert.get("source_contract_status") != "valid":
            errors.append(f"{alert_id}: source_contract_status must be valid")
        if not alert.get("operator_response"):
            errors.append(f"{alert_id}: operator_response is required")
        errors.extend(validate_required_operations(alert_id, alert.get("required_operations")))
        outcomes = alert.get("required_outcomes")
        if not isinstance(outcomes, list) or not outcomes:
            errors.append(f"{alert_id}: required_outcomes must be a non-empty list")
        elif any(outcome not in valid_outcomes for outcome in outcomes):
            errors.append(f"{alert_id}: required_outcomes must use code-owned outcomes")
    missing = sorted(REQUIRED_ALERT_CANDIDATES - observed)
    extra = sorted(observed - REQUIRED_ALERT_CANDIDATES)
    if missing:
        errors.append(
            "AI model-risk operations contract missing alert candidates: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "AI model-risk operations contract contains unsupported alert candidates: "
            + ", ".join(extra)
        )
    return errors


def _validate_non_proof_boundaries(payload: dict[str, Any]) -> list[str]:
    boundaries = payload.get("non_proof_boundaries")
    if not isinstance(boundaries, list):
        return ["AI model-risk operations contract non_proof_boundaries must be a list"]
    missing = sorted(
        REQUIRED_NON_PROOF_BOUNDARIES - {item for item in boundaries if isinstance(item, str)}
    )
    if missing:
        return [
            "AI model-risk operations contract missing non-proof boundaries: " + "; ".join(missing)
        ]
    return []


OPERATIONS_CONTRACT_VALIDATORS = (
    _validate_header,
    _validate_source_of_truth,
    _validate_action_content_policy,
    _validate_output_content_integrity,
    _validate_claim_grounding,
    _validate_execution_provenance,
    _validate_provider_safe_metadata,
    _validate_dashboard_controls,
    _validate_alert_candidates,
    _validate_non_proof_boundaries,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the lotus-idea AI model-risk operations contract."
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=CONTRACT_PATH,
        help="Repository-relative AI model-risk operations contract path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_ai_model_risk_operations_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("AI model-risk operations contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
