from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

from app.application.workbench.contract_proof import (
    build_gateway_workbench_contract_proof_payload,
)
from app.application.workbench.runtime_execution import (
    build_gateway_workbench_runtime_execution_proof_payload,
)
from app.application.implementation_proof_capability_updates import (
    build_capability_readiness,
)
from app.application.implementation_proof_consumption import (
    _apply_gateway_workbench_contract_proof,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.workbench.read_path_source_contract import (
    build_workbench_read_path_source_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository


ROOT = Path(__file__).resolve().parents[2]


def _bound_aggregate_proof(payload: dict[str, object], proof_ref: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "proof.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        bound = bind_aggregate_proof_provenance(
            payload,
            artifact_path=artifact_path,
            proof_ref=proof_ref,
            repository_root=ROOT,
        )
        bound["aggregateProofProvenance"]["sourceTreeDirty"] = False
        return bound


def test_gateway_workbench_contract_proof_application_is_noop_for_other_capability() -> None:
    capability = build_capability_readiness(
        "workbench-product-proof",
        "Workbench product realization",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("gateway_workbench_proof_missing", "workbench_panel_missing"),
    )

    result = _apply_gateway_workbench_contract_proof(
        capability,
        "output/workbench/gateway-workbench-contract-proof.json",
    )

    assert result is capability


def test_readiness_uses_gateway_workbench_contract_proof_without_support_promotion() -> None:
    proof_ref = "output/workbench/gateway-workbench-contract-proof.json"
    proof = _bound_aggregate_proof(
        _valid_gateway_workbench_contract_proof(),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        gateway_workbench_contract_proof=proof,
        gateway_workbench_contract_proof_ref=proof_ref,
    )

    assert "gateway_workbench_proof_missing" in snapshot.overall_blockers
    assert "workbench_product_proof_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "gateway_workbench_discovery_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    source_ingestion = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "source-ingestion"
    )
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    workbench = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "workbench-product-proof"
    )
    assert "gateway_workbench_proof_missing" in source_ingestion.blockers
    assert "gateway_workbench_proof_missing" in outbox_delivery.blockers
    assert "workbench_panel_missing" in workbench.blockers
    assert "output/workbench/gateway-workbench-contract-proof.json" in (
        source_ingestion.evidence_refs
    )
    assert "output/workbench/gateway-workbench-contract-proof.json" in (
        outbox_delivery.evidence_refs
    )
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_readiness_uses_gateway_workbench_runtime_proof_for_bff_consumption_only() -> None:
    proof_ref = "output/workbench/gateway-workbench-runtime-execution-proof.json"
    proof = _bound_aggregate_proof(
        _valid_gateway_workbench_runtime_execution_proof(),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        gateway_workbench_runtime_execution_proof=proof,
        gateway_workbench_runtime_execution_proof_ref=proof_ref,
    )

    workbench = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "workbench-product-proof"
    )
    assert "workbench_gateway_bff_consumption_proof_missing" not in workbench.blockers
    assert "output/workbench/gateway-workbench-runtime-execution-proof.json" in (
        workbench.evidence_refs
    )
    assert "workbench_panel_missing" in workbench.blockers
    assert "browser_accessibility_proof_missing" in workbench.blockers
    assert "canonical_demo_runtime_proof_missing" in workbench.blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_gateway_workbench_contract_proof() -> dict[str, object]:
    read_path_source_contract_proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    return build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_source_contract_proof=read_path_source_contract_proof,
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )


def _valid_gateway_workbench_runtime_execution_proof() -> dict[str, object]:
    return build_gateway_workbench_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_live_validation_summary={
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
                    "path": (
                        "output/playwright/live-canonical/advisory-opportunities-live.png"
                    ),
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
        },
        workbench_live_validation_summary_ref=(
            "lotus-workbench:output/playwright/live-canonical/live-validation-summary.json"
        ),
        workbench_shot_index_text=(
            "# Shots\n- Validation summary: live-validation-summary.json\n"
            "- advisory-opportunities-live.png\n"
        ),
        workbench_shot_index_ref="lotus-workbench:output/playwright/live-canonical/SHOT-INDEX.md",
        owner_mainline_evidence=json.loads(
            (
                ROOT
                / "contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json"
            ).read_text(encoding="utf-8")
        ),
    )
