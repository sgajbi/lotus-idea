from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.disaster_recovery import ValidateRestoredDatabase
from app.domain.disaster_recovery import (
    DisasterRecoveryPolicy,
    RestoredDatabaseSnapshot,
    RestoreDrillRequest,
    RestoreValidationStatus,
)

TABLES = frozenset({"idea_candidate_record", "idea_outbox_event"})
NOW = datetime(2026, 7, 11, 6, 0, tzinfo=UTC)


class StubInspector:
    def __init__(self, snapshot: RestoredDatabaseSnapshot) -> None:
        self.snapshot = snapshot
        self.expected_tables: frozenset[str] | None = None

    def inspect(self, *, expected_tables: frozenset[str]) -> RestoredDatabaseSnapshot:
        self.expected_tables = expected_tables
        return self.snapshot


def test_restore_use_case_proves_bounded_real_restore_evidence() -> None:
    inspector = StubInspector(valid_snapshot())
    use_case = ValidateRestoredDatabase(inspector, policy(), now=lambda: NOW)

    evidence = use_case.execute(valid_request())

    assert inspector.expected_tables == TABLES
    assert evidence.status is RestoreValidationStatus.PASSED
    assert evidence.validation_mode == "real_restore_validation"
    assert evidence.real_restored_backup is True
    assert evidence.synthetic_smoke is False
    assert evidence.actual_rpo_seconds == 300
    assert evidence.actual_rto_seconds == 900
    assert evidence.failed_checks == ()


def test_restore_use_case_reports_every_independent_failure_without_short_circuiting() -> None:
    snapshot = replace(
        valid_snapshot(),
        table_row_counts={"idea_candidate_record": 0},
        table_content_sha256={"idea_candidate_record": "a" * 64},
        missing_primary_key_tables=("idea_candidate_record",),
        unvalidated_constraints=("unexpected_constraint",),
        invalid_indexes=("invalid_index",),
        referential_violation_counts={"candidate_outbox": 1},
        semantic_violation_counts={"outbox_lease_state": 2},
    )
    request = replace(
        valid_request(),
        backup_created_at_utc=NOW - timedelta(hours=3),
        recovery_point_utc=NOW - timedelta(hours=2),
        incident_cutoff_utc=NOW - timedelta(hours=1),
        restore_started_at_utc=NOW - timedelta(hours=1),
    )

    evidence = ValidateRestoredDatabase(StubInspector(snapshot), policy(), now=lambda: NOW).execute(
        request
    )

    assert evidence.status is RestoreValidationStatus.FAILED
    assert set(evidence.failed_checks) == {
        "owned_table_inventory",
        "representative_linked_state",
        "primary_keys",
        "validated_constraints",
        "valid_ready_indexes",
        "referential_integrity",
        "workflow_state_integrity",
        "rpo",
        "rto",
    }


def test_restore_policy_allows_only_declared_legacy_unvalidated_constraint() -> None:
    snapshot = replace(
        valid_snapshot(),
        unvalidated_constraints=("ck_idea_candidate_record_state_policy_v1",),
    )
    configured_policy = replace(
        policy(),
        allowed_unvalidated_constraints=frozenset({"ck_idea_candidate_record_state_policy_v1"}),
    )

    evidence = ValidateRestoredDatabase(
        StubInspector(snapshot), configured_policy, now=lambda: NOW
    ).execute(valid_request())

    assert evidence.status is RestoreValidationStatus.PASSED


def test_restore_use_case_rejects_readiness_time_before_restore_started() -> None:
    use_case = ValidateRestoredDatabase(
        StubInspector(valid_snapshot()),
        policy(),
        now=lambda: NOW - timedelta(minutes=16),
    )

    with pytest.raises(ValueError, match="must not be before restore_started_at_utc"):
        use_case.execute(valid_request())


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"backup_identifier": "postgresql://secret"}, "source-safe identifier"),
        ({"migration_bundle_sha256": "not-a-hash"}, "lowercase SHA-256"),
        (
            {"backup_created_at_utc": datetime(2026, 7, 11, 1, 0)},
            "timezone-aware UTC",
        ),
        (
            {"recovery_point_utc": NOW, "incident_cutoff_utc": NOW - timedelta(minutes=1)},
            "must not be after incident_cutoff_utc",
        ),
    ],
)
def test_restore_request_rejects_unsafe_or_incoherent_metadata(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(valid_request(), **changes)


def valid_request() -> RestoreDrillRequest:
    return RestoreDrillRequest(
        backup_identifier="backup-20260711-001",
        backup_source="ci-disposable-postgres",
        operator_id="github-actions",
        correlation_id="drill-run-123",
        migration_bundle_sha256="f" * 64,
        latest_migration="008_downstream_submission_state_machine",
        backup_created_at_utc=NOW - timedelta(minutes=45),
        incident_cutoff_utc=NOW - timedelta(minutes=20),
        recovery_point_utc=NOW - timedelta(minutes=25),
        restore_started_at_utc=NOW - timedelta(minutes=15),
    )


def valid_snapshot() -> RestoredDatabaseSnapshot:
    return RestoredDatabaseSnapshot(
        database_identity_sha256="d" * 64,
        postgres_version="PostgreSQL 16.4",
        table_row_counts={table: 1 for table in TABLES},
        table_content_sha256={table: "a" * 64 for table in TABLES},
        missing_primary_key_tables=(),
        unvalidated_constraints=(),
        invalid_indexes=(),
        referential_violation_counts={"candidate_outbox": 0},
        semantic_violation_counts={"outbox_lease_state": 0},
    )


def policy() -> DisasterRecoveryPolicy:
    return DisasterRecoveryPolicy(
        rpo_minutes=15,
        rto_minutes=30,
        owned_tables=TABLES,
        allowed_unvalidated_constraints=frozenset(),
        required_non_empty_tables=TABLES,
    )
