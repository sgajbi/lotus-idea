from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application.runtime_trust_telemetry.test_execution_contract import (  # noqa: E402
    REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS,
    REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS,
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_BLOCKERS_SATISFIED,
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION,
    build_runtime_trust_telemetry_test_execution_payload,
    runtime_trust_telemetry_test_execution_is_valid,
)
from scripts.proof_source_safety import (  # noqa: E402
    forbidden_content_validator,
    validate_forbidden_content,
)

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "contentHash",
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
    "candidate_id",
    "client_id",
    "content_hash",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}

_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_runtime_trust_telemetry_test_execution_contract() -> list[str]:
    errors: list[str] = []
    contract = build_runtime_trust_telemetry_test_execution_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if contract.get("schemaVersion") != RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION:
        errors.append(
            "runtime trust telemetry test-execution schema must be "
            f"{RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION}"
        )
    if tuple(contract.get("evidenceRefs") or ()) != (
        REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS
    ):
        errors.append("runtime trust telemetry test execution must use governed evidence refs")
    if tuple(contract.get("aggregateBlockersSatisfied") or ()) != (
        RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_BLOCKERS_SATISFIED
    ):
        errors.append("runtime trust telemetry test execution must clear no runtime blocker")
    if tuple(contract.get("remainingCertificationBlockers") or ()) != (
        REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS
    ):
        errors.append("runtime trust telemetry test execution must retain runtime blockers")
    if not runtime_trust_telemetry_test_execution_is_valid(contract):
        errors.append("runtime trust telemetry test execution must validate against its contract")
    validate_forbidden_content(contract, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_runtime_trust_telemetry_test_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Runtime trust telemetry test-execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
