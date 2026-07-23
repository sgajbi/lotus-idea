from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from app.application.runtime_trust_telemetry import build_runtime_trust_telemetry_snapshot
from app.domain import InMemoryIdeaRepository
from scripts.runtime_trust_telemetry import generate_preview, generate_snapshot
from scripts.runtime_trust_telemetry.generate_snapshot import (
    validate_runtime_trust_telemetry_snapshot_payload,
)


OBSERVED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_runtime_trust_telemetry_snapshot_payload_passes_script_contract_gate() -> None:
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()

    assert validate_runtime_trust_telemetry_snapshot_payload(snapshot) == []


def test_runtime_trust_telemetry_snapshot_cli_can_exercise_source_safe_candidate(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime" / "idea-candidate.telemetry.v1.json"

    result = generate_snapshot.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-safe-local-exercise",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["freshness"]["freshness_state"] == "current"
    assert payload["completeness_status"] == "partial"
    assert payload["data_quality_status"] == "quality_passed"
    assert payload["lineage"]["lineage_materialized"] is True
    assert payload["observed_trust_metadata"]["product_name"] == "IdeaCandidate"
    assert _product(payload, "lotus-idea:IdeaCandidate:v1")["observed_record_count"] == 1
    assert _product(payload, "lotus-idea:IdeaCandidate:v1")["coverage_status"] == "runtime_backed"
    assert "runtime_candidate_snapshot_missing" not in payload["blocking"]["blocked_reason"]
    assert "durable_repository_not_configured" in payload["blocking"]["blocked_reason"]
    assert "platform_mesh_certification_missing" in payload["blocking"]["blocked_reason"]
    assert payload["blocking"]["blocked"] is True
    rendered = json.dumps(payload)
    assert "candidateId" not in rendered
    assert "portfolio_id" not in rendered
    assert "contentHash" not in rendered


def test_runtime_trust_telemetry_preview_cli_can_exercise_source_safe_candidate(
    tmp_path: Path,
) -> None:
    output = tmp_path / "preview.json"

    result = generate_preview.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-safe-local-exercise",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["candidateSnapshotCount"] == 1
    assert payload["currentSourceRefCount"] == 4
    assert payload["runtimeTelemetryBacked"] is False
    assert payload["platformCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "runtime_candidate_snapshot_missing" not in payload["certificationBlockers"]
    assert "durable_repository_not_configured" in payload["certificationBlockers"]


def test_runtime_trust_telemetry_snapshot_gate_blocks_sensitive_fragments() -> None:
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()
    snapshot["observed_trust_metadata"] = {
        "product_name": "IdeaCandidate",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    }

    errors = validate_runtime_trust_telemetry_snapshot_payload(snapshot)

    assert any("undeclared fields: portfolio_id" in error for error in errors)
    assert any("source-unsafe fragment: portfolio_id" in error for error in errors)


def test_runtime_trust_telemetry_snapshot_gate_requires_blocker_issue_refs() -> None:
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()
    del snapshot["blocking"]["blocker_issue_refs"]["runtime_candidate_snapshot_missing"]
    snapshot["product_coverage"][0]["blocker_issue_refs"] = {}

    errors = validate_runtime_trust_telemetry_snapshot_payload(snapshot)

    assert any(
        "runtime snapshot blocking.blocker_issue_refs missing blockers: "
        "runtime_candidate_snapshot_missing" in error
        for error in errors
    )
    assert any(
        "runtime snapshot product_coverage[0].blocker_issue_refs missing blockers" in error
        for error in errors
    )


def test_runtime_trust_telemetry_snapshot_gate_rejects_unmapped_blockers() -> None:
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        generated_at_utc=OBSERVED_AT,
    ).to_dict()
    snapshot["product_coverage"][0]["certification_blockers"].append(
        "new_unmapped_certification_blocker"
    )
    snapshot["product_coverage"][0]["blocker_issue_refs"]["new_unmapped_certification_blocker"] = [
        "sgajbi/lotus-idea#692"
    ]

    errors = validate_runtime_trust_telemetry_snapshot_payload(snapshot)

    assert any(
        "runtime snapshot product_coverage[0].blocker_issue_refs."
        "new_unmapped_certification_blocker is not in the canonical blocker issue-ref map" in error
        for error in errors
    )


def _product(payload: dict[str, object], product_id: str) -> dict[str, object]:
    coverage = payload["product_coverage"]
    assert isinstance(coverage, list)
    return next(
        product
        for product in coverage
        if isinstance(product, dict) and product["product_id"] == product_id
    )
