# ruff: noqa: E402
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.workbench.owner_mainline_evidence import (  # noqa: E402
    OWNER_MAINLINE_EVIDENCE_CONTRACT_REF,
    validate_owner_mainline_evidence_contract,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
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
    "candidateId",
    "clientId",
    "portfolioId",
    "request-body",
    "response-body",
    "/source/",
}


def validate_owner_mainline_evidence_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Owner-mainline evidence contract is unreadable: {exc}"]
    if not isinstance(payload, dict):
        return ["Owner-mainline evidence contract must be a JSON object"]
    errors.extend(
        validate_owner_mainline_evidence_contract(payload, repository_root=ROOT),
    )
    validate_forbidden_content(
        payload,
        errors,
        FORBIDDEN_KEYS,
        FORBIDDEN_TEXT_FRAGMENTS,
    )
    return errors


def main() -> int:
    errors = validate_owner_mainline_evidence_file(ROOT / OWNER_MAINLINE_EVIDENCE_CONTRACT_REF)
    if errors:
        print("\n".join(errors))
        return 1
    print("Gateway/Workbench owner-mainline evidence gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
