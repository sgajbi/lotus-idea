from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from tests.unit.postgres_outbox_fake_helpers import (
    claim_outbox_event_rows,
    fail_outbox_event_row,
    outbox_delivery_ready_rows,
    outbox_readiness_summary_row,
    publish_outbox_event_row,
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

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        normalized = " ".join(query.lower().split())
        self.connection.executed_sql.append(normalized)
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
            self._rows = [
                {
                    "conversion_intent_count": len(self.connection.rows["idea_conversion_intent"]),
                    "conversion_outcome_count": len(
                        self.connection.rows["idea_conversion_outcome"]
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
                self.connection.rows, "idea_candidate_record", "lifecycle_status"
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
            self.connection.rows[table_name].append(row_for_insert(table_name, params))
            return
        raise AssertionError(f"unexpected SQL: {query}")

    def fetchall(self) -> Sequence[dict[str, Any]]:
        return self._rows

    def __enter__(self) -> FakePostgresCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakePostgresConnection:
    def __init__(self, *, fail_on_insert: str | None = None) -> None:
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
            "idea_report_evidence_pack_request": [],
            "idea_downstream_submission": [],
            "idea_ai_explanation_lineage": [],
        }
        self.fail_on_insert = fail_on_insert
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
        "idea_conversion_outcome",
        "idea_report_evidence_pack_request",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
    ):
        if f" from {table_name}" in query:
            return table_name
    raise AssertionError(f"unknown select table: {query}")
