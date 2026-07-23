from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, cast

import pytest

from app.application.demo_readiness_claims import (
    DEMO_READINESS_CLAIM_MATRIX_PATH,
    SUPPORTED_FEATURES_PATH,
    demo_readiness_claim_matrix_from_payload,
    load_demo_readiness_claim_matrix,
    validate_demo_readiness_claim_matrix,
    validate_demo_readiness_claim_matrix_payload,
)


def _payload() -> dict[str, object]:
    payload = json.loads(Path(DEMO_READINESS_CLAIM_MATRIX_PATH).read_text(encoding="utf-8"))
    return cast(dict[str, object], payload)


def _supported_features_payload() -> dict[str, object]:
    payload = json.loads(Path(SUPPORTED_FEATURES_PATH).read_text(encoding="utf-8"))
    return cast(dict[str, object], payload)


def _errors_for_payload(
    payload: dict[str, object],
    *,
    supported_features_payload: dict[str, object] | None = None,
) -> list[str]:
    contract = demo_readiness_claim_matrix_from_payload(payload)
    return validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=(
            supported_features_payload
            if supported_features_payload is not None
            else _supported_features_payload()
        ),
    )


def test_demo_readiness_claim_matrix_current_contract_passes() -> None:
    assert validate_demo_readiness_claim_matrix() == []


def test_demo_readiness_claim_matrix_rejects_non_object_contract_file(tmp_path: Path) -> None:
    contract_path = tmp_path / "claim-matrix.json"
    supported_features_path = tmp_path / "supported-features.json"
    contract_path.write_text("[]", encoding="utf-8")
    supported_features_path.write_text(
        json.dumps(_supported_features_payload()),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="demo readiness claim matrix contract must be a JSON object",
    ):
        validate_demo_readiness_claim_matrix(
            repository_root=tmp_path,
            contract_path=Path("claim-matrix.json"),
            supported_features_path=Path("supported-features.json"),
        )


def test_demo_readiness_claim_matrix_rejects_non_object_supported_features(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "claim-matrix.json"
    supported_features_path = tmp_path / "supported-features.json"
    contract_path.write_text(json.dumps(_payload()), encoding="utf-8")
    supported_features_path.write_text("[]", encoding="utf-8")

    assert validate_demo_readiness_claim_matrix(
        repository_root=tmp_path,
        contract_path=Path("claim-matrix.json"),
        supported_features_path=Path("supported-features.json"),
    ) == ["supported-features registry must be a JSON object"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload.__setitem__("source_of_truth", []),
            "demo readiness source_of_truth must be an object",
        ),
        (
            lambda payload: payload.__setitem__("claim_matrix", {}),
            "demo readiness claim_matrix must be a list",
        ),
        (
            lambda payload: payload.__setitem__("claim_matrix", ["not-an-object"]),
            "demo readiness claim_matrix entries must be objects",
        ),
        (
            lambda payload: payload.__setitem__("do_not_claim", {}),
            "demo readiness do_not_claim must be a list",
        ),
        (
            lambda payload: payload.__setitem__("do_not_claim", ["not-an-object"]),
            "demo readiness do_not_claim entries must be objects",
        ),
        (
            lambda payload: payload.__setitem__("commercial_proof_pack", []),
            "demo readiness commercial_proof_pack must be an object",
        ),
    ],
)
def test_claim_matrix_rejects_malformed_contract_shapes(
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    payload = _payload()
    mutate(payload)

    with pytest.raises(ValueError, match=message):
        demo_readiness_claim_matrix_from_payload(payload)


def test_demo_readiness_claim_matrix_loads_typed_claims() -> None:
    contract = load_demo_readiness_claim_matrix()

    assert contract.contract_id == "lotus-idea-demo-readiness-claim-matrix"
    assert contract.canonical_portfolio_ref == "PB_SG_GLOBAL_BAL_001"
    assert contract.readiness_flags["demo_ready"] is False
    assert contract.commercial_proof_pack.pack_status == "internal_enablement_only"
    assert {claim.claim_category for claim in contract.claim_matrix} >= {
        "implemented_foundation",
        "bounded_internal_walkthrough",
        "blocked_external_proof",
        "prohibited_claim",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "contract_id",
            "unexpected-contract",
            "demo readiness claim matrix contract_id is invalid",
        ),
        (
            "contract_version",
            "2.0.0",
            "demo readiness claim matrix contract_version must be 1.0.0",
        ),
        ("repository", "lotus-core", "demo readiness claim matrix repository must be lotus-idea"),
        ("governing_rfcs", [], "demo readiness claim matrix must be governed by RFC-0002"),
        ("rfc_slices", [], "demo readiness claim matrix must be tied to slice-16"),
        (
            "issue_refs",
            [],
            "demo readiness claim matrix must reference sgajbi/lotus-idea#697",
        ),
        (
            "canonical_portfolio_ref",
            "PB_TEST",
            "demo readiness claim matrix canonical portfolio ref must be governed",
        ),
        (
            "claim_posture",
            "client_demo_ready",
            "demo readiness claim posture must remain bounded and not client-demo-ready",
        ),
    ],
)
def test_claim_matrix_rejects_header_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = _payload()
    payload[field] = value

    assert message in _errors_for_payload(payload)


