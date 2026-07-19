from __future__ import annotations

from datetime import UTC, datetime

from app.application.runtime_trust_telemetry import build_runtime_trust_telemetry_snapshot
from app.domain import InMemoryIdeaRepository
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
