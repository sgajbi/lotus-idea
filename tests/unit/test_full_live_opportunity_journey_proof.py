from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.full_live_opportunity_journey_proof import (
    FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_SCHEMA_VERSION,
    REQUIRED_FULL_LIVE_JOURNEY_NON_CLAIMS,
    REQUIRED_JOURNEY_CAPABILITY_IDS,
    build_full_live_opportunity_journey_proof_payload,
    full_live_opportunity_journey_proof_is_valid,
)
from app.application.workbench.runtime_execution import (
    build_gateway_workbench_runtime_execution_proof_payload,
)
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[2]


def test_builds_blocked_full_live_opportunity_journey_proof() -> None:
    proof = _valid_full_live_journey_proof()

    assert proof["schemaVersion"] == FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["rfc"] == "RFC-0002"
    assert proof["sliceIds"] == ["RFC-0002/slice-17"]
    assert proof["trackingIssues"] == ["sgajbi/lotus-idea#680", "sgajbi/lotus-idea#699"]
    assert proof["proofType"] == "full_live_opportunity_journey"
    assert proof["evidenceClass"] == EvidenceClass.RUNTIME_EXECUTION.value
    assert proof["aggregateJourneyProofValid"] is True
    assert proof["fullLiveJourneyCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["clientPublicationAuthorized"] is False
    assert proof["proofClosed"] is False
    assert proof["aggregateBlockersCleared"] == ["workbench_gateway_bff_consumption_proof_missing"]
    assert proof["remainingCertificationBlockers"]
    assert tuple(proof["nonProofClaims"]) == REQUIRED_FULL_LIVE_JOURNEY_NON_CLAIMS
    assert [item["capabilityId"] for item in proof["journeyCapabilityCoverage"]] == list(
        REQUIRED_JOURNEY_CAPABILITY_IDS
    )
    assert full_live_opportunity_journey_proof_is_valid(proof) is True


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-workbench"),
        ("generatedAtUtc", "not-a-time"),
        ("rfc", "RFC-0003"),
        ("proofType", "source_contract"),
        ("proofScope", "unsupported"),
        ("evidenceClass", EvidenceClass.SOURCE_CONTRACT.value),
        ("aggregateJourneyProofValid", False),
        ("fullLiveJourneyCertified", True),
        ("canonicalPortfolioId", "OTHER"),
        ("canonicalBenchmarkCode", "OTHER"),
        ("productionIdentityImplemented", True),
        ("clientPublicationAuthorized", True),
        ("suitabilityOrExecutionAuthorized", True),
        ("dataProductCertified", True),
        ("supportedFeaturePromoted", True),
        ("fullDemoReadinessCertified", True),
        ("proofClosed", True),
    ],
)
def test_rejects_claim_inflation_and_wrong_top_level_values(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_full_live_journey_proof()
    proof[field_name] = bad_value

    assert full_live_opportunity_journey_proof_is_valid(proof) is False


def test_rejects_missing_required_journey_capability() -> None:
    proof = build_full_live_opportunity_journey_proof_payload(
        generated_at_utc=datetime(2026, 7, 28, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        implementation_proof_readiness={
            **_valid_readiness_snapshot(),
            "capabilities": _valid_readiness_snapshot()["capabilities"][:-1],
        },
        implementation_proof_readiness_ref="output/implementation-proof/readiness-current.json",
        gateway_workbench_runtime_execution_proof=_valid_gateway_workbench_runtime_proof(),
        gateway_workbench_runtime_execution_proof_ref=(
            "output/workbench/gateway-workbench-runtime-execution-proof.json"
        ),
    )

    assert proof["aggregateJourneyProofValid"] is False
    assert proof["proofChecks"]["requiredJourneyCapabilitiesPresent"] is False
    assert full_live_opportunity_journey_proof_is_valid(proof) is False


def test_rejects_invalid_gateway_workbench_runtime_proof() -> None:
    proof = build_full_live_opportunity_journey_proof_payload(
        generated_at_utc=datetime(2026, 7, 28, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        implementation_proof_readiness=_valid_readiness_snapshot(),
        implementation_proof_readiness_ref="output/implementation-proof/readiness-current.json",
        gateway_workbench_runtime_execution_proof={"schemaVersion": "wrong"},
        gateway_workbench_runtime_execution_proof_ref=(
            "output/workbench/gateway-workbench-runtime-execution-proof.json"
        ),
    )

    assert proof["aggregateJourneyProofValid"] is False
    assert proof["proofChecks"]["gatewayWorkbenchRuntimeEvidenceValid"] is False
    assert full_live_opportunity_journey_proof_is_valid(proof) is False


def test_gate_script_accepts_contract_without_runtime_artifact() -> None:
    module = _load_gate_script()

    assert module.validate_full_live_opportunity_journey_contract(repository_root=ROOT) == []


def test_generator_writes_valid_full_live_journey_proof(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    gateway_path = tmp_path / "gateway-workbench-runtime-proof.json"
    output_path = tmp_path / "full-live-journey-proof.json"
    readiness_path.write_text(json.dumps(_valid_readiness_snapshot()), encoding="utf-8")
    gateway_path.write_text(json.dumps(_valid_gateway_workbench_runtime_proof()), encoding="utf-8")
    module = _load_generator_script()

    result = module.main(
        [
            "--generated-at-utc",
            "2026-07-28T00:00:00Z",
            "--implementation-proof-readiness",
            str(readiness_path),
            "--gateway-workbench-runtime-execution-proof",
            str(gateway_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert full_live_opportunity_journey_proof_is_valid(payload) is True


def _valid_full_live_journey_proof() -> dict[str, Any]:
    return build_full_live_opportunity_journey_proof_payload(
        generated_at_utc=datetime(2026, 7, 28, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        implementation_proof_readiness=_valid_readiness_snapshot(),
        implementation_proof_readiness_ref="output/implementation-proof/readiness-current.json",
        gateway_workbench_runtime_execution_proof=_valid_gateway_workbench_runtime_proof(),
        gateway_workbench_runtime_execution_proof_ref=(
            "output/workbench/gateway-workbench-runtime-execution-proof.json"
        ),
    )


def _valid_readiness_snapshot() -> dict[str, Any]:
    return {
        "repository": "lotus-idea",
        "evaluatedAtUtc": "2026-07-28T00:00:00Z",
        "readinessStatus": "blocked",
        "supportabilityStatus": "not_certified",
        "certificationReady": False,
        "supportedFeaturesPromoted": False,
        "overallBlockers": [
            "live_core_source_proof_missing",
            "workbench_panel_missing",
            "supported_feature_promotion_missing",
        ],
        "capabilities": [
            _capability("source-ingestion", ["live_core_source_proof_missing"]),
            _capability("advisor-review-queue", ["workbench_product_proof_missing"]),
            _capability("workbench-product-proof", ["workbench_panel_missing"]),
            _capability("downstream-realization", ["manage_live_contract_proof_missing"]),
            _capability("outbox-delivery", ["external_broker_runtime_proof_missing"]),
            _capability("data-mesh-certification", ["data_mesh_not_certified"]),
            _capability(
                "runtime-trust-telemetry-preview",
                ["certified_runtime_trust_telemetry_missing"],
            ),
            _capability("supported-feature-promotion", ["no_supported_features_promoted"]),
        ],
    }


def _capability(capability_id: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "capabilityId": capability_id,
        "readinessStatus": "blocked",
        "supportabilityStatus": "not_certified",
        "evidenceRefs": [],
        "blockers": blockers,
        "supportedFeaturePromoted": False,
    }


def _valid_gateway_workbench_runtime_proof() -> dict[str, Any]:
    return build_gateway_workbench_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 7, 28, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        workbench_live_validation_summary=_valid_workbench_summary(),
        workbench_live_validation_summary_ref=(
            "lotus-workbench:output/playwright/live-canonical/live-validation-summary.json"
        ),
        workbench_shot_index_text=_valid_shot_index(),
        workbench_shot_index_ref="lotus-workbench:output/playwright/live-canonical/SHOT-INDEX.md",
        owner_mainline_evidence=json.loads(
            (
                ROOT
                / "contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json"
            ).read_text(encoding="utf-8")
        ),
    )


def _valid_workbench_summary() -> dict[str, Any]:
    return {
        "generatedAt": "2026-07-28T00:00:00Z",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "benchmarkCode": "BMK_PB_GLOBAL_BALANCED_60_40",
        "canonicalContract": {
            "contractId": "canonical-front-office-demo-data-contract",
            "contractVersion": "1.0.0",
            "governedByRfc": "RFC-0076",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "benchmarkCode": "BMK_PB_GLOBAL_BALANCED_60_40",
            "canonicalAsOfDate": "2026-04-10",
        },
        "advisoryJourneyChecks": [
            {
                "key": "opportunities",
                "title": "Opportunities And Ideas",
                "route": (
                    "/recommendations?mode=opportunities&portfolioId=PB_SG_GLOBAL_BAL_001"
                    "&candidateId=idea_high_cash_001"
                ),
                "panel": "advisory.opportunities",
                "owner": "lotus-idea",
                "sourcePosture": "idea-review-queue-through-gateway",
                "state": "ready",
                "gatewayBacked": True,
            }
        ],
        "uiChecks": [
            {
                "description": "Idea candidate review queue",
                "kind": "table",
                "rowCount": 1,
            }
        ],
        "screenshots": [
            {
                "name": "advisory-opportunities-live.png",
                "path": "output/playwright/live-canonical/advisory-opportunities-live.png",
                "route": (
                    "/recommendations?mode=opportunities&portfolioId=PB_SG_GLOBAL_BAL_001"
                    "&candidateId=idea_high_cash_001"
                ),
                "panel": "advisory.opportunities",
                "portfolioId": "PB_SG_GLOBAL_BAL_001",
                "benchmarkCode": "BMK_PB_GLOBAL_BALANCED_60_40",
                "asOfDate": "2026-04-10",
                "state": "demo_ready",
            }
        ],
    }


def _valid_shot_index() -> str:
    return "\n".join(
        (
            "# Canonical front-office live validation shots",
            "- Validation summary: live-validation-summary.json",
            "- advisory-opportunities-live.png",
            "",
        )
    )


def _load_gate_script() -> ModuleType:
    return _load_script("full_live_opportunity_journey_proof_gate")


def _load_generator_script() -> ModuleType:
    return _load_script("generate_full_live_opportunity_journey_proof")


def _load_script(name: str) -> ModuleType:
    script_path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
