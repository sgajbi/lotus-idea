from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application.downstream_realization.route_source_contract import (  # noqa: E402
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_ROUTE_PROFILE,
    MANAGE_ACTION_ROUTE,
    MANAGE_ROUTE_PROFILE,
    REMAINING_ADVISE_ROUTE_BLOCKERS,
    REMAINING_MANAGE_ROUTE_BLOCKERS,
    REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS,
    REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS,
    ROUTE_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
    ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
    advise_route_source_contract_is_valid,
    build_advise_route_source_contract_payload,
    build_manage_route_source_contract_payload,
    manage_route_source_contract_is_valid,
)

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


def validate_route_source_contracts() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-downstream-route-proof-") as temp_dir:
        temp_root = Path(temp_dir)
        advise_proof = build_advise_route_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            advise_root=_write_advise_fixture(temp_root),
        )
        manage_proof = build_manage_route_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            manage_root=_write_manage_fixture(temp_root),
        )

    _validate_profile_proof(
        advise_proof,
        contract_name="Advise route source contract",
        target_route=ADVISE_PROPOSAL_ROUTE,
        remaining_blockers=REMAINING_ADVISE_ROUTE_BLOCKERS,
        valid=advise_route_source_contract_is_valid,
        errors=errors,
    )
    _validate_profile_proof(
        manage_proof,
        contract_name="Manage route source contract",
        target_route=MANAGE_ACTION_ROUTE,
        remaining_blockers=REMAINING_MANAGE_ROUTE_BLOCKERS,
        valid=manage_route_source_contract_is_valid,
        errors=errors,
    )
    return errors


def _validate_profile_proof(
    proof: Mapping[str, object],
    *,
    contract_name: str,
    target_route: str,
    remaining_blockers: tuple[str, ...],
    valid: Callable[[Mapping[str, object]], bool],
    errors: list[str],
) -> None:
    if proof.get("schemaVersion") != ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION:
        errors.append(f"{contract_name} schema version is incorrect")
    if proof.get("sourceContractValid") is not True:
        errors.append(f"{contract_name} must be valid for contract fixtures")
    if proof.get("targetRoute") != target_route:
        errors.append(f"{contract_name} target route mismatch")
    if tuple(proof.get("sourceContractBlockersSatisfied") or ()) != (
        ROUTE_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    ):
        errors.append(f"{contract_name} must not satisfy live blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != remaining_blockers:
        errors.append(f"{contract_name} must retain live and authority blockers")
    if not valid(proof):
        errors.append(f"{contract_name} must validate against downstream contract truth")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)


def _write_advise_fixture(temp_root: Path) -> Path:
    advise_root = temp_root / "lotus-advise"
    _write_required_files(advise_root, ADVISE_ROUTE_PROFILE.source_refs)
    contract_path = advise_root / ADVISE_ROUTE_PROFILE.contract_path
    contract_path.write_text(json.dumps(_advise_contract_payload()), encoding="utf-8")
    return advise_root


def _write_manage_fixture(temp_root: Path) -> Path:
    manage_root = temp_root / "lotus-manage"
    _write_required_files(manage_root, MANAGE_ROUTE_PROFILE.source_refs)
    contract_path = manage_root / MANAGE_ROUTE_PROFILE.contract_path
    contract_path.write_text(json.dumps(_manage_contract_payload()), encoding="utf-8")
    return manage_root


def _write_required_files(root: Path, source_refs: tuple[str, ...]) -> None:
    for ref in source_refs:
        path = root / ref
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
        "certification_blockers": list(REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS),
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
        "certification_blockers": list(REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS),
    }


def main() -> int:
    errors = validate_route_source_contracts()
    if errors:
        print("\n".join(errors))
        return 1
    print("Downstream route source-contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