def test_claim_matrix_rejects_supported_feature_promotion() -> None:
    payload = _payload()
    payload["supported_feature_promoted"] = True

    errors = _errors_for_payload(payload)
    assert "demo readiness claim matrix must keep supported_feature_promoted false" in errors


def test_claim_matrix_treats_non_list_string_fields_as_missing() -> None:
    payload = _payload()
    payload["governing_rfcs"] = "RFC-0002"

    errors = _errors_for_payload(payload)

    assert "demo readiness claim matrix must be governed by RFC-0002" in errors


def test_claim_matrix_rejects_missing_claim_categories() -> None:
    payload = _payload()
    payload["claim_matrix"] = []

    errors = _errors_for_payload(payload)

    assert (
        "demo readiness claim categories missing: blocked_external_proof, "
        "bounded_internal_walkthrough, implemented_foundation, prohibited_claim"
    ) in errors


def test_claim_matrix_rejects_external_distribution() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["external_distribution_allowed"] = True
    payload["claim_matrix"] = claims

    errors = _errors_for_payload(payload)
    assert "idea-governed-foundation: external distribution must remain false" in errors


def test_claim_matrix_rejects_positive_demo_language() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["allowed_language"] = "Lotus Idea is demo-ready for client publication."
    payload["claim_matrix"] = claims

    errors = _errors_for_payload(payload)
    assert any(
        "allowed_language contains unsupported positive claim phrase `is demo-ready`" in error
        for error in errors
    )


def test_claim_matrix_rejects_supported_features_drift() -> None:
    payload = _payload()
    supported_features = _supported_features_payload()
    supported_features["features"] = [{"id": "demo-commercial-proof"}]

    errors = _errors_for_payload(payload, supported_features_payload=supported_features)
    assert "supported-features features[] must remain empty for this claim matrix" in errors


def test_claim_matrix_rejects_supported_features_header_and_shape_drift() -> None:
    payload = _payload()
    supported_features = _supported_features_payload()
    supported_features["repository"] = "lotus-core"
    supported_features["current_posture"] = "promoted"
    supported_features["features"] = {}

    errors = _errors_for_payload(payload, supported_features_payload=supported_features)

    assert "supported-features repository must be lotus-idea" in errors
    assert "supported-features current_posture must remain foundation_only" in errors
    assert "supported-features features must be a list" in errors


def test_claim_matrix_rejects_missing_required_do_not_claim_boundary() -> None:
    payload = _payload()
    boundaries = copy.deepcopy(payload["do_not_claim"])
    assert isinstance(boundaries, list)
    payload["do_not_claim"] = [
        boundary
        for boundary in boundaries
        if cast(dict[str, object], boundary)["boundary_key"] != "ai-governance"
    ]

    errors = _errors_for_payload(payload)
    assert "demo readiness do_not_claim missing boundaries: ai-governance" in errors


def test_claim_matrix_rejects_external_commercial_pack_distribution() -> None:
    payload = _payload()
    commercial_pack = copy.deepcopy(payload["commercial_proof_pack"])
    assert isinstance(commercial_pack, dict)
    commercial_pack["client_safe_distribution_ready"] = True
    payload["commercial_proof_pack"] = commercial_pack

    errors = _errors_for_payload(payload)
    assert "commercial proof pack must not claim client-safe distribution readiness" in errors


def test_claim_matrix_rejects_missing_source_of_truth_and_unsafe_refs() -> None:
    payload = _payload()
    source_of_truth = copy.deepcopy(payload["source_of_truth"])
    assert isinstance(source_of_truth, dict)
    source_of_truth.pop("contract_gate")
    source_of_truth["demo_claims"] = "../outside-repo.md"
    source_of_truth["wiki_demo_readiness"] = "docs/missing-demo-readiness.md"
    payload["source_of_truth"] = source_of_truth

    errors = _errors_for_payload(payload)

    assert "demo readiness source_of_truth missing keys: contract_gate" in errors
    assert (
        "demo readiness source_of_truth.demo_claims ref `../outside-repo.md` "
        "must stay repository-relative"
    ) in errors
    assert (
        "demo readiness source_of_truth.wiki_demo_readiness ref "
        "`docs/missing-demo-readiness.md` is missing"
    ) in errors


