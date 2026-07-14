from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application.data_mesh.platform_catalog_source_contract import (  # noqa: E402
    PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED,
    PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION,
    REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS,
    REQUIRED_PLATFORM_MESH_EVIDENCE_REFS,
    build_platform_mesh_onboarding_proof_payload,
    platform_mesh_onboarding_proof_is_valid,
)

try:
    from scripts.proof_source_safety import (  # noqa: E402
        forbidden_content_validator,
        validate_forbidden_content,
    )
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]  # noqa: E402

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "contentHash",
    "correlationId",
    "holdingId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "content_hash",
    "correlation_id",
    "holding_id",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_platform_mesh_onboarding_proof_contract(
    *,
    platform_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    proof = build_platform_mesh_onboarding_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )
    if proof.get("schemaVersion") != PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION:
        errors.append(
            "platform mesh onboarding proof schema must be "
            f"{PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_PLATFORM_MESH_EVIDENCE_REFS:
        errors.append("platform mesh onboarding proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED
    ):
        errors.append("platform mesh onboarding proof must clear only platform inclusion blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS
    ):
        errors.append("platform mesh onboarding proof must retain certification blockers")
    proof_checks = proof.get("proofChecks")
    file_evidence_present = (
        isinstance(proof_checks, Mapping) and proof_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not platform_mesh_onboarding_proof_is_valid(proof):
        errors.append(
            "platform mesh onboarding proof must validate against sibling platform truth when "
            "sibling evidence is present"
        )
    if not file_evidence_present and proof.get("platformMeshOnboardingProofValid") is not False:
        errors.append("missing sibling platform evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_platform_mesh_onboarding_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Platform mesh onboarding proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
