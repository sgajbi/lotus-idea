from __future__ import annotations

import hashlib
from typing import Any, Callable

import psycopg
from psycopg import sql

from app.domain.disaster_recovery import RestoredDatabaseSnapshot

ConnectionFactory = Callable[[str], Any]

REFERENTIAL_CHECKS: dict[str, tuple[frozenset[str], str]] = {
    "ai_lineage_candidate": (
        frozenset({"idea_ai_explanation_lineage", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_ai_explanation_lineage child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "audit_candidate": (
        frozenset({"idea_audit_event", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_audit_event child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE child.candidate_id IS NOT NULL AND parent.candidate_id IS NULL""",
    ),
    "conversion_intent_candidate": (
        frozenset({"idea_conversion_intent", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_conversion_intent child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "conversion_outcome_intent": (
        frozenset({"idea_conversion_outcome", "idea_conversion_intent"}),
        """SELECT COUNT(*) FROM idea_conversion_outcome child
           LEFT JOIN idea_conversion_intent parent
             ON parent.conversion_intent_id = child.conversion_intent_id
           WHERE parent.conversion_intent_id IS NULL""",
    ),
    "conversion_outcome_supersedes": (
        frozenset({"idea_conversion_outcome"}),
        """SELECT COUNT(*) FROM idea_conversion_outcome child
           LEFT JOIN idea_conversion_outcome parent
             ON parent.conversion_outcome_id = child.supersedes_conversion_outcome_id
           WHERE child.supersedes_conversion_outcome_id IS NOT NULL
             AND parent.conversion_outcome_id IS NULL""",
    ),
    "feedback_candidate": (
        frozenset({"idea_feedback_event", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_feedback_event child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "idempotency_candidate": (
        frozenset({"idea_idempotency_record", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_idempotency_record child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE child.candidate_id IS NOT NULL AND parent.candidate_id IS NULL""",
    ),
    "lifecycle_candidate": (
        frozenset({"idea_lifecycle_history", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_lifecycle_history child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "outbox_candidate_aggregate": (
        frozenset({"idea_outbox_event", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_outbox_event child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.aggregate_id
           WHERE child.aggregate_type = 'idea_candidate' AND parent.candidate_id IS NULL""",
    ),
    "outbox_recovery_event": (
        frozenset({"idea_outbox_recovery_audit", "idea_outbox_event"}),
        """SELECT COUNT(*) FROM idea_outbox_recovery_audit child
           LEFT JOIN idea_outbox_event parent ON parent.outbox_event_id = child.outbox_event_id
           WHERE parent.outbox_event_id IS NULL""",
    ),
    "report_candidate": (
        frozenset({"idea_report_evidence_pack_request", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_report_evidence_pack_request child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "report_conversion_intent": (
        frozenset({"idea_report_evidence_pack_request", "idea_conversion_intent"}),
        """SELECT COUNT(*) FROM idea_report_evidence_pack_request child
           LEFT JOIN idea_conversion_intent parent
             ON parent.conversion_intent_id = child.conversion_intent_id
           WHERE parent.conversion_intent_id IS NULL""",
    ),
    "review_candidate": (
        frozenset({"idea_review_decision", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_review_decision child
           LEFT JOIN idea_candidate_record parent ON parent.candidate_id = child.candidate_id
           WHERE parent.candidate_id IS NULL""",
    ),
    "submission_conversion_intent": (
        frozenset({"idea_downstream_submission", "idea_conversion_intent"}),
        """SELECT COUNT(*) FROM idea_downstream_submission child
           LEFT JOIN idea_conversion_intent parent
             ON parent.conversion_intent_id = child.resource_id
           WHERE child.resource_type = 'conversion_intent'
             AND parent.conversion_intent_id IS NULL""",
    ),
    "submission_report_pack": (
        frozenset({"idea_downstream_submission", "idea_report_evidence_pack_request"}),
        """SELECT COUNT(*) FROM idea_downstream_submission child
           LEFT JOIN idea_report_evidence_pack_request parent
             ON parent.report_evidence_pack_id = child.resource_id
           WHERE child.resource_type = 'report_evidence_pack'
             AND parent.report_evidence_pack_id IS NULL""",
    ),
}

SEMANTIC_CHECKS: dict[str, tuple[frozenset[str], str]] = {
    "candidate_quarantine_source": (
        frozenset({"idea_candidate_state_quarantine", "idea_candidate_record"}),
        """SELECT COUNT(*) FROM idea_candidate_state_quarantine quarantine
           LEFT JOIN idea_candidate_record source ON source.candidate_id = quarantine.candidate_id
           WHERE source.candidate_id IS NULL""",
    ),
    "conversion_quarantine_source": (
        frozenset({"idea_conversion_outcome_quarantine", "idea_conversion_outcome"}),
        """SELECT COUNT(*) FROM idea_conversion_outcome_quarantine quarantine
           LEFT JOIN idea_conversion_outcome source
             ON source.conversion_outcome_id = quarantine.conversion_outcome_id
           WHERE source.conversion_outcome_id IS NULL""",
    ),
    "duplicate_outbox_fingerprint": (
        frozenset({"idea_outbox_event"}),
        """SELECT COUNT(*) FROM (
               SELECT idempotency_fingerprint FROM idea_outbox_event
               WHERE idempotency_fingerprint IS NOT NULL
               GROUP BY idempotency_fingerprint HAVING COUNT(*) > 1
           ) duplicates""",
    ),
    "outbox_failure_state": (
        frozenset({"idea_outbox_event"}),
        """SELECT COUNT(*) FROM idea_outbox_event
           WHERE (status IN ('failed', 'dead_letter') AND (
                    failure_reason IS NULL
                    OR first_failed_at_utc IS NULL
                    OR last_failed_at_utc IS NULL
                 ))
              OR (status = 'failed' AND next_attempt_at_utc IS NULL)
              OR (status = 'dead_letter' AND next_attempt_at_utc IS NOT NULL)
              OR (status IN ('leased', 'published') AND (
                    (failure_reason IS NULL) <> (first_failed_at_utc IS NULL)
                    OR (first_failed_at_utc IS NULL) <> (last_failed_at_utc IS NULL)
                    OR next_attempt_at_utc IS NOT NULL
                 ))
              OR (status = 'pending' AND (
                    failure_reason IS NOT NULL
                    OR first_failed_at_utc IS NOT NULL
                    OR last_failed_at_utc IS NOT NULL
                    OR next_attempt_at_utc IS NOT NULL
                 ))""",
    ),
    "outbox_lease_state": (
        frozenset({"idea_outbox_event"}),
        """SELECT COUNT(*) FROM idea_outbox_event
           WHERE (status = 'leased' AND (
                    lease_owner IS NULL OR lease_attempt_id IS NULL OR lease_expires_at_utc IS NULL
                 ))
              OR (status <> 'leased' AND (
                    lease_owner IS NOT NULL OR lease_attempt_id IS NOT NULL
                    OR lease_expires_at_utc IS NOT NULL
                 ))""",
    ),
    "outbox_publication_state": (
        frozenset({"idea_outbox_event"}),
        """SELECT COUNT(*) FROM idea_outbox_event
           WHERE (status = 'published' AND published_at_utc IS NULL)
              OR (status <> 'published' AND published_at_utc IS NOT NULL)""",
    ),
    "submission_lease_state": (
        frozenset({"idea_downstream_submission"}),
        """SELECT COUNT(*) FROM idea_downstream_submission
           WHERE (status = 'in_flight' AND (
                    lease_owner IS NULL OR lease_attempt_id IS NULL OR lease_expires_at_utc IS NULL
                 ))
              OR ((lease_owner IS NULL)::int
                  + (lease_attempt_id IS NULL)::int
                  + (lease_expires_at_utc IS NULL)::int) NOT IN (0, 3)""",
    ),
    "submission_resource_type": (
        frozenset({"idea_downstream_submission"}),
        """SELECT COUNT(*) FROM idea_downstream_submission
           WHERE resource_type NOT IN ('conversion_intent', 'report_evidence_pack')""",
    ),
}


class PostgresRestoredDatabaseInspector:
    def __init__(
        self,
        database_url: str,
        *,
        connect: ConnectionFactory = psycopg.connect,
    ) -> None:
        if not database_url.strip():
            raise ValueError("database_url is required")
        self._database_url = database_url
        self._connect = connect

    def inspect(self, *, expected_tables: frozenset[str]) -> RestoredDatabaseSnapshot:
        with self._connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                observed_tables = _observed_owned_tables(cursor)
                present_tables = expected_tables.intersection(observed_tables)
                row_counts, content_hashes = _table_summaries(cursor, present_tables)
                identity = _database_identity(cursor)
                postgres_version = _scalar_text(cursor, "SELECT version()")
                missing_primary_keys = _missing_primary_keys(cursor, present_tables)
                unvalidated_constraints = _unvalidated_constraints(cursor)
                invalid_indexes = _invalid_indexes(cursor)
                referential_violations = _run_checks(cursor, REFERENTIAL_CHECKS, observed_tables)
                semantic_violations = _run_checks(cursor, SEMANTIC_CHECKS, observed_tables)

        return RestoredDatabaseSnapshot(
            database_identity_sha256=identity,
            postgres_version=postgres_version,
            table_row_counts=row_counts,
            table_content_sha256=content_hashes,
            missing_primary_key_tables=tuple(sorted(missing_primary_keys)),
            unvalidated_constraints=tuple(sorted(unvalidated_constraints)),
            invalid_indexes=tuple(sorted(invalid_indexes)),
            referential_violation_counts=referential_violations,
            semantic_violation_counts=semantic_violations,
        )


def _observed_owned_tables(cursor: Any) -> frozenset[str]:
    cursor.execute(
        """SELECT tablename FROM pg_catalog.pg_tables
           WHERE schemaname = 'public' AND tablename LIKE 'idea\\_%' ESCAPE '\\'
           ORDER BY tablename"""
    )
    return frozenset(str(row[0]) for row in cursor.fetchall())


def _table_summaries(cursor: Any, tables: frozenset[str]) -> tuple[dict[str, int], dict[str, str]]:
    row_counts: dict[str, int] = {}
    content_hashes: dict[str, str] = {}
    for table in sorted(tables):
        query = sql.SQL(
            """SELECT COUNT(*), encode(sha256(
                   COALESCE(string_agg(row_digest, '' ORDER BY row_digest), '')::bytea
               ), 'hex')
               FROM (
                   SELECT encode(sha256(row_to_json(source_row)::text::bytea), 'hex') row_digest
                   FROM {} AS source_row
               ) hashed_rows"""
        ).format(sql.Identifier(table))
        cursor.execute(query)
        row = cursor.fetchone()
        row_counts[table] = int(row[0])
        content_hashes[table] = str(row[1])
    return row_counts, content_hashes


def _database_identity(cursor: Any) -> str:
    cursor.execute(
        """SELECT current_database(), current_user,
                  COALESCE(inet_server_addr()::text, 'local'),
                  COALESCE(inet_server_port()::text, 'local')"""
    )
    identity = ":".join(str(value) for value in cursor.fetchone())
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _missing_primary_keys(cursor: Any, tables: frozenset[str]) -> set[str]:
    if not tables:
        return set()
    cursor.execute(
        """SELECT requested.table_name
           FROM unnest(%s::text[]) requested(table_name)
           WHERE NOT EXISTS (
               SELECT 1 FROM pg_catalog.pg_constraint constraint_record
               JOIN pg_catalog.pg_class table_record
                 ON table_record.oid = constraint_record.conrelid
               JOIN pg_catalog.pg_namespace namespace_record
                 ON namespace_record.oid = table_record.relnamespace
               WHERE namespace_record.nspname = 'public'
                 AND table_record.relname = requested.table_name
                 AND constraint_record.contype = 'p'
           )""",
        (sorted(tables),),
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _unvalidated_constraints(cursor: Any) -> set[str]:
    cursor.execute(
        """SELECT constraint_record.conname
           FROM pg_catalog.pg_constraint constraint_record
           JOIN pg_catalog.pg_class table_record ON table_record.oid = constraint_record.conrelid
           JOIN pg_catalog.pg_namespace namespace_record
             ON namespace_record.oid = table_record.relnamespace
           WHERE namespace_record.nspname = 'public'
             AND table_record.relname LIKE 'idea\\_%' ESCAPE '\\'
             AND NOT constraint_record.convalidated"""
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _invalid_indexes(cursor: Any) -> set[str]:
    cursor.execute(
        """SELECT index_record.relname
           FROM pg_catalog.pg_index index_state
           JOIN pg_catalog.pg_class index_record ON index_record.oid = index_state.indexrelid
           JOIN pg_catalog.pg_class table_record ON table_record.oid = index_state.indrelid
           JOIN pg_catalog.pg_namespace namespace_record
             ON namespace_record.oid = table_record.relnamespace
           WHERE namespace_record.nspname = 'public'
             AND table_record.relname LIKE 'idea\\_%' ESCAPE '\\'
             AND (NOT index_state.indisvalid OR NOT index_state.indisready)"""
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _run_checks(
    cursor: Any,
    checks: dict[str, tuple[frozenset[str], str]],
    observed_tables: frozenset[str],
) -> dict[str, int]:
    results: dict[str, int] = {}
    for name, (required_tables, query) in sorted(checks.items()):
        if required_tables.issubset(observed_tables):
            cursor.execute(query)
            results[name] = int(cursor.fetchone()[0])
    return results


def _scalar_text(cursor: Any, query: str) -> str:
    cursor.execute(query)
    return str(cursor.fetchone()[0])
