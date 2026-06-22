from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.downstream_realization_contracts import (  # noqa: E402
    DOWNSTREAM_CONTRACT_PLAN_PATH,
    DownstreamRealizationContractPlan,
    downstream_realization_contract_plan_from_payload,
    load_downstream_realization_contract_plan,
)


REQUIRED_CONTRACTS = {
    "lotus-idea-to-lotus-advise-proposal-intake:v1": "lotus-advise",
    "lotus-idea-to-lotus-manage-action-intake:v1": "lotus-manage",
    "lotus-idea-to-lotus-report-evidence-pack-intake:v1": "lotus-report",
}
REQUIRED_EVIDENCE_REFS = {
    "lotus-idea-to-lotus-advise-proposal-intake:v1": {
        "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
        "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
    },
    "lotus-idea-to-lotus-manage-action-intake:v1": {
        "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
        "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
    },
    "lotus-idea-to-lotus-report-evidence-pack-intake:v1": {
        "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        "lotus-render",
        "lotus-archive",
    },
}


def validate_downstream_realization_contract_plan(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = DOWNSTREAM_CONTRACT_PLAN_PATH,
) -> list[str]:
    plan = load_downstream_realization_contract_plan(
        repository_root=repository_root,
        contract_path=contract_path,
    )
    return validate_downstream_realization_contract_plan_payload(
        plan,
        repository_root=repository_root,
    )


def validate_downstream_realization_contract_plan_payload(
    plan: DownstreamRealizationContractPlan,
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    if plan.contract_id != "lotus-idea-downstream-realization-contract-plan":
        errors.append(
            "downstream contract plan contract_id must be "
            "`lotus-idea-downstream-realization-contract-plan`"
        )
    if plan.contract_version != "1.0.0":
        errors.append("downstream contract plan contract_version must be 1.0.0")
    if plan.repository != "lotus-idea":
        errors.append("downstream contract plan repository must be lotus-idea")
    if plan.lifecycle_status != "planned":
        errors.append("downstream contract plan lifecycle_status must remain planned")
    if plan.supportability_status != "not_certified":
        errors.append("downstream contract plan supportability_status must remain not_certified")
    if plan.route_existence_proven:
        errors.append("downstream contract plan must not claim route existence proof")
    if plan.downstream_execution_proven:
        errors.append("downstream contract plan must not claim downstream execution proof")
    if plan.supported_feature_promoted:
        errors.append("downstream contract plan must not promote supported features")

    errors.extend(_validate_source_of_truth(plan, repository_root=repository_root))
    errors.extend(_validate_contracts(plan))
    return errors


def _validate_source_of_truth(
    plan: DownstreamRealizationContractPlan,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    required_keys = {
        "readiness_builder",
        "contract_loader",
        "downstream_adapter_port",
        "downstream_adapter_foundation",
        "contract_gate",
        "operations_runbook",
        "rfc_slice_12",
        "rfc_slice_13",
    }
    missing_keys = sorted(required_keys - set(plan.source_of_truth))
    if missing_keys:
        errors.append(
            "downstream contract plan source_of_truth missing keys: " + ", ".join(missing_keys)
        )
    for key, relative_path in sorted(plan.source_of_truth.items()):
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"downstream contract plan source_of_truth.{key} path must stay relative")
            continue
        if not (repository_root / path).exists():
            errors.append(f"downstream contract plan source_of_truth.{key} path missing")
    return errors


def _validate_contracts(plan: DownstreamRealizationContractPlan) -> list[str]:
    errors: list[str] = []
    declared_contracts = {contract.contract_id: contract for contract in plan.contracts}
    missing_contracts = sorted(set(REQUIRED_CONTRACTS) - set(declared_contracts))
    extra_contracts = sorted(set(declared_contracts) - set(REQUIRED_CONTRACTS))
    if missing_contracts:
        errors.append("downstream contract plan missing contracts: " + ", ".join(missing_contracts))
    if extra_contracts:
        errors.append(
            "downstream contract plan contains unsupported contracts: " + ", ".join(extra_contracts)
        )

    for contract_id, owner_repository in sorted(REQUIRED_CONTRACTS.items()):
        contract = declared_contracts.get(contract_id)
        if contract is None:
            continue
        if contract.owner_repository != owner_repository:
            errors.append(f"{contract_id}: owner_repository must be {owner_repository}")
        if contract.source_authority != owner_repository:
            errors.append(f"{contract_id}: source_authority must be {owner_repository}")
        if not contract.target_route.startswith("planned:"):
            errors.append(f"{contract_id}: target_route must remain planned before route proof")
        if contract.route_fit_status != "not_certified":
            errors.append(f"{contract_id}: route_fit_status must remain not_certified")
        if contract.adapter_status != "adapter_foundation_present":
            errors.append(f"{contract_id}: adapter_status must be adapter_foundation_present")
        if not contract.blockers:
            errors.append(f"{contract_id}: blockers are required before certification")

        missing_refs = sorted(REQUIRED_EVIDENCE_REFS[contract_id] - set(contract.evidence_refs))
        if missing_refs:
            errors.append(
                f"{contract_id}: evidence_refs missing required references: "
                + ", ".join(missing_refs)
            )
        if _has_sensitive_or_executable_route_claim(contract.evidence_refs):
            errors.append(
                f"{contract_id}: evidence_refs must not include downstream current routes"
            )
    return errors


def _has_sensitive_or_executable_route_claim(evidence_refs: tuple[str, ...]) -> bool:
    return any(
        ref.startswith(("GET http", "POST http", "PUT http", "PATCH http", "DELETE http"))
        for ref in evidence_refs
    )


def _parse_payload(payload: dict[str, Any]) -> DownstreamRealizationContractPlan:
    return downstream_realization_contract_plan_from_payload(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate lotus-idea downstream realization contract posture."
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=DOWNSTREAM_CONTRACT_PLAN_PATH,
        help="Repository-relative downstream realization contract plan path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_downstream_realization_contract_plan(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Downstream realization contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
