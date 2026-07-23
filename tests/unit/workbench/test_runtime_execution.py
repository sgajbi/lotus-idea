from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from app.application.workbench.owner_mainline_evidence import OWNER_MAINLINE_EVIDENCE_CONTRACT_REF
from app.application.workbench.runtime_execution import (
    GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED,
    GATEWAY_WORKBENCH_RUNTIME_EXECUTION_SCHEMA_VERSION,
    REQUIRED_GATEWAY_WORKBENCH_RUNTIME_NON_CLAIMS,
    REMAINING_GATEWAY_WORKBENCH_RUNTIME_CERTIFICATION_BLOCKERS,
    build_gateway_workbench_runtime_execution_proof_payload,
    gateway_workbench_runtime_execution_proof_is_valid,
    validate_gateway_workbench_runtime_execution_proof,
)
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[3]


def test_builds_closed_gateway_workbench_runtime_execution_proof() -> None:
    proof = _valid_gateway_workbench_runtime_execution_proof()

    assert proof["schemaVersion"] == GATEWAY_WORKBENCH_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["rfc"] == "RFC-0002"
    assert proof["sliceIds"] == ["RFC-0002/slice-11", "RFC-0002/slice-17"]
    assert proof["proofType"] == "gateway_workbench_runtime_execution"
    assert proof["evidenceClass"] == EvidenceClass.RUNTIME_EXECUTION.value
    assert proof["runtimeExecutionProofValid"] is True
    assert proof["gatewayBffConsumptionObserved"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_GATEWAY_WORKBENCH_RUNTIME_CERTIFICATION_BLOCKERS
    )
    assert tuple(proof["nonProofClaims"]) == REQUIRED_GATEWAY_WORKBENCH_RUNTIME_NON_CLAIMS
    assert proof["productionIdentityImplemented"] is False
    assert proof["browserAccessibilityCertified"] is False
    assert proof["canonicalDemoRuntimeCertified"] is False
    assert proof["dataProductCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["clientPublicationAuthorized"] is False
    assert proof["suitabilityOrExecutionAuthorized"] is False
    assert proof["proofClosed"] is False
    assert gateway_workbench_runtime_execution_proof_is_valid(proof) is True


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
        ("runtimeExecutionProofValid", False),
        ("canonicalPortfolioId", "OTHER"),
        ("canonicalBenchmarkCode", "OTHER"),
        ("gatewayBffConsumptionObserved", False),
        ("productionIdentityImplemented", True),
        ("browserAccessibilityCertified", True),
        ("canonicalDemoRuntimeCertified", True),
        ("dataProductCertified", True),
        ("supportedFeaturePromoted", True),
        ("clientPublicationAuthorized", True),
        ("suitabilityOrExecutionAuthorized", True),
        ("proofClosed", True),
    ],
)
def test_rejects_claim_inflation_and_wrong_top_level_values(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_gateway_workbench_runtime_execution_proof()
    proof[field_name] = bad_value

    assert gateway_workbench_runtime_execution_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "sliceIds",
        "runtimeEvidenceRefs",
        "surfaceCoverage",
        "aggregateBlockersCleared",
        "remainingCertificationBlockers",
        "nonProofClaims",
    ],
)
def test_rejects_missing_or_changed_contract_arrays(field_name: str) -> None:
    proof = _valid_gateway_workbench_runtime_execution_proof()
    proof[field_name] = []

    assert gateway_workbench_runtime_execution_proof_is_valid(proof) is False


def test_rejects_unknown_top_level_fields() -> None:
    proof = _valid_gateway_workbench_runtime_execution_proof()
    proof["supported"] = True

    errors = validate_gateway_workbench_runtime_execution_proof(proof)

    assert "unknown top-level gateway-workbench runtime fields: ['supported']" in errors


def test_rejects_summary_without_gateway_backed_idea_journey() -> None:
    proof = build_gateway_workbench_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_live_validation_summary={
            **_valid_workbench_summary(),
            "advisoryJourneyChecks": [],
        },
        workbench_live_validation_summary_ref=(
            "lotus-workbench:output/playwright/live-canonical/live-validation-summary.json"
        ),
        workbench_shot_index_text=_valid_shot_index(),
        workbench_shot_index_ref="lotus-workbench:output/playwright/live-canonical/SHOT-INDEX.md",
        owner_mainline_evidence=_owner_mainline_evidence(),
    )

    assert proof["runtimeExecutionProofValid"] is False
    assert proof["proofChecks"]["ideaJourneyThroughGatewayObserved"] is False
    assert gateway_workbench_runtime_execution_proof_is_valid(proof) is False


def test_gate_script_accepts_contract_without_runtime_artifact() -> None:
    module = _load_gate_script()

    assert module.validate_gateway_workbench_runtime_execution_contract(
        repository_root=ROOT,
        artifact_path=None,
    ) == []


def test_gate_script_rejects_invalid_runtime_artifact(tmp_path: Path) -> None:
    module = _load_gate_script()
    path = tmp_path / "proof.json"
    path.write_text(json.dumps({"schemaVersion": "wrong"}), encoding="utf-8")

    errors = module.validate_gateway_workbench_runtime_execution_contract(
        repository_root=ROOT,
        artifact_path=path,
    )

    assert any("schemaVersion" in error for error in errors)


def test_generator_writes_valid_runtime_proof(tmp_path: Path) -> None:
    workbench_root = _materialize_workbench_runtime_evidence(tmp_path)
    module = _load_generator_script()
    output = tmp_path / "gateway-workbench-runtime-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--workbench-root",
            str(workbench_root),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert gateway_workbench_runtime_execution_proof_is_valid(payload) is True


def _valid_gateway_workbench_runtime_execution_proof() -> dict[str, Any]:
    return build_gateway_workbench_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_live_validation_summary=_valid_workbench_summary(),
        workbench_live_validation_summary_ref=(
            "lotus-workbench:output/playwright/live-canonical/live-validation-summary.json"
        ),
        workbench_shot_index_text=_valid_shot_index(),
        workbench_shot_index_ref="lotus-workbench:output/playwright/live-canonical/SHOT-INDEX.md",
        owner_mainline_evidence=_owner_mainline_evidence(),
    )


def _valid_workbench_summary() -> dict[str, Any]:
    return {
        "generatedAt": "2026-06-21T10:10:00Z",
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


def _owner_mainline_evidence() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / OWNER_MAINLINE_EVIDENCE_CONTRACT_REF).read_text(encoding="utf-8")),
    )


def _materialize_workbench_runtime_evidence(tmp_path: Path) -> Path:
    workbench_root = tmp_path / "lotus-workbench"
    evidence_dir = workbench_root / "output" / "playwright" / "live-canonical"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "live-validation-summary.json").write_text(
        json.dumps(_valid_workbench_summary()),
        encoding="utf-8",
    )
    (evidence_dir / "SHOT-INDEX.md").write_text(_valid_shot_index(), encoding="utf-8")
    return workbench_root


def _load_gate_script() -> ModuleType:
    return _load_script("runtime_execution_proof_gate")


def _load_generator_script() -> ModuleType:
    return _load_script("generate_runtime_execution_proof")


def _load_script(name: str) -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
