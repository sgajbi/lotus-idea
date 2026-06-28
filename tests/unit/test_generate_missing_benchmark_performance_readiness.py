from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.missing_benchmark_performance_readiness_proof import (
    build_missing_benchmark_performance_readiness_proof_payload,
)


def test_generate_readiness_uses_missing_benchmark_performance_readiness_proof(
    tmp_path: Path,
) -> None:
    performance_proof = tmp_path / "missing-benchmark-performance-readiness-proof.json"
    performance_proof.write_text(
        json.dumps(
            build_missing_benchmark_performance_readiness_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_performance_source_attempted=True,
                performance_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-performance",
                    "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
                    "sourceEvidenceCurrent": True,
                    "performanceBenchmarkReadinessSourceRefPresent": True,
                    "benchmarkContextAvailable": False,
                    "benchmarkReadinessDiagnostic": "performance_benchmark_context_missing",
                    "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--missing-benchmark-performance-readiness-proof",
            str(performance_proof),
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
        "opportunity_archetype_performance_benchmark_readiness_source_ref_missing"
        not in archetypes["blockers"]
    )
    assert (
        "opportunity_archetype_missing_benchmark_live_core_source_proof_missing"
        in archetypes["blockers"]
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes["blockers"]
    assert "Missing benchmark Performance readiness proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
