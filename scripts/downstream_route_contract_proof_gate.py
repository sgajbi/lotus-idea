from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Callable
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_PROPOSAL_ROUTE_PROFILE,
    ADVISE_ROUTE_BLOCKERS_CLEARED,
    DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION,
    MANAGE_ACTION_ROUTE,
    MANAGE_ACTION_ROUTE_PROFILE,
    MANAGE_ROUTE_BLOCKERS_CLEARED,
    REMAINING_ADVISE_ROUTE_BLOCKERS,
    REMAINING_MANAGE_ROUTE_BLOCKERS,
    build_advise_proposal_route_proof_payload,
    build_manage_action_route_proof_payload,
    advise_proposal_route_proof_is_valid,
    manage_action_route_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[1]

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


def validate_downstream_route_contract_proofs() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-downstream-route-proof-") as temp_dir:
        temp_root = Path(temp_dir)
        advise_proof = build_advise_proposal_route_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            advise_root=_write_advise_fixture(temp_root),
        )
        manage_proof = build_manage_action_route_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            manage_root=_write_manage_fixture(temp_root),
        )

    _validate_profile_proof(
        advise_proof,
        route_valid_field="adviseProposalRouteProofValid",
        target_route=ADVISE_PROPOSAL_ROUTE,
        blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
        remaining_blockers=REMAINING_ADVISE_ROUTE_BLOCKERS,
        valid=advise_proposal_route_proof_is_valid,
        errors=errors,
    )
    _validate_profile_proof(
        manage_proof,
        route_valid_field="manageActionRouteProofValid",
        target_route=MANAGE_ACTION_ROUTE,
        blockers_cleared=MANAGE_ROUTE_BLOCKERS_CLEARED,
        remaining_blockers=REMAINING_MANAGE_ROUTE_BLOCKERS,
        valid=manage_action_route_proof_is_valid,
        errors=errors,
    )
    return errors


def _validate_profile_proof(
    proof: Mapping[str, object],
    *,
    route_valid_field: str,
    target_route: str,
    blockers_cleared: tuple[str, ...],
    remaining_blockers: tuple[str, ...],
    valid: Callable[[Mapping[str, object]], bool],
    errors: list[str],
) -> None:
    if proof.get("schemaVersion") != DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append("downstream route proof schema version is incorrect")
    if proof.get(route_valid_field) is not True:
        errors.append(f"{route_valid_field} must be true for contract fixtures")
    if proof.get("targetRoute") != target_route:
        errors.append(f"{route_valid_field} target route mismatch")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != blockers_cleared:
        errors.append(f"{route_valid_field} must clear only its route blocker")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != remaining_blockers:
        errors.append(f"{route_valid_field} must retain downstream authority blockers")
    if not valid(proof):
        errors.append(f"{route_valid_field} must validate against downstream contract truth")
    _validate_forbidden_content(proof, errors)


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


def _write_advise_fixture(temp_root: Path) -> Path:
    advise_root = temp_root / "lotus-advise"
    _write_required_files(advise_root, ADVISE_PROPOSAL_ROUTE_PROFILE.evidence_refs)
    contract_path = advise_root / ADVISE_PROPOSAL_ROUTE_PROFILE.contract_path
    contract_path.write_text(json.dumps(_advise_contract_payload()), encoding="utf-8")
    return advise_root


def _write_manage_fixture(temp_root: Path) -> Path:
    manage_root = temp_root / "lotus-manage"
    _write_required_files(manage_root, MANAGE_ACTION_ROUTE_PROFILE.evidence_refs)
    contract_path = manage_root / MANAGE_ACTION_ROUTE_PROFILE.contract_path
    contract_path.write_text(json.dumps(_manage_contract_payload()), encoding="utf-8")
    return manage_root


def _write_required_files(root: Path, evidence_refs: tuple[str, ...]) -> None:
    for ref in evidence_refs:
        if not ref.startswith("../"):
            continue
        relative = ref.split("/", maxsplit=2)[2]
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# source-safe fixture\n", encoding="utf-8")


def _advise_contract_payload() -> dict[str, object]:
    return {
        "contract_id": "lotus-advise-idea-proposal-intake",
        "repository": "lotus-advise",
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": "lotus-idea:IdeaCandidate:v1",
        "owned_product": "lotus-advise:AdvisoryProposalLifecycleRecord:v1",
        "source_authority": "lotus-idea",
        "proposal_authority": "lotus-advise",
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "downstream_execution_proven": False,
        "supported_feature_promoted": False,
        "target_route": ADVISE_PROPOSAL_ROUTE,
        "non_proof_boundaries": [
            "Proves only a live route foundation for source-safe lotus-idea proposal intake.",
            "Does not grant suitability, policy approval, or client-communication authority.",
            "Does not create orders, execution instructions, fills, or settlement records.",
            "Does not promote a supported feature in lotus-advise or lotus-idea.",
        ],
        "certification_blockers": list(REMAINING_ADVISE_ROUTE_BLOCKERS),
    }


def _manage_contract_payload() -> dict[str, object]:
    return {
        "contract_id": "lotus-manage-idea-action-intake",
        "repository": "lotus-manage",
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": "lotus-idea:IdeaCandidate:v1",
        "owned_product": "lotus-manage:PortfolioActionRegister:v1",
        "source_authority": "lotus-manage",
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "downstream_execution_proven": False,
        "supported_feature_promoted": False,
        "target_route": MANAGE_ACTION_ROUTE,
        "non_proof_boundaries": [
            "Proves only a live route foundation for source-safe lotus-idea action intake.",
            "Does not grant suitability, mandate approval, or client-communication authority.",
            "Does not create orders, execution instructions, fills, or settlement records.",
            "Does not promote a supported feature in lotus-manage or lotus-idea.",
        ],
        "certification_blockers": list(REMAINING_MANAGE_ROUTE_BLOCKERS),
    }


def main() -> int:
    errors = validate_downstream_route_contract_proofs()
    if errors:
        print("\n".join(errors))
        return 1
    print("Downstream route contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
