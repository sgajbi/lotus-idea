from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_readiness_preserves_blocker_without_aggregate_provenance() -> None:
    raw_proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=raw_proof,
        durable_repository_proof_ref="durable repository proof artifact",
    )

    assert "durable_repository_not_configured" in snapshot.overall_blockers


def test_implementation_proof_readiness_preserves_blocker_for_stale_proof(
    tmp_path: Path,
) -> None:
    stale_proof = tmp_path / "durable-repository-proof.json"
    stale_proof.write_text(
        json.dumps(
            build_durable_repository_proof_payload(
                generated_at_utc=datetime(2026, 6, 20, 9, 0, tzinfo=UTC),
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
            "--durable-repository-proof",
            str(stale_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "durable_repository_not_configured" in payload["overallBlockers"]


def test_implementation_proof_readiness_preserves_blocker_for_source_revision_mismatch(
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "durable-repository-proof.json"
    raw_proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof_path.write_text(json.dumps(raw_proof), encoding="utf-8")
    bound_proof = bind_aggregate_proof_provenance(
        raw_proof,
        artifact_path=proof_path,
        proof_ref="durable repository proof artifact",
        repository_root=ROOT,
    )
    bound_proof["aggregateProofProvenance"]["sourceRevision"] = "different-source-revision"

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=bound_proof,
        durable_repository_proof_ref="durable repository proof artifact",
    )

    assert "durable_repository_not_configured" in snapshot.overall_blockers
