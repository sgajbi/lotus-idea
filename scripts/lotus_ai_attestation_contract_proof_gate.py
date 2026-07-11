from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.lotus_ai_attestation_contract_proof import (
    build_lotus_ai_attestation_contract_proof,
    lotus_ai_attestation_consumer_contract_is_valid,
    lotus_ai_attestation_contract_proof_is_valid,
)

try:
    from scripts.proof_source_safety import forbidden_content_validator
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "portfolioId",
    "prompt",
    "providerResponse",
    "rawPayload",
    "requestBody",
    "responseBody",
    "signature",
}
FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "portfolio_id",
    "raw prompt",
    "raw provider",
    "signature_base64url",
}
_validate_source_safety = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_lotus_ai_attestation_contract_proof(*, lotus_ai_root: Path | None = None) -> list[str]:
    resolved_lotus_ai_root = lotus_ai_root or ROOT.parent / "lotus-ai"
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=resolved_lotus_ai_root,
    )
    errors: list[str] = []
    producer_checkout_available = resolved_lotus_ai_root.is_dir()
    proof_valid = (
        lotus_ai_attestation_contract_proof_is_valid(proof)
        if producer_checkout_available
        else lotus_ai_attestation_consumer_contract_is_valid(proof)
    )
    if not proof_valid:
        scope = "cross-repository" if producer_checkout_available else "consumer-only"
        errors.append("local Lotus AI attestation contract proof must be valid")
        errors.append(f"Lotus AI attestation validation scope: {scope}")
    _validate_source_safety(proof, errors)
    return errors


def main() -> int:
    errors = validate_lotus_ai_attestation_contract_proof()
    if errors:
        print("\n".join(errors))
        return 1
    print("Lotus AI attestation contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
