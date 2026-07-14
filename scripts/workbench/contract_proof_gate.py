from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.application.workbench.contract_proof import (  # noqa: E402
    GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS,
    REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS,
    build_gateway_workbench_contract_proof_payload,
    gateway_workbench_contract_proof_is_valid,
)
from app.application.workbench.read_path_source_contract import (  # noqa: E402
    build_workbench_read_path_source_contract_proof_payload,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "eventId",
    "holdingId",
    "idempotencyKey",
    "payload",
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
    "client_id",
    "clientId",
    "correlation_id",
    "event_id",
    "idea_high_cash_001",
    "portfolio_id",
    "portfolioId",
    "request-body",
    "response-body",
    "/source/",
    "supported feature is promoted",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_gateway_workbench_contract_proof_contract() -> list[str]:
    errors: list[str] = []
    read_path_source_contract_proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof = build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_source_contract_proof=read_path_source_contract_proof,
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )
    if proof.get("schemaVersion") != GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append(
            "Gateway/Workbench contract proof schema must be "
            f"{GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS
    ):
        errors.append("Gateway/Workbench local evidence refs must match the contract")
    if tuple(proof.get("declaredRouteRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS
    ):
        errors.append("Gateway/Workbench declared route refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("Gateway/Workbench source-contract proof must clear no blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS
    ):
        errors.append("Gateway/Workbench contract proof must retain runtime/product blockers")
    if not gateway_workbench_contract_proof_is_valid(proof):
        errors.append("Gateway/Workbench contract proof must validate")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_gateway_workbench_contract_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Gateway/Workbench contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
