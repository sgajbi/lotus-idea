# ruff: noqa: E402
from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.workbench.discovery_contract_proof import (  # noqa: E402
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS,
    build_gateway_workbench_discovery_contract_proof_payload,
    gateway_workbench_discovery_contract_proof_is_valid,
)
from app.application.workbench.contract_proof import (  # noqa: E402
    build_gateway_workbench_contract_proof_payload,
)
from app.application.data_mesh.platform_catalog_source_contract import (  # noqa: E402
    build_platform_catalog_source_contract_payload,
)
from app.application.workbench.read_path_source_contract import (  # noqa: E402
    build_workbench_read_path_source_contract_proof_payload,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

PLATFORM_ROOT = ROOT.parent / "lotus-platform"

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


def validate_gateway_workbench_discovery_contract_proof_contract(
    *,
    platform_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    effective_platform_root = platform_root or PLATFORM_ROOT
    generated_at_utc = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    read_path_source_contract_proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
    )
    gateway_workbench_contract_proof = build_gateway_workbench_contract_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        workbench_read_path_source_contract_proof=read_path_source_contract_proof,
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )
    platform_catalog_source_contract = build_platform_catalog_source_contract_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        platform_root=effective_platform_root,
    )
    proof = build_gateway_workbench_discovery_contract_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        platform_root=effective_platform_root,
        platform_catalog_source_contract=platform_catalog_source_contract,
        workbench_read_path_source_contract_proof=read_path_source_contract_proof,
        gateway_workbench_contract_proof=gateway_workbench_contract_proof,
        platform_catalog_source_contract_ref="output/data-mesh/platform-catalog-source-contract.json",
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
        gateway_workbench_contract_proof_ref=(
            "output/workbench/gateway-workbench-contract-proof.json"
        ),
    )
    if proof.get("schemaVersion") != GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append(
            "Gateway/Workbench discovery contract proof schema must be "
            f"{GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("Gateway/Workbench discovery contract proof must clear no runtime blocker")
    if tuple(proof.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS
    ):
        errors.append("Gateway/Workbench discovery local evidence refs must match contract")
    if tuple(proof.get("platformEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS
    ):
        errors.append("Gateway/Workbench discovery platform evidence refs must match contract")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS
    ):
        errors.append(
            "Gateway/Workbench discovery contract proof must retain certification blockers"
        )
    proof_checks = proof.get("proofChecks")
    file_evidence_present = (
        isinstance(proof_checks, Mapping) and proof_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not gateway_workbench_discovery_contract_proof_is_valid(proof):
        errors.append(
            "Gateway/Workbench discovery contract proof must validate against sibling platform truth when "
            "sibling evidence is present"
        )
    if (
        not file_evidence_present
        and proof.get("gatewayWorkbenchDiscoveryContractProofValid") is not False
    ):
        errors.append("missing sibling platform evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_gateway_workbench_discovery_contract_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Gateway/Workbench discovery contract proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
