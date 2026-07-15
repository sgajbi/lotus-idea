from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from tests.support.core_benchmark_assignment_runtime_evidence import (
    valid_core_benchmark_assignment_runtime_evidence,
)


def test_generate_implementation_proof_readiness_uses_explicit_core_benchmark_assignment_live_proof(
    tmp_path: Path,
) -> None:
    core_proof = tmp_path / "core-benchmark-assignment-live-proof.json"
    core_proof.write_text(
        json.dumps(
            valid_core_benchmark_assignment_runtime_evidence(
                evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--core-benchmark-assignment-live-proof",
            str(core_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert (
        "opportunity_archetype_benchmark_assignment_source_ref_missing"
        not in (archetypes["blockers"])
    )
    assert "opportunity_archetype_live_performance_source_proof_missing" in (archetypes["blockers"])
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Core benchmark assignment live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
