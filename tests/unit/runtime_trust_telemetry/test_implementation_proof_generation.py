from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.runtime_trust_telemetry.test_execution_contract import (
    build_runtime_trust_telemetry_test_execution_payload,
)


def test_explicit_test_execution_adds_evidence_without_clearing_runtime_blockers(
    tmp_path: Path,
) -> None:
    telemetry_evidence = tmp_path / "runtime-trust-telemetry-test-execution.json"
    telemetry_evidence.write_text(
        json.dumps(
            build_runtime_trust_telemetry_test_execution_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[3],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--runtime-trust-telemetry-test-execution",
            str(telemetry_evidence),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    expected_blockers = {
        "runtime_candidate_snapshot_missing",
        "certified_runtime_trust_telemetry_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "runtime_trust_telemetry_product_coverage_incomplete",
        "platform_mesh_certification_missing",
    }
    assert expected_blockers <= set(payload["overallBlockers"])
    capabilities = {
        capability["capabilityId"]: capability for capability in payload["capabilities"]
    }
    runtime_telemetry = capabilities["runtime-trust-telemetry-preview"]
    data_mesh = capabilities["data-mesh-certification"]
    assert "runtime_candidate_snapshot_missing" in runtime_telemetry["blockers"]
    assert "certified_runtime_trust_telemetry_missing" in runtime_telemetry["blockers"]
    assert "runtime_trust_telemetry_product_coverage_incomplete" in data_mesh["blockers"]
    evidence_ref = "runtime trust telemetry test execution artifact"
    assert evidence_ref in runtime_telemetry["evidenceRefs"]
    assert evidence_ref in data_mesh["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
