from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.mandate_restriction_source_product_proof import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION,
    build_mandate_restriction_source_product_proof_payload,
    mandate_restriction_source_product_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[2]
GENERATED_AT = datetime(2026, 6, 28, 10, 10, tzinfo=UTC)


def test_mandate_restriction_source_product_proof_is_source_safe_and_bounded() -> None:
    payload = build_mandate_restriction_source_product_proof_payload(
        generated_at_utc=GENERATED_AT,
    )

    assert payload["schemaVersion"] == MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["sourceProductId"] == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    assert payload["typedRestrictionDiagnosticContractReady"] is True
    assert payload["requiredRestrictionDiagnostics"] == [
        "mandate_restriction_review_required",
        "product_restriction_review_required",
        "country_restriction_review_required",
        "suitability_policy_actionability_blocked",
    ]
    assert payload["restrictionDiagnosticsOwnedByAdvise"] is True
    assert payload["lotusIdeaDoesNotClearRestrictions"] is True
    assert payload["mandateStateAuthorityGranted"] is False
    assert payload["restrictionClearanceAuthorityGranted"] is False
    assert payload["suitabilityAuthorityGranted"] is False
    assert payload["policyApprovalGranted"] is False
    assert payload["proposalApprovalGranted"] is False
    assert payload["rebalanceAuthorityGranted"] is False
    assert payload["orderAuthorityGranted"] is False
    assert payload["liveAdviseSourceProofCertified"] is False
    assert payload["clientPublicationReady"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_typed_restriction_source_product_missing"
    ]
    assert (
        "opportunity_archetype_live_restriction_source_proof_missing"
        in payload["remainingCertificationBlockers"]
    )
    assert mandate_restriction_source_product_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "evaluationId" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_mandate_restriction_source_product_proof_rejects_generic_source_product() -> None:
    payload = build_mandate_restriction_source_product_proof_payload(
        generated_at_utc=GENERATED_AT,
        source_product_summary={
            "sourceProductId": "lotus-advise:GenericPolicyRecord:v1",
            "requiredRestrictionDiagnostics": ["mandate_restriction_review_required"],
        },
    )

    assert "advise_restriction_source_product_mismatch" in payload["proofBlockers"]
    assert "advise_restriction_required_diagnostics_missing" in payload["proofBlockers"]
    assert mandate_restriction_source_product_proof_is_valid(payload) is False


def test_mandate_restriction_source_product_proof_requires_advise_owned_boundary() -> None:
    payload = build_mandate_restriction_source_product_proof_payload(
        generated_at_utc=GENERATED_AT,
        source_product_summary={
            "restrictionDiagnosticsOwnedByAdvise": False,
            "lotusIdeaDoesNotClearRestrictions": False,
        },
    )

    assert "advise_restriction_diagnostics_not_advise_owned" in payload["proofBlockers"]
    assert "lotus_idea_restriction_authority_boundary_missing" in payload["proofBlockers"]
    assert mandate_restriction_source_product_proof_is_valid(payload) is False


def test_mandate_restriction_source_product_proof_requires_timezone_aware_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_mandate_restriction_source_product_proof_payload(
            generated_at_utc=datetime(2026, 6, 28, 10, 10),
        )


def test_mandate_restriction_source_product_generator_writes_valid_artifact(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "mandate-restriction-source-product-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-28T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["proofFamily"] == "mandate-restriction-source-product"
    assert payload["supportedFeaturePromoted"] is False
    assert mandate_restriction_source_product_proof_is_valid(payload) is True


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_mandate_restriction_source_product_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_mandate_restriction_source_product_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
