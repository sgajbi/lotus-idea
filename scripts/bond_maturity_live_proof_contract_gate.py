from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.bond_maturity_live_proof import (
    BOND_MATURITY_LIVE_BLOCKERS_CLEARED,
    BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION,
    bond_maturity_live_proof_is_valid,
    build_bond_maturity_live_proof_payload,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_bond_maturity_live_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductIds",
    "generatedAtUtc",
    "liveCoreSourceAttempted",
    "runStatus",
    "holdingsRefPresent",
    "maturityFactRefPresent",
    "nextMaturityDatePresent",
    "maturingPositionCountPresent",
    "sourceEvidenceCurrent",
    "maturityDiagnostic",
    "sourceDiagnosticCodes",
    "supportedFeaturePromoted",
    "proofClosed",
    "aggregateBlockersCleared",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


def validate_bond_maturity_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_bond_maturity_live_proof.py is required")
        return errors

    payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "holdingsRefPresent": True,
            "maturityFactRefPresent": True,
            "nextMaturityDatePresent": True,
            "maturingPositionCountPresent": True,
            "sourceEvidenceCurrent": True,
            "maturityDiagnostic": "core_maturity_evidence_ready",
            "sourceDiagnosticCodes": ["core_maturity_evidence_ready"],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "bond maturity live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("bond maturity proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("bond maturity proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(BOND_MATURITY_LIVE_BLOCKERS_CLEARED):
        errors.append("bond maturity proof must clear only its live Core source blocker")
    for blocker in (
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"bond maturity proof must retain blocker `{blocker}`")
    if not bond_maturity_live_proof_is_valid(payload):
        errors.append("valid bond maturity proof fixture should validate")

    blocked_payload = build_bond_maturity_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "errorCode": "core_maturity_source_unavailable",
            "holdingsRefPresent": False,
            "maturityFactRefPresent": False,
            "nextMaturityDatePresent": False,
            "maturingPositionCountPresent": False,
            "sourceEvidenceCurrent": False,
            "maturityDiagnostic": "core_maturity_source_unavailable",
            "sourceDiagnosticCodes": ["core_maturity_source_unavailable"],
        },
    )
    if bond_maturity_live_proof_is_valid(blocked_payload):
        errors.append("blocked bond maturity proof fixture must not validate")

    _validate_forbidden_content(payload, errors)
    _validate_forbidden_content(blocked_payload, errors)
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
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def main() -> int:
    errors = validate_bond_maturity_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Bond maturity live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
