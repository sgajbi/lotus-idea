from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Mapping

from app.domain.data_lifecycle import DataLifecycleState
from app.domain.data_lifecycle_schedule import ScheduledLifecycleControlSnapshot
from app.observability.service_slo_metrics import observe_postgres_operation


class PostgresScheduledDataLifecycleRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def scan_data_lifecycle_controls(
        self,
        *,
        evaluated_at_utc: datetime,
        limit: int,
    ) -> tuple[ScheduledLifecycleControlSnapshot, ...]:
        started_at = time.perf_counter()
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_SCHEDULED_REVIEW_QUERY, (evaluated_at_utc, limit))
                snapshots = tuple(_snapshot_from_row(row) for row in cursor.fetchall())
            observe_postgres_operation(
                operation="projection_read",
                outcome="success",
                duration_seconds=time.perf_counter() - started_at,
            )
            return snapshots
        except Exception:
            observe_postgres_operation(
                operation="projection_read",
                outcome="failed",
                duration_seconds=time.perf_counter() - started_at,
            )
            raise


def _snapshot_from_row(row: Mapping[str, Any]) -> ScheduledLifecycleControlSnapshot:
    held_from_state = row.get("held_from_state")
    return ScheduledLifecycleControlSnapshot(
        candidate_id=str(row["candidate_id"]),
        tenant_id=str(row["tenant_id"]),
        policy_ref=str(row["policy_ref"]),
        state=DataLifecycleState(str(row["state"])),
        retention_expires_at_utc=row["retention_expires_at_utc"],
        control_version=int(row["version"]),
        active_outbox_count=int(row["active_outbox_count"]),
        active_downstream_count=int(row["active_downstream_count"]),
        held_from_state=(
            DataLifecycleState(str(held_from_state)) if held_from_state is not None else None
        ),
    )


_SCHEDULED_REVIEW_QUERY = """
    SELECT control.candidate_id,
           control.tenant_id,
           control.policy_ref,
           control.state,
           control.held_from_state,
           control.retention_expires_at_utc,
           control.version,
           (
               SELECT COUNT(*)
               FROM idea_outbox_event event
               WHERE event.aggregate_type = 'idea_candidate'
                 AND event.aggregate_id = control.candidate_id
                 AND event.status <> 'published'
           ) AS active_outbox_count,
           (
               SELECT COUNT(*)
               FROM idea_downstream_submission submission
               WHERE submission.status IN ('in_flight', 'reconciliation_required')
                 AND ((
                     submission.resource_type = 'conversion_intent'
                     AND submission.resource_id IN (
                         SELECT conversion_intent_id
                         FROM idea_conversion_intent
                         WHERE candidate_id = control.candidate_id
                     )
                 ) OR (
                     submission.resource_type = 'report_evidence_pack'
                     AND submission.resource_id IN (
                         SELECT report_evidence_pack_id
                         FROM idea_report_evidence_pack_request
                         WHERE candidate_id = control.candidate_id
                     )
                 ))
           ) AS active_downstream_count
    FROM idea_data_lifecycle_control control
    WHERE control.retention_expires_at_utc <= %s
      AND control.state <> 'purged'
    ORDER BY control.retention_expires_at_utc, control.candidate_id
    LIMIT %s
"""
