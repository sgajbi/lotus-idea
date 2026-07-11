from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from app.domain.outbox_recovery import outbox_dead_letter_support_reference
from tests.unit.postgres_downstream_submission_fake_helpers import (
    execute_downstream_submission_query,
)
from tests.unit.postgres_outbox_fake_helpers import (
    claim_outbox_event_rows,
    fail_outbox_event_row,
    outbox_delivery_ready_rows,
    outbox_readiness_summary_row,
    publish_outbox_event_row,
    recover_dead_letter_row,
)
from tests.unit.postgres_repository_lookup_fake_helpers import (
    candidate_detail_rows,
    downstream_lookup_rows,
    idempotency_lookup_rows,
)
from tests.unit.postgres_repository_mutation_fake_helpers import (
    row_for_insert,
    update_candidate_record_row,
)
from tests.unit.postgres_repository_runtime_trust_helpers import (
    candidate_json_count_rows,
    runtime_trust_telemetry_count_rows,
    runtime_trust_telemetry_summary_rows,
    table_count_rows,
)
from tests.unit.postgres_review_queue_fake_helpers import (
    review_queue_count_rows,
    review_queue_page_rows,
    review_queue_readiness_summary_rows,
)


class FakePostgresCursor:
    def __init__(self, connection: FakePostgresConnection) -> None:
        self.connection = connection
        self._rows: list[dict[str, Any]] = []
        self.rowcount = 0

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        normalized = " ".join(query.lower().split())
        self.connection.executed_sql.append(normalized)
        self.rowcount = 0
        if _execute_data_lifecycle_query(self, normalized, params):
            return
        if execute_downstream_submission_query(self, normalized, params):
            return
        if _execute_outbox_recovery_query(self, normalized, params):
            return
        if normalized.startswith("/* lotus-idea review-queue-count */"):
            assert params is not None
            self._rows = review_queue_count_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea review-queue-page */"):
            assert params is not None
            self._rows = review_queue_page_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea review-queue-readiness-summary */"):
            assert params is not None
            self._rows = review_queue_readiness_summary_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea outbox-delivery-ready-events */"):
            assert params is not None
            self._rows = outbox_delivery_ready_rows(self.connection, params)
            return
        if normalized.startswith("/* lotus-idea outbox-readiness-summary */"):
            assert params is not None
            self._rows = outbox_readiness_summary_row(self.connection, params)
            return
        if normalized.startswith("/* lotus-idea downstream-realization-readiness-summary */"):
            quarantined_intents = {
                row["conversion_intent_id"]
                for row in self.connection.rows["idea_conversion_outcome_quarantine"]
            }
            self._rows = [
                {
                    "conversion_intent_count": len(self.connection.rows["idea_conversion_intent"]),
                    "conversion_outcome_count": len(
                        {
                            row["conversion_intent_id"]
                            for row in self.connection.rows["idea_conversion_outcome"]
                            if row["conversion_intent_id"] not in quarantined_intents
                        }
                    ),
                    "report_evidence_pack_request_count": len(
                        self.connection.rows["idea_report_evidence_pack_request"]
                    ),
                }
            ]
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-summary */"):
            self._rows = runtime_trust_telemetry_summary_rows(self.connection.rows)
            return
        if normalized.startswith(
            "/* lotus-idea runtime-trust-telemetry-source-authority-counts */"
        ):
            self._rows = runtime_trust_telemetry_count_rows(
                self.connection.rows,
                "source_system",
            )
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-freshness-counts */"):
            self._rows = runtime_trust_telemetry_count_rows(self.connection.rows, "freshness")
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-supportability-counts */"):
            self._rows = candidate_json_count_rows(
                self.connection.rows,
                ("evidence_packet", "supportability"),
            )
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-lifecycle-counts */"):
            self._rows = table_count_rows(
                self.connection.rows,
                "idea_candidate_record",
                "lifecycle_status",
                active_candidates_only=True,
            )
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-data-lifecycle-counts */"):
            self._rows = table_count_rows(
                self.connection.rows, "idea_data_lifecycle_control", "state"
            )
            return
        if normalized.startswith("/* lotus-idea candidate-detail"):
            assert params is not None
            self._rows = candidate_detail_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea downstream-lookup"):
            assert params is not None
            self._rows = downstream_lookup_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea idempotency-lookup */"):
            assert params is not None
            self._rows = idempotency_lookup_rows(self.connection, normalized, params)
            return
        if _execute_conversion_outcome_query(self, normalized, params):
            return
        if normalized.startswith("/* lotus-idea review-identity-decision */"):
            assert params is not None
            self._rows = [
                {"decision_json": row["decision_json"]}
                for row in self.connection.rows["idea_review_decision"]
                if row["review_decision_id"] == params[0]
            ]
            return
        if normalized.startswith("/* lotus-idea review-identity-feedback */"):
            assert params is not None
            self._rows = [
                {"feedback_json": row["feedback_json"]}
                for row in self.connection.rows["idea_feedback_event"]
                if row["feedback_event_id"] == params[0]
            ]
            return
        if normalized.startswith("with selected"):
            assert params is not None
            self.connection.begin_write()
            self._rows = claim_outbox_event_rows(self.connection, params)
            return
        if normalized.startswith("update idea_candidate_record"):
            assert params is not None
            self.connection.begin_write()
            self._rows = update_candidate_record_row(self.connection.rows, params)
            return
        if normalized.startswith("update idea_outbox_event"):
            assert params is not None
            self.connection.begin_write()
            if "set status = %s, published_at_utc = %s" in normalized:
                self._rows = publish_outbox_event_row(self.connection, params)
            elif "set status = %s, published_at_utc = null" in normalized:
                self._rows = recover_dead_letter_row(self.connection, params)
            else:
                self._rows = fail_outbox_event_row(self.connection, params)
            return
        if normalized.startswith("select"):
            if (
                "from idea_outbox_event" in normalized
                and "where outbox_event_id = %s" in normalized
            ):
                assert params is not None
                self._rows = [
                    row
                    for row in self.connection.rows["idea_outbox_event"]
                    if row["outbox_event_id"] == params[0]
                ]
                return
            self._rows = list(self.connection.rows[_table_from_select(normalized)])
            return
        if normalized.startswith("delete from"):
            self.connection.begin_write()
            self.connection.deletes += 1
            self.connection.rows[normalized.split()[2]].clear()
            return
        if normalized.startswith("insert into"):
            table_name = normalized.split()[2]
            self.connection.begin_write()
            if table_name == self.connection.fail_on_insert:
                raise RuntimeError(f"insert failed for {table_name}")
            assert params is not None
            if table_name == "idea_idempotency_record" and "on conflict" in normalized:
                idempotency_key = params[0]
                if any(
                    row["idempotency_key"] == idempotency_key
                    for row in self.connection.rows[table_name]
                ):
                    self._rows = []
                    return
                row = row_for_insert(table_name, params)
                self.connection.rows[table_name].append(row)
                self._rows = [{"idempotency_key": idempotency_key}]
                return
            if _execute_identity_insert(self, table_name, normalized, params):
                return
            self.connection.rows[table_name].append(row_for_insert(table_name, params))
            self.rowcount = 1
            return
        raise AssertionError(f"unexpected SQL: {query}")

    def fetchall(self) -> Sequence[dict[str, Any]]:
        return self._rows

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __enter__(self) -> FakePostgresCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _execute_data_lifecycle_query(
    cursor: FakePostgresCursor,
    normalized: str,
    params: Sequence[Any] | None,
) -> bool:
    connection = cursor.connection
    if normalized.startswith("/* lotus-idea downstream-submission-lifecycle-fence */"):
        assert params is not None
        resource_table = (
            "idea_conversion_intent"
            if "from idea_conversion_intent" in normalized
            else "idea_report_evidence_pack_request"
        )
        identity_column = (
            "conversion_intent_id"
            if resource_table == "idea_conversion_intent"
            else "report_evidence_pack_id"
        )
        resources = [
            row for row in connection.rows[resource_table] if row[identity_column] == params[0]
        ]
        controls = {
            row["candidate_id"]: row for row in connection.rows["idea_data_lifecycle_control"]
        }
        cursor._rows = [
            dict(control)
            for resource in resources
            if (control := controls.get(resource["candidate_id"])) is not None
        ]
        if not resources and not controls:
            cursor._rows = [
                {"candidate_id": "legacy-fixture", "state": "active", "held_from_state": None}
            ]
        return True
    if normalized.startswith("select") and "candidate_id = any(" in normalized:
        assert params is not None
        candidate_ids = set(params[0])
        table = (
            "idea_data_lifecycle_control"
            if "from idea_data_lifecycle_control" in normalized
            else "idea_candidate_record"
        )
        cursor._rows = [
            row for row in connection.rows[table] if row["candidate_id"] in candidate_ids
        ]
        return True
    if not normalized.startswith("insert into idea_data_lifecycle_control"):
        return False
    assert params is not None
    connection.begin_write()
    candidate_id, tenant_id, policy_ref, persisted_at_utc, updated_at_utc = params
    rows = connection.rows["idea_data_lifecycle_control"]
    if any(row["candidate_id"] == candidate_id for row in rows):
        return True
    rows.append(
        {
            "candidate_id": candidate_id,
            "tenant_id": tenant_id,
            "policy_ref": policy_ref,
            "state": "active",
            "retention_expires_at_utc": persisted_at_utc.replace(year=persisted_at_utc.year + 7),
            "version": 1,
            "updated_at_utc": updated_at_utc,
            "held_from_state": None,
            "hold_authority_ref": None,
            "hold_change_reference": None,
            "held_at_utc": None,
            "erased_at_utc": None,
            "purged_at_utc": None,
            "tombstone_sha256": None,
        }
    )
    cursor.rowcount = 1
    return True


