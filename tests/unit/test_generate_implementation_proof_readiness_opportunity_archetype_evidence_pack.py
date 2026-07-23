from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report
from app.application.opportunity_archetype_evidence_pack import (
    build_canonical_opportunity_archetype_evidence_pack,
)
from tests.support.proof_provenance import bind_clean_aggregate_proof_provenance

ROOT = Path(__file__).resolve().parents[2]


def test_generate_implementation_proof_readiness_consumes_archetype_evidence_pack(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        proof_report,
        "bind_aggregate_proof_provenance",
        bind_clean_aggregate_proof_provenance,
    )
    pack_path = tmp_path / "canonical-archetype-evidence-pack.json"
    pack_path.write_text(
        json.dumps(
            build_canonical_opportunity_archetype_evidence_pack(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--opportunity-archetype-evidence-pack",
            str(pack_path),
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
    assert "canonical opportunity archetype evidence-pack artifact" in (archetypes["evidenceRefs"])
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
