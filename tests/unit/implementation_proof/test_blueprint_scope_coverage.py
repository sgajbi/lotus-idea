from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.application.blueprint_scope_coverage import (
    BLUEPRINT_COVERAGE_CONTRACT_PATH,
    BLUEPRINT_PATH,
    SUPPORTED_FEATURE_POSTURE,
    blueprint_scope_coverage_errors,
)

ROOT = Path(__file__).resolve().parents[3]


def test_blueprint_scope_coverage_contract_maps_current_blueprint_scope() -> None:
    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=_contract(),
    )

    assert errors == []


def test_blueprint_scope_coverage_rejects_missing_owned_capability() -> None:
    contract = _contract()
    removed = contract["ownedCapabilities"].pop(0)["capability"]

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert f"ownedCapabilities: missing blueprint item `{removed}`" in errors


def test_blueprint_scope_coverage_rejects_stale_target_family() -> None:
    contract = _contract()
    contract["targetOpportunityFamilies"].append(
        {
            "family": "unsupported novelty product idea",
            "status": "planned_not_supported",
            "sliceIds": ["RFC-0002/slice-20"],
            "issues": [
                {
                    "repository": "sgajbi/lotus-idea",
                    "number": 701,
                    "url": "https://github.com/sgajbi/lotus-idea/issues/701",
                }
            ],
            "evidenceRefs": ["docs/LOTUS_IDEA_BLUEPRINT.md"],
            "supportedFeaturePosture": SUPPORTED_FEATURE_POSTURE,
        }
    )

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert (
        "targetOpportunityFamilies: stale item `unsupported novelty product idea` "
        "is not in the blueprint"
    ) in errors


def test_blueprint_scope_coverage_rejects_supported_claim_promotion() -> None:
    contract = _contract()
    capability = contract["ownedCapabilities"][0]["capability"]
    contract["ownedCapabilities"][0]["supportedFeaturePosture"] = "supported"

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert (
        f"ownedCapabilities: `{capability}` must keep supportedFeaturePosture "
        f"`{SUPPORTED_FEATURE_POSTURE}`"
    ) in errors


def test_blueprint_scope_coverage_rejects_malformed_issue_reference() -> None:
    contract = _contract()
    capability = contract["ownedCapabilities"][0]["capability"]
    contract["ownedCapabilities"][0]["issues"][0]["url"] = (
        "https://github.com/sgajbi/lotus-idea/issues/999"
    )

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert any(
        error.startswith(f"ownedCapabilities: `{capability}` has malformed GitHub issue reference")
        for error in errors
    )


def _blueprint() -> str:
    return (ROOT / BLUEPRINT_PATH).read_text(encoding="utf-8")


def _contract() -> dict[str, Any]:
    payload = json.loads((ROOT / BLUEPRINT_COVERAGE_CONTRACT_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return copy.deepcopy(payload)
