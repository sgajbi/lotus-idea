from __future__ import annotations

import json
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report

from tests.unit.downstream_realization.fixtures import valid_manage_intake_runtime_execution


def test_generate_implementation_proof_readiness_uses_manage_intake_runtime_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.proof_provenance.source_tree_dirty", lambda _: False)
    proof = tmp_path / "manage-intake-runtime-execution-proof.json"
    proof.write_text(json.dumps(valid_manage_intake_runtime_execution()), encoding="utf-8")
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-07-22T00:00:00Z",
            "--manage-intake-runtime-execution-proof",
            str(proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    downstream = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "downstream-realization"
    )
    assert "manage_live_contract_proof_missing" not in downstream["blockers"]
    assert "rebalance_execution_authority_remains_lotus_manage" in downstream["blockers"]
    assert (
        "Manage idea action-intake runtime execution proof artifact" in downstream["evidenceRefs"]
    )
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