def test_claim_matrix_rejects_claim_field_drift_and_bad_refs() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["claim_key"] = ""
    claim["claim_category"] = "unsupported"
    claim["claim_status"] = "unsupported"
    claim["audiences"] = []
    claim["allowed_language"] = ""
    claim["prohibited_language"] = ""
    claim["evidence_refs"] = ["docs/missing-evidence.md", "GET /health"]
    claim["blockers"] = []
    claim["issue_refs"] = ["lotus-idea#697"]
    payload["claim_matrix"] = claims

    errors = _errors_for_payload(payload)

    assert "demo readiness claim_key is required" in errors
    assert ": unsupported claim_category" in errors
    assert ": unsupported claim_status" in errors
    assert ": audiences are required" in errors
    assert ": allowed_language is required" in errors
    assert ": prohibited_language is required" in errors
    assert ": blockers are required before promotion" in errors
    assert (
        "demo readiness .issue_refs ref `lotus-idea#697` must be a sgajbi/<repo>#<number> ref"
    ) in errors
    assert "demo readiness .evidence_refs ref `docs/missing-evidence.md` is missing" in errors


def test_claim_matrix_rejects_missing_claim_evidence_and_issue_refs() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["evidence_refs"] = []
    claim["issue_refs"] = []
    payload["claim_matrix"] = claims

    errors = _errors_for_payload(payload)

    assert "idea-governed-foundation: evidence_refs are required" in errors
    assert "idea-governed-foundation: issue_refs are required" in errors


def test_claim_matrix_rejects_duplicate_claim_key_and_invalid_status_pairing() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    first_claim = cast(dict[str, Any], claims[0])
    second_claim = cast(dict[str, Any], claims[1])
    second_claim["claim_key"] = first_claim["claim_key"]
    first_claim["claim_status"] = "prohibited"
    second_claim["claim_category"] = "blocked_external_proof"
    second_claim["claim_status"] = "bounded_internal_only"
    payload["claim_matrix"] = claims

    errors = _errors_for_payload(payload)

    assert "duplicate demo readiness claim keys: idea-governed-foundation" in errors
    assert (
        "idea-governed-foundation: prohibited status must use prohibited_claim category" in errors
    )
    assert "idea-governed-foundation: blocked external proof must stay blocked" in errors


def test_claim_matrix_rejects_boundary_field_drift_and_bad_issue_ref() -> None:
    payload = _payload()
    boundaries = copy.deepcopy(payload["do_not_claim"])
    assert isinstance(boundaries, list)
    boundary = cast(dict[str, Any], boundaries[0])
    boundary["owner_boundary"] = ""
    boundary["required_before_claim"] = []
    boundary["issue_refs"] = ["sgajbi/lotus-idea#not-a-number"]
    payload["do_not_claim"] = boundaries

    errors = _errors_for_payload(payload)

    assert "source-authority: owner_boundary is required" in errors
    assert "source-authority: required_before_claim is required" in errors
    assert (
        "demo readiness source-authority.issue_refs ref "
        "`sgajbi/lotus-idea#not-a-number` must be a sgajbi/<repo>#<number> ref"
    ) in errors


def test_claim_matrix_rejects_missing_boundary_issue_refs() -> None:
    payload = _payload()
    boundaries = copy.deepcopy(payload["do_not_claim"])
    assert isinstance(boundaries, list)
    boundary = cast(dict[str, Any], boundaries[0])
    boundary["issue_refs"] = []
    payload["do_not_claim"] = boundaries

    errors = _errors_for_payload(payload)

    assert "source-authority: issue_refs are required" in errors


def test_claim_matrix_rejects_commercial_pack_field_drift_and_bad_evidence_ref() -> None:
    payload = _payload()
    commercial_pack = copy.deepcopy(payload["commercial_proof_pack"])
    assert isinstance(commercial_pack, dict)
    commercial_pack["pack_status"] = "externally_distributable"
    commercial_pack["rfp_safe_distribution_ready"] = True
    commercial_pack["approved_internal_uses"] = []
    commercial_pack["required_before_external_use"] = []
    commercial_pack["evidence_refs"] = ["docs/missing-commercial-proof.md"]
    payload["commercial_proof_pack"] = commercial_pack

    errors = _errors_for_payload(payload)

    assert "commercial proof pack must remain internal_enablement_only" in errors
    assert "commercial proof pack must not claim RFP-safe distribution readiness" in errors
    assert "commercial proof pack approved_internal_uses are required" in errors
    assert "commercial proof pack required_before_external_use is required" in errors
    assert (
        "demo readiness commercial_proof_pack.evidence_refs ref "
        "`docs/missing-commercial-proof.md` is missing"
    ) in errors


def test_claim_matrix_rejects_missing_commercial_pack_evidence_and_sensitive_markers() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    commercial_pack = copy.deepcopy(payload["commercial_proof_pack"])
    assert isinstance(claims, list)
    assert isinstance(commercial_pack, dict)
    cast(dict[str, Any], claims[0])["allowed_language"] = "Includes raw_payload evidence."
    commercial_pack["evidence_refs"] = []
    payload["claim_matrix"] = claims
    payload["commercial_proof_pack"] = commercial_pack

    errors = _errors_for_payload(payload)

    assert "commercial proof pack evidence_refs are required" in errors
    assert "demo readiness claim matrix contains forbidden sensitive marker `raw_payload`" in errors