def _execute_conversion_outcome_query(
    cursor: FakePostgresCursor,
    normalized: str,
    params: Sequence[Any] | None,
) -> bool:
    if normalized.startswith("/* lotus-idea conversion-outcome-identity */"):
        assert params is not None
        cursor._rows = [
            {"outcome_json": row["outcome_json"]}
            for row in cursor.connection.rows["idea_conversion_outcome"]
            if row["conversion_outcome_id"] == params[0]
        ]
        return True
    if normalized.startswith("/* lotus-idea conversion-outcome-history */"):
        assert params is not None
        rows = [
            row
            for row in cursor.connection.rows["idea_conversion_outcome"]
            if row["conversion_intent_id"] == params[0]
        ]
        rows.sort(
            key=lambda row: (
                row["source_event_version"],
                row["recorded_at_utc"],
                row["conversion_outcome_id"],
            )
        )
        cursor._rows = [{"outcome_json": row["outcome_json"]} for row in rows]
        return True
    return False


def _execute_identity_insert(
    cursor: FakePostgresCursor,
    table_name: str,
    normalized: str,
    params: Sequence[Any],
) -> bool:
    identity_columns = {
        "idea_review_decision": "review_decision_id",
        "idea_feedback_event": "feedback_event_id",
    }
    if table_name in identity_columns and "on conflict" in normalized:
        identity_column = identity_columns[table_name]
        resource_id = params[0]
        if any(row[identity_column] == resource_id for row in cursor.connection.rows[table_name]):
            cursor._rows = []
            return True
        cursor.connection.rows[table_name].append(row_for_insert(table_name, params))
        cursor._rows = [{identity_column: resource_id}]
        return True
    if table_name == "idea_conversion_outcome" and "on conflict" in normalized:
        resource_id, conversion_intent_id = params[:2]
        source_event_version = params[4]
        if any(
            row["conversion_outcome_id"] == resource_id
            or (
                row["conversion_intent_id"] == conversion_intent_id
                and row["source_event_version"] == source_event_version
            )
            for row in cursor.connection.rows[table_name]
        ):
            cursor._rows = []
            return True
        cursor.connection.rows[table_name].append(row_for_insert(table_name, params))
        cursor._rows = [{"conversion_outcome_id": resource_id}]
        return True
    return False


