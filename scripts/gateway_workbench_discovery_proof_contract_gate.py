from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.gateway_workbench_discovery_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS,
    build_gateway_workbench_discovery_proof_payload,
    gateway_workbench_discovery_proof_is_valid,
)
from app.application.gateway_workbench_operational_proof import (
    build_gateway_workbench_operational_proof_payload,
)
from app.application.platform_mesh_onboarding_proof import (
    build_platform_mesh_onboarding_proof_payload,
)
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload


ROOT = Path(__file__).resolve().parents[1]
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


def validate_gateway_workbench_discovery_proof_contract() -> list[str]:
    errors: list[str] = []
    generated_at_utc = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    workbench_read_path_proof = build_workbench_read_path_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
    )
    gateway_workbench_operational_proof = build_gateway_workbench_operational_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        workbench_read_path_proof=workbench_read_path_proof,
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
    )
    platform_mesh_onboarding_proof = build_platform_mesh_onboarding_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        platform_root=PLATFORM_ROOT,
    )
    proof = build_gateway_workbench_discovery_proof_payload(
        generated_at_utc=generated_at_utc,
        repository_root=ROOT,
        platform_root=PLATFORM_ROOT,
        platform_mesh_onboarding_proof=platform_mesh_onboarding_proof,
        workbench_read_path_proof=workbench_read_path_proof,
        gateway_workbench_operational_proof=gateway_workbench_operational_proof,
        platform_mesh_onboarding_proof_ref="output/data-mesh/platform-mesh-onboarding-proof.json",
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
        gateway_workbench_operational_proof_ref=(
            "output/workbench/gateway-workbench-operational-proof.json"
        ),
    )
    if proof.get("schemaVersion") != GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION:
        errors.append(
            "Gateway/Workbench discovery proof schema must be "
            f"{GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS_CLEARED
    ):
        errors.append("Gateway/Workbench discovery proof must clear only discovery blocker")
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
        errors.append("Gateway/Workbench discovery proof must retain certification blockers")
    if not gateway_workbench_discovery_proof_is_valid(proof):
        errors.append("Gateway/Workbench discovery proof must validate against its contract")
    _validate_forbidden_content(proof, errors)
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
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def main() -> int:
    errors = validate_gateway_workbench_discovery_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Gateway/Workbench discovery proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
