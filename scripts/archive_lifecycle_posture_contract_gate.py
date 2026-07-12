from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/lotus-archive-lifecycle-posture-consumer.v1.json"
REQUIRED_BINDINGS = {
    "tenant_id",
    "candidate_id",
    "evidence_pack_id",
    "document_id",
    "retention_policy_ref",
    "lifecycle_action",
}
REQUIRED_REPLAY_FENCES = {
    "applied_decision_replay_fence": "archive_decision_id",
    "applied_digest_replay_fence": "archive_payload_digest",
    "blocked_attempt_consumes_receipt": False,
}


def validate_contract(path: Path = CONTRACT) -> list[str]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("producer_product_id") != "lotus-archive:IdeaEvidenceLifecycleDecision:v1":
        errors.append("producer product identity must match the Lotus Archive contract")
    if payload.get("trust_bundle_environment") != (
        "LOTUS_IDEA_ARCHIVE_LIFECYCLE_TRUST_BUNDLE_JSON"
    ):
        errors.append("consumer must use the governed strict Archive trust bundle")
    if set(payload.get("required_bindings", ())) != REQUIRED_BINDINGS:
        errors.append(
            "receipt must bind tenant, candidate, evidence pack, document, policy, and action"
        )

    verification = payload.get("verification_controls", {})
    expected_verification = {
        "signature_algorithm": "Ed25519",
        "digest_algorithm": "sha256",
        "maximum_ttl_seconds": 300,
        "active_or_rotated_trusted_key_required": True,
        "exact_linked_evidence_pack_required": True,
        "disposal_authorized_must_be_false": True,
    }
    if verification != expected_verification:
        errors.append("Archive receipt verification controls must remain strict and source-bound")

    policy = payload.get("policy", {})
    if policy != {
        "archive_legal_hold_blocks_release_erase_and_purge": True,
        "apply_hold_requires_archive_action": "LEGAL_HOLD",
        "purge_requires_archive_action": "DISPOSAL_EXECUTED",
        "unlinked_candidate_requires_absent_receipt": True,
    }:
        errors.append("Archive hold, purge, and unlinked-candidate policy must remain fail closed")

    if any(payload.get("source_safety", {}).values()):
        errors.append("Archive posture receipt must exclude document, evidence, and client content")
    authority = payload.get("authority", {})
    if authority != {
        "archive_lifecycle_posture": "lotus-archive",
        "idea_owned_record_mutation": "lotus-idea",
        "bank_lifecycle_action": "independent_signed_authority_required",
        "archive_disposal_authority": "not_granted",
        "report_retention_policy_authority": "not_granted",
    }:
        errors.append("consumer must preserve bank, Archive, Report, and Idea authority boundaries")
    if payload.get("persistence") != {
        "migration": "015_archive_lifecycle_posture_receipt",
        **REQUIRED_REPLAY_FENCES,
    }:
        errors.append("migration 015 and applied-only decision/digest replay fencing are required")
    if payload.get("supportability_status") != "not_certified":
        errors.append("Archive lifecycle consumer posture must remain not_certified")
    if payload.get("supported_feature_promoted") is not False:
        errors.append("Archive lifecycle consumer must not promote a supported feature")
    if not payload.get("remaining_blockers"):
        errors.append("remaining production and authority blockers are required")
    return errors


def main() -> int:
    errors = validate_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Archive lifecycle posture consumer contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