def _execute_outbox_recovery_query(
    cursor: FakePostgresCursor,
    normalized: str,
    params: Sequence[Any] | None,
) -> bool:
    connection = cursor.connection
    if normalized.startswith("/* lotus-idea outbox-dead-letter-summaries */"):
        assert params is not None
        status, limit = params
        rows = [
            dict(row) for row in connection.rows["idea_outbox_event"] if row["status"] == status
        ]
        rows.sort(
            key=lambda row: (row["last_failed_at_utc"], row["outbox_event_id"]),
            reverse=True,
        )
        cursor._rows = rows[:limit]
        return True
    if normalized.startswith("/* lotus-idea outbox-recovery-audit-records */"):
        cursor._rows = sorted(
            connection.rows["idea_outbox_recovery_audit"],
            key=lambda row: (row["requested_at_utc"], row["recovery_id"]),
        )
        return True
    if (
        "from idea_outbox_recovery_audit" in normalized
        and "where idempotency_fingerprint = %s" in normalized
    ):
        assert params is not None
        cursor._rows = [
            row
            for row in connection.rows["idea_outbox_recovery_audit"]
            if row["idempotency_fingerprint"] == params[0]
        ]
        return True
    if (
        "count(*) as recovery_count" in normalized
        and "from idea_outbox_recovery_audit" in normalized
    ):
        assert params is not None
        cursor._rows = [
            {
                "recovery_count": sum(
                    1
                    for row in connection.rows["idea_outbox_recovery_audit"]
                    if row["outbox_event_id"] == params[0]
                )
            }
        ]
        return True
    if normalized.startswith("/* lotus-idea outbox-dead-letter-by-support-reference */"):
        assert params is not None
        cursor._rows = [
            row
            for row in connection.rows["idea_outbox_event"]
            if outbox_dead_letter_support_reference(row["outbox_event_id"]) == params[0]
        ]
        return True
    if normalized.startswith("insert into idea_outbox_recovery_audit"):
        assert params is not None
        connection.begin_write()
        recovery_columns = (
            "recovery_id",
            "outbox_event_id",
            "support_reference",
            "idempotency_fingerprint",
            "request_fingerprint",
            "actor_subject",
            "recovery_reason",
            "change_reference",
            "requested_at_utc",
            "lease_owner",
            "lease_attempt_id",
            "lease_expires_at_utc",
            "original_retry_count",
            "original_failure_reason",
            "original_first_failed_at_utc",
            "original_last_failed_at_utc",
        )
        connection.rows["idea_outbox_recovery_audit"].append(dict(zip(recovery_columns, params)))
        return True
    return False


