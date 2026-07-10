from __future__ import annotations

from typing import Any

import pytest

from app.infrastructure.postgres_disaster_recovery import (
    REFERENTIAL_CHECKS,
    SEMANTIC_CHECKS,
    PostgresRestoredDatabaseInspector,
)


class _InspectorCursor:
    def __init__(self, tables: frozenset[str]) -> None:
        self.tables = tables
        self.executed: list[str] = []
        self._one: tuple[Any, ...] = (0,)
        self._many: list[tuple[Any, ...]] = []

    def __enter__(self) -> _InspectorCursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: Any, _params: object = None) -> None:
        rendered = query.as_string(None) if hasattr(query, "as_string") else str(query)
        normalized = " ".join(rendered.split())
        self.executed.append(normalized)
        self._one = (0,)
        self._many = []

        if "FROM pg_catalog.pg_tables" in normalized:
            self._many = [(table,) for table in sorted(self.tables)]
        elif "string_agg(row_digest" in normalized:
            self._one = (2, "a" * 64)
        elif "SELECT current_database()" in normalized:
            self._one = ("restored", "inspector", "127.0.0.1", "5432")
        elif normalized == "SELECT version()":
            self._one = ("PostgreSQL 18 test",)
        elif "FROM unnest(" in normalized:
            self._many = [("idea_missing_primary_key",)]
        elif "NOT constraint_record.convalidated" in normalized:
            self._many = [("candidate_state_pending_validation",)]
        elif "NOT index_state.indisvalid" in normalized:
            self._many = [("idea_invalid_index",)]

    def fetchone(self) -> tuple[Any, ...]:
        return self._one

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._many


class _InspectorConnection:
    def __init__(self, cursor: _InspectorCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _InspectorConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def cursor(self) -> _InspectorCursor:
        return self._cursor


def test_restore_inspector_covers_linked_workflow_and_resume_safety() -> None:
    assert {
        "ai_lineage_candidate",
        "conversion_outcome_intent",
        "outbox_candidate_aggregate",
        "outbox_recovery_event",
        "report_conversion_intent",
        "submission_conversion_intent",
        "submission_report_pack",
    }.issubset(REFERENTIAL_CHECKS)
    assert {
        "duplicate_outbox_fingerprint",
        "outbox_failure_state",
        "outbox_lease_state",
        "outbox_publication_state",
        "submission_lease_state",
    }.issubset(SEMANTIC_CHECKS)


def test_restore_inspector_queries_are_read_only() -> None:
    forbidden = ("insert ", "update ", "delete ", "alter ", "drop ", "truncate ")

    for _, query in (*REFERENTIAL_CHECKS.values(), *SEMANTIC_CHECKS.values()):
        normalized = " ".join(query.lower().split())
        assert normalized.startswith("select count(*)")
        assert not any(keyword in normalized for keyword in forbidden)


def test_restore_inspector_enforces_complete_outbox_failure_timing() -> None:
    query = SEMANTIC_CHECKS["outbox_failure_state"][1]

    assert "first_failed_at_utc IS NULL" in query
    assert "last_failed_at_utc IS NULL" in query
    assert "next_attempt_at_utc IS NOT NULL" in query


def test_restore_inspector_preserves_complete_downstream_fencing_history() -> None:
    query = SEMANTIC_CHECKS["submission_lease_state"][1]

    assert "NOT IN (0, 3)" in query
    assert "status <> 'in_flight'" not in query


def test_restore_inspector_rejects_missing_database_url() -> None:
    with pytest.raises(ValueError, match="database_url is required"):
        PostgresRestoredDatabaseInspector("  ")


def test_restore_inspector_maps_catalog_and_invariant_results() -> None:
    tables = frozenset(
        table
        for required_tables, _ in (*REFERENTIAL_CHECKS.values(), *SEMANTIC_CHECKS.values())
        for table in required_tables
    )
    cursor = _InspectorCursor(tables)
    connection = _InspectorConnection(cursor)
    inspector = PostgresRestoredDatabaseInspector(
        "postgresql://restore-target",
        connect=lambda _: connection,
    )

    snapshot = inspector.inspect(expected_tables=tables | {"idea_absent_table"})

    assert snapshot.table_row_counts == {table: 2 for table in tables}
    assert snapshot.table_content_sha256 == {table: "a" * 64 for table in tables}
    assert snapshot.postgres_version == "PostgreSQL 18 test"
    assert len(snapshot.database_identity_sha256) == 64
    assert snapshot.missing_primary_key_tables == ("idea_missing_primary_key",)
    assert snapshot.unvalidated_constraints == ("candidate_state_pending_validation",)
    assert snapshot.invalid_indexes == ("idea_invalid_index",)
    assert snapshot.referential_violation_counts == {name: 0 for name in REFERENTIAL_CHECKS}
    assert snapshot.semantic_violation_counts == {name: 0 for name in SEMANTIC_CHECKS}
    assert cursor.executed[0] == ("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    assert all("idea_absent_table" not in query for query in cursor.executed)


def test_restore_inspector_skips_checks_without_required_tables() -> None:
    cursor = _InspectorCursor(frozenset())
    inspector = PostgresRestoredDatabaseInspector(
        "postgresql://empty-restore-target",
        connect=lambda _: _InspectorConnection(cursor),
    )

    snapshot = inspector.inspect(expected_tables=frozenset())

    assert snapshot.table_row_counts == {}
    assert snapshot.table_content_sha256 == {}
    assert snapshot.missing_primary_key_tables == ()
    assert snapshot.referential_violation_counts == {}
    assert snapshot.semantic_violation_counts == {}
