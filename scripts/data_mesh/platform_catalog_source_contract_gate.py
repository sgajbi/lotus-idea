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
    PLATFORM_CATALOG_SOURCE_BLOCKERS_SATISFIED,
    PLATFORM_CATALOG_SOURCE_CONTRACT_SCHEMA_VERSION,
    REMAINING_PLATFORM_CATALOG_CERTIFICATION_BLOCKERS,
    REQUIRED_PLATFORM_CATALOG_EVIDENCE_REFS,
    build_platform_catalog_source_contract_payload,
    platform_catalog_source_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402

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


def validate_platform_catalog_source_contract(
    *,
    platform_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    proof = build_platform_catalog_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )
    if proof.get("schemaVersion") != PLATFORM_CATALOG_SOURCE_CONTRACT_SCHEMA_VERSION:
        errors.append(
            "platform catalog source contract schema must be "
            f"{PLATFORM_CATALOG_SOURCE_CONTRACT_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_PLATFORM_CATALOG_EVIDENCE_REFS:
        errors.append("platform catalog source contract evidence refs must match the contract")
    if proof.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("platform catalog source contract must declare source_contract evidence")
    if tuple(proof.get("sourceContractBlockersSatisfied") or ()) != (
        PLATFORM_CATALOG_SOURCE_BLOCKERS_SATISFIED
    ):
        errors.append(
            "platform catalog source contract must satisfy only platform inclusion blockers"
        )
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_PLATFORM_CATALOG_CERTIFICATION_BLOCKERS
    ):
        errors.append("platform catalog source contract must retain certification blockers")
    contract_checks = proof.get("contractChecks")
    file_evidence_present = (
        isinstance(contract_checks, Mapping) and contract_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not platform_catalog_source_contract_is_valid(proof):
        errors.append(
            "platform catalog source contract must validate against sibling platform truth when "
            "sibling evidence is present"
        )
    if not file_evidence_present and proof.get("sourceContractValid") is not False:
        errors.append("missing sibling platform evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_platform_catalog_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Platform catalog source contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