class FakePostgresConnection:
    def __init__(
        self,
        *,
        fail_on_insert: str | None = None,
        fail_on_update: str | None = None,
    ) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {
            "idea_candidate_record": [],
            "idea_idempotency_record": [],
            "idea_lifecycle_history": [],
            "idea_audit_event": [],
            "idea_outbox_event": [],
            "idea_review_decision": [],
            "idea_feedback_event": [],
            "idea_conversion_intent": [],
            "idea_conversion_outcome": [],
            "idea_conversion_outcome_quarantine": [],
            "idea_report_evidence_pack_request": [],
            "idea_downstream_submission": [],
            "idea_ai_explanation_lineage": [],
            "idea_outbox_recovery_audit": [],
            "idea_data_lifecycle_control": [],
            "idea_data_lifecycle_operation": [],
        }
        self.fail_on_insert = fail_on_insert
        self.fail_on_update = fail_on_update
        self.commits = 0
        self.rollbacks = 0
        self.deletes = 0
        self.executed_sql: list[str] = []
        self._transaction_rows: dict[str, list[dict[str, Any]]] | None = None

    def cursor(self) -> FakePostgresCursor:
        return FakePostgresCursor(self)

    def begin_write(self) -> None:
        if self._transaction_rows is None:
            self._transaction_rows = deepcopy(self.rows)

    def commit(self) -> None:
        self._transaction_rows = None
        self.commits += 1

    def rollback(self) -> None:
        if self._transaction_rows is not None:
            self.rows = deepcopy(self._transaction_rows)
            self._transaction_rows = None
        self.rollbacks += 1


def _table_from_select(query: str) -> str:
    for table_name in (
        "idea_candidate_record",
        "idea_idempotency_record",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_conversion_outcome_quarantine",
        "idea_conversion_outcome",
        "idea_report_evidence_pack_request",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
        "idea_outbox_recovery_audit",
        "idea_data_lifecycle_control",
        "idea_data_lifecycle_operation",
    ):
        if f" from {table_name}" in query:
            return table_name
    raise AssertionError(f"unknown select table: {query}")
