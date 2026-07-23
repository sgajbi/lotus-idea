from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

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


def test_demo_readiness_claim_matrix_current_contract_passes() -> None:
    assert validate_demo_readiness_claim_matrix() == []


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


def test_claim_matrix_rejects_supported_feature_promotion() -> None:
    payload = _payload()
    payload["supported_feature_promoted"] = True
    contract = demo_readiness_claim_matrix_from_payload(payload)

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=_supported_features_payload(),
    )

    assert "demo readiness claim matrix must keep supported_feature_promoted false" in errors


def test_claim_matrix_rejects_external_distribution() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["external_distribution_allowed"] = True
    payload["claim_matrix"] = claims
    contract = demo_readiness_claim_matrix_from_payload(payload)

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=_supported_features_payload(),
    )

    assert "idea-governed-foundation: external distribution must remain false" in errors


def test_claim_matrix_rejects_positive_demo_language() -> None:
    payload = _payload()
    claims = copy.deepcopy(payload["claim_matrix"])
    assert isinstance(claims, list)
    claim = cast(dict[str, Any], claims[0])
    claim["allowed_language"] = "Lotus Idea is demo-ready for client publication."
    payload["claim_matrix"] = claims
    contract = demo_readiness_claim_matrix_from_payload(payload)

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=_supported_features_payload(),
    )

    assert any(
        "allowed_language contains unsupported positive claim phrase `is demo-ready`" in error
        for error in errors
    )


def test_claim_matrix_rejects_supported_features_drift() -> None:
    payload = _payload()
    contract = demo_readiness_claim_matrix_from_payload(payload)
    supported_features = _supported_features_payload()
    supported_features["features"] = [{"id": "demo-commercial-proof"}]

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=supported_features,
    )

    assert "supported-features features[] must remain empty for this claim matrix" in errors


def test_claim_matrix_rejects_missing_required_do_not_claim_boundary() -> None:
    payload = _payload()
    boundaries = copy.deepcopy(payload["do_not_claim"])
    assert isinstance(boundaries, list)
    payload["do_not_claim"] = [
        boundary
        for boundary in boundaries
        if cast(dict[str, object], boundary)["boundary_key"] != "ai-governance"
    ]
    contract = demo_readiness_claim_matrix_from_payload(payload)

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=_supported_features_payload(),
    )

    assert "demo readiness do_not_claim missing boundaries: ai-governance" in errors


def test_claim_matrix_rejects_external_commercial_pack_distribution() -> None:
    payload = _payload()
    commercial_pack = copy.deepcopy(payload["commercial_proof_pack"])
    assert isinstance(commercial_pack, dict)
    commercial_pack["client_safe_distribution_ready"] = True
    payload["commercial_proof_pack"] = commercial_pack
    contract = demo_readiness_claim_matrix_from_payload(payload)

    errors = validate_demo_readiness_claim_matrix_payload(
        contract,
        supported_features_payload=_supported_features_payload(),
    )

    assert "commercial proof pack must not claim client-safe distribution readiness" in errors
