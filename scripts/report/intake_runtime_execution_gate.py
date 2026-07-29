from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_source_safety import validate_forbidden_content
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.report.intake_runtime_execution import (  # noqa: E402
    report_intake_runtime_execution_is_valid,
)

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


def main(argv: list[str] | None = None) -> int:
    path = Path(argv[0] if argv else "output/report/intake-runtime-execution-proof.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(payload, dict) or not report_intake_runtime_execution_is_valid(payload):
        errors.append("Report intake runtime execution proof failed contract validation")
    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    if errors:
        print("\n".join(errors))
        return 1
    print("Report intake runtime execution gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
