from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/lotus-ai-provider-retention-consumer.v1.json"
REQUIRED_BINDINGS = {
    "workflow_run_id",
    "tenant_id",
    "provider_id",
    "provider_mode",
    "model_id",
    "model_version",
}
REQUIRED_REPLAY_FENCES = {
    "confirmation_id",
    "provider_confirmation_ref",
    "replay_nonce",
}


def validate_contract(path: Path = CONTRACT) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("producer_product_id") != "lotus-ai:ProviderRetentionConfirmation:v1":
        errors.append("producer product identity must match the Lotus AI contract")
    if set(payload.get("required_bindings", ())) != REQUIRED_BINDINGS:
        errors.append("required bindings must cover run, tenant, provider, and model identity")
    if set(payload.get("replay_fences", ())) != REQUIRED_REPLAY_FENCES:
        errors.append("replay fences must cover confirmation, provider reference, and nonce")
    if any(payload.get("source_safety", {}).values()):
        errors.append("provider retention receipt must exclude sensitive content")
    failure = payload.get("failure_policy", {})
    if failure != {
        "outcome": "PROVIDER_FAILURE",
        "supportability_status": "BLOCKED",
        "deletion_confirmed": False,
    }:
        errors.append("provider failure must remain blocked and cannot prove deletion")
    authority = payload.get("authority", {})
    if any(
        authority.get(key) != "not_granted"
        for key in (
            "bank_lifecycle_action",
            "archive_lifecycle_posture",
            "report_retention_policy",
        )
    ):
        errors.append("provider retention receipt must not grant external lifecycle authority")
    if payload.get("supportability_status") != "not_certified":
        errors.append("consumer posture must remain not_certified")
    if payload.get("supported_feature_promoted") is not False:
        errors.append("provider retention consumer must not promote a supported feature")
    if not payload.get("remaining_blockers"):
        errors.append("remaining certification blockers are required")
    return errors


def main() -> int:
    errors = validate_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("AI provider retention consumer contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
