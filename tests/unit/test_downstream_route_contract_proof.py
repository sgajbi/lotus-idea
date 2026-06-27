from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

import pytest

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

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_advise_route_proof(tmp_path: Path) -> None:
    proof = _valid_advise_route_proof(tmp_path)

    assert proof["schemaVersion"] == DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "lotus_advise_idea_proposal_intake_route_contract"
    assert proof["proofScope"] == "source_safe_advise_proposal_route_only"
    assert proof["adviseProposalRouteProofValid"] is True
    assert proof["targetRoute"] == ADVISE_PROPOSAL_ROUTE
    assert tuple(proof["aggregateBlockersCleared"]) == ADVISE_ROUTE_BLOCKERS_CLEARED
    assert tuple(proof["remainingCertificationBlockers"]) == (REMAINING_ADVISE_ROUTE_BLOCKERS)
    assert proof["downstreamExecutionProven"] is False
    assert proof["suitabilityAuthorityGranted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert advise_proposal_route_proof_is_valid(proof) is True
    _assert_source_safe(proof)


def test_builds_source_safe_manage_route_proof(tmp_path: Path) -> None:
    proof = _valid_manage_route_proof(tmp_path)

    assert proof["schemaVersion"] == DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "lotus_manage_idea_action_intake_route_contract"
    assert proof["proofScope"] == "source_safe_manage_action_route_only"
    assert proof["manageActionRouteProofValid"] is True
    assert proof["targetRoute"] == MANAGE_ACTION_ROUTE
    assert tuple(proof["aggregateBlockersCleared"]) == MANAGE_ROUTE_BLOCKERS_CLEARED
    assert tuple(proof["remainingCertificationBlockers"]) == (REMAINING_MANAGE_ROUTE_BLOCKERS)
    assert proof["downstreamExecutionProven"] is False
    assert proof["rebalanceExecutionAuthorityGranted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert manage_action_route_proof_is_valid(proof) is True
    _assert_source_safe(proof)


def test_route_proofs_fail_closed_when_sibling_evidence_is_missing(tmp_path: Path) -> None:
    advise_proof = build_advise_proposal_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        advise_root=tmp_path / "missing-advise",
    )
    manage_proof = build_manage_action_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        manage_root=tmp_path / "missing-manage",
    )

    assert advise_proof["adviseProposalRouteProofValid"] is False
    assert manage_proof["manageActionRouteProofValid"] is False
    assert advise_proposal_route_proof_is_valid(advise_proof) is False
    assert manage_action_route_proof_is_valid(manage_proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value", "valid"),
    [
        ("schemaVersion", "wrong", advise_proposal_route_proof_is_valid),
        ("repository", "lotus-advise", advise_proposal_route_proof_is_valid),
        ("proofType", "wrong", advise_proposal_route_proof_is_valid),
        ("proofScope", "execution", advise_proposal_route_proof_is_valid),
        ("adviseProposalRouteProofValid", False, advise_proposal_route_proof_is_valid),
        ("targetRoute", "POST /advisory/proposals", advise_proposal_route_proof_is_valid),
        ("downstreamExecutionProven", True, advise_proposal_route_proof_is_valid),
        ("suitabilityAuthorityGranted", True, advise_proposal_route_proof_is_valid),
        ("clientPublicationAuthorityGranted", True, advise_proposal_route_proof_is_valid),
        ("supportedFeaturePromoted", True, advise_proposal_route_proof_is_valid),
        ("proofClosed", True, advise_proposal_route_proof_is_valid),
        ("generatedAtUtc", "not-a-date", advise_proposal_route_proof_is_valid),
    ],
)
def test_rejects_advise_route_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    valid: object,
    tmp_path: Path,
) -> None:
    proof = _valid_advise_route_proof(tmp_path)
    proof[field_name] = bad_value

    assert valid(proof) is False  # type: ignore[operator]


def test_advise_route_proof_cli_allows_missing_sibling_evidence_for_default_readiness(
    tmp_path: Path,
) -> None:
    module = _load_script("generate_advise_proposal_route_proof")
    output_path = tmp_path / "proof" / "advise-route-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00Z",
            "--advise-root",
            str(tmp_path / "missing-lotus-advise"),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["adviseProposalRouteProofValid"] is False
    assert advise_proposal_route_proof_is_valid(proof) is False


def test_manage_route_proof_cli_allows_missing_sibling_evidence_for_default_readiness(
    tmp_path: Path,
) -> None:
    module = _load_script("generate_manage_action_route_proof")
    output_path = tmp_path / "proof" / "manage-route-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00Z",
            "--manage-root",
            str(tmp_path / "missing-lotus-manage"),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["manageActionRouteProofValid"] is False
    assert manage_action_route_proof_is_valid(proof) is False


def test_downstream_route_contract_proof_gate_scans_tuple_content() -> None:
    module = _load_script("downstream_route_contract_proof_gate")
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def _valid_advise_route_proof(tmp_path: Path) -> dict[str, Any]:
    return build_advise_proposal_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        advise_root=_write_downstream_fixture(
            tmp_path,
            repository="lotus-advise",
            profile=ADVISE_PROPOSAL_ROUTE_PROFILE,
            contract_payload=_advise_contract_payload(),
        ),
    )


def _valid_manage_route_proof(tmp_path: Path) -> dict[str, Any]:
    return build_manage_action_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        manage_root=_write_downstream_fixture(
            tmp_path,
            repository="lotus-manage",
            profile=MANAGE_ACTION_ROUTE_PROFILE,
            contract_payload=_manage_contract_payload(),
        ),
    )


def _write_downstream_fixture(
    tmp_path: Path,
    *,
    repository: str,
    profile: object,
    contract_payload: dict[str, object],
) -> Path:
    root = tmp_path / repository
    evidence_refs = tuple(getattr(profile, "evidence_refs"))
    for ref in evidence_refs:
        if not ref.startswith(f"../{repository}/"):
            continue
        path = root / ref.removeprefix(f"../{repository}/")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(json.dumps(contract_payload), encoding="utf-8")
        else:
            path.write_text("# source-safe fixture\n", encoding="utf-8")
    return root


def _advise_contract_payload() -> dict[str, object]:
    return {
        "repository": "lotus-advise",
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": "lotus-idea:IdeaCandidate:v1",
        "owned_product": "lotus-advise:AdvisoryProposalLifecycleRecord:v1",
        "source_authority": "lotus-advise",
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "downstream_execution_proven": False,
        "supported_feature_promoted": False,
        "target_route": ADVISE_PROPOSAL_ROUTE,
        "non_proof_boundaries": [
            "Proves only a live route foundation for source-safe proposal intake.",
            "Does not grant suitability or client-communication authority.",
            "Does not create orders, execution instructions, fills, or settlement records.",
            "Does not promote a supported feature in lotus-advise or lotus-idea.",
        ],
        "certification_blockers": list(REMAINING_ADVISE_ROUTE_BLOCKERS),
    }


def _manage_contract_payload() -> dict[str, object]:
    return {
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
            "Proves only a live route foundation for source-safe action intake.",
            "Does not grant suitability or client-communication authority.",
            "Does not create orders, execution instructions, fills, or settlement records.",
            "Does not promote a supported feature in lotus-manage or lotus-idea.",
        ],
        "certification_blockers": list(REMAINING_MANAGE_ROUTE_BLOCKERS),
    }


def _assert_source_safe(payload: Mapping[str, object]) -> None:
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def _load_script(module_name: str) -> ModuleType:
    script_path = ROOT / "scripts" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
