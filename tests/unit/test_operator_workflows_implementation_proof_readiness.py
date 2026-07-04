from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

import scripts.generate_implementation_proof_readiness as proof_report

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.operator_workflows_operations_proof import (
    build_operator_workflows_operations_proof_payload,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_readiness_reports_operator_workflows_operations_capability() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    operator_workflows = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "operator-workflows-operations"
    )
    assert {
        "contracts/observability/lotus-idea-operator-workflows-operations.v1.json",
        "make operator-workflows-ops-contract-gate",
        "make operator-workflows-operations-proof-contract-gate",
    }.issubset(operator_workflows.evidence_refs)
    assert {
        "operator_workflow_dashboard_not_certified",
        "operator_workflow_alerts_not_certified",
        "external_broker_runtime_proof_missing",
    }.issubset(operator_workflows.blockers)


def test_implementation_proof_readiness_uses_operator_workflows_operations_proof_without_product_claim() -> (
    None
):
    proof_ref = "output/operations/operator-workflows-operations-proof.json"
    proof = _bound_aggregate_proof(
        build_operator_workflows_operations_proof_payload(
            generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        operator_workflows_operations_proof=proof,
        operator_workflows_operations_proof_ref=proof_ref,
    )

    assert "operator_workflow_dashboard_not_certified" not in snapshot.overall_blockers
    assert "operator_workflow_alerts_not_certified" not in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" in snapshot.overall_blockers
    assert "downstream_execution_outcome_authority_missing" in snapshot.overall_blockers
    assert "data_mesh_certification_missing" in snapshot.overall_blockers
    assert "gateway_workbench_proof_missing" in snapshot.overall_blockers
    assert "supported_feature_promotion_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    operator_workflows = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "operator-workflows-operations"
    )
    assert "operator_workflow_dashboard_not_certified" not in operator_workflows.blockers
    assert "operator_workflow_alerts_not_certified" not in operator_workflows.blockers
    assert "external_broker_runtime_proof_missing" in operator_workflows.blockers
    assert proof_ref in operator_workflows.evidence_refs


def test_generate_implementation_proof_readiness_uses_explicit_operator_workflows_operations_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def bind_clean_aggregate_proof_provenance(*args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = bind_aggregate_proof_provenance(*args, **kwargs)
        bound["aggregateProofProvenance"]["sourceTreeDirty"] = False
        return bound

    monkeypatch.setattr(
        proof_report,
        "bind_aggregate_proof_provenance",
        bind_clean_aggregate_proof_provenance,
    )
    operator_proof = tmp_path / "operator-workflows-operations-proof.json"
    operator_proof.write_text(
        json.dumps(
            build_operator_workflows_operations_proof_payload(
                generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-26T00:00:00Z",
            "--operator-workflows-operations-proof",
            str(operator_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    operator_workflows = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "operator-workflows-operations"
    )
    assert "operator_workflow_dashboard_not_certified" not in operator_workflows["blockers"]
    assert "operator_workflow_alerts_not_certified" not in operator_workflows["blockers"]
    assert "operator workflows operations proof artifact" in operator_workflows["evidenceRefs"]
    assert "external_broker_runtime_proof_missing" in operator_workflows["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def _bound_aggregate_proof(payload: dict[str, object], proof_ref: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "proof.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        bound = bind_aggregate_proof_provenance(
            payload,
            artifact_path=artifact_path,
            repository_root=ROOT,
            proof_ref=proof_ref,
        )
        bound["aggregateProofProvenance"]["sourceTreeDirty"] = False
        return bound
