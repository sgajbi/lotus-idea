# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.ai_attestation.source_contract import (  # noqa: E402
    AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
    build_ai_attestation_source_contract,
    idea_consumer_source_contract_is_valid,
    signed_ai_attestation_source_contract_is_valid,
)
from scripts.proof_source_safety import (  # noqa: E402
    forbidden_content_validator,
    validate_forbidden_content,
)


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


def validate_ai_attestation_source_contract(
    *,
    lotus_ai_root: Path | None = None,
) -> list[str]:
    resolved_lotus_ai_root = lotus_ai_root or ROOT.parent / "lotus-ai"
    payload = build_ai_attestation_source_contract(
        generated_at_utc=datetime(2026, 7, 15, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=resolved_lotus_ai_root,
    )
    errors: list[str] = []
    if tuple(payload.get("sourceContractBlockersSatisfied") or ()) != (
        AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    ):
        errors.append("signed AI attestation source contract must clear no blockers")
    if resolved_lotus_ai_root.is_dir():
        if not signed_ai_attestation_source_contract_is_valid(payload):
            errors.append("full signed AI attestation source contract must be valid")
    elif not idea_consumer_source_contract_is_valid(payload):
        errors.append("Idea consumer-only attestation source contract must be valid")
    validate_forbidden_content(
        payload,
        errors,
        FORBIDDEN_KEYS,
        FORBIDDEN_TEXT_FRAGMENTS,
    )
    return errors


def main() -> int:
    errors = validate_ai_attestation_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Signed AI attestation source-contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
