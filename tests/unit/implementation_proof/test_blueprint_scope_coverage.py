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


def test_blueprint_scope_coverage_rejects_header_drift() -> None:
    contract = _contract()
    contract["schemaVersion"] = "stale"

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert any("`schemaVersion` must be" in error for error in errors)


def test_blueprint_scope_coverage_rejects_malformed_entry_group() -> None:
    contract = _contract()
    contract["ownedCapabilities"] = {"capability": "not-a-list"}

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert f"{BLUEPRINT_COVERAGE_CONTRACT_PATH}: `ownedCapabilities` must be a list" in errors


def test_blueprint_scope_coverage_rejects_entry_field_drift() -> None:
    contract = _contract()
    capability = contract["ownedCapabilities"][0]["capability"]
    contract["ownedCapabilities"][0]["sliceIds"] = "RFC-0002/slice-18"
    contract["ownedCapabilities"][0]["issues"] = "https://github.com/sgajbi/lotus-idea/issues/701"
    contract["ownedCapabilities"][0]["evidenceRefs"] = []
    contract["ownedCapabilities"][0]["status"] = "supported"

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=_blueprint(),
        contract=contract,
    )

    assert f"ownedCapabilities: `{capability}` must name at least one RFC-0002 slice" in errors
    assert f"ownedCapabilities: `{capability}` must name at least one GitHub issue" in errors
    assert f"ownedCapabilities: `{capability}` must name at least one evidence reference" in errors
    assert f"ownedCapabilities: `{capability}` has unsupported status `supported`" in errors


def test_blueprint_scope_coverage_handles_minimal_current_blueprint_sections() -> None:
    blueprint = "\n".join(
        (
            "## Owned Capabilities",
            "",
            "1. owned capability.",
            "",
            "## Non-Owned Capabilities",
            "",
            "1. non-owned boundary;",
            "",
            "## Target Opportunity Families",
            "",
            "1. final family",
        )
    )
    contract = {
        "schemaVersion": "lotus-idea.rfc0002.blueprint-scope-coverage.v1",
        "repository": "lotus-idea",
        "rfc": "RFC-0002",
        "trackingIssue": "https://github.com/sgajbi/lotus-idea/issues/701",
        "blueprintSource": "docs/LOTUS_IDEA_BLUEPRINT.md",
        "supportedFeaturePosture": SUPPORTED_FEATURE_POSTURE,
        "ownedCapabilities": [_entry("capability", "owned capability")],
        "nonOwnedAuthorityBoundaries": [_entry("boundary", "non-owned boundary")],
        "targetOpportunityFamilies": [_entry("family", "final family")],
    }

    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=blueprint,
        contract=contract,
    )

    assert errors == []


def test_blueprint_scope_coverage_rejects_missing_blueprint_sections_as_stale_contract() -> None:
    errors = blueprint_scope_coverage_errors(
        blueprint_markdown="# No governed blueprint sections\n",
        contract=_contract(),
    )

    assert any(error.startswith("ownedCapabilities: stale item") for error in errors)


def _blueprint() -> str:
    return (ROOT / BLUEPRINT_PATH).read_text(encoding="utf-8")


def _contract() -> dict[str, Any]:
    payload = json.loads((ROOT / BLUEPRINT_COVERAGE_CONTRACT_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return copy.deepcopy(payload)


def _entry(item_key: str, item: str) -> dict[str, Any]:
    return {
        item_key: item,
        "status": "planned_not_supported",
        "sliceIds": ["RFC-0002/slice-18"],
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
