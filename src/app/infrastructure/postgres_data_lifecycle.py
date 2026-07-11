from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import hashlib
import json
from typing import Any, Mapping

from psycopg.types.json import Jsonb

from app.domain.data_lifecycle import (
    REGULATED_ADVISORY_POLICY_REF,
    DataLifecycleBlocker,
    DataLifecycleCandidateContext,
    DataLifecycleCommand,
    DataLifecycleControl,
    DataLifecycleDecision,
    DataLifecycleEvaluation,
    DataLifecycleOperationResult,
    DataLifecycleState,
)
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_data_lifecycle_redaction import (
    data_lifecycle_actor_tombstone,
    purge_expired_candidate_payloads,
    redact_candidate_graph,
)
from app.ports.data_lifecycle import DataLifecycleEvaluator


class PostgresDataLifecycleRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: DataLifecycleEvaluator,
    ) -> DataLifecycleOperationResult:
        try:
            with self._connection.cursor() as cursor:
                _lock_idempotency_key(cursor, command.idempotency_key)
                existing = _load_operation(cursor, command.idempotency_key)
                if existing is not None:
                    result = _replay_or_conflict(cursor, command, existing)
                else:
                    context = _load_candidate_context(cursor, command.candidate_id)
                    evaluation = evaluator(
                        command,
                        context,
                        evaluated_at_utc=evaluated_at_utc,
                    )
                    result = _apply_evaluation(
                        cursor,
                        command=command,
                        evaluation=evaluation,
                        evaluated_at_utc=evaluated_at_utc,
                    )
            self._connection.commit()
            return result
        except Exception:
            self._connection.rollback()
            raise


class DataLifecycleWriteBlockedError(RuntimeError):
    def __init__(self, candidate_id: str, blocker: str) -> None:
        self.candidate_id = candidate_id
        self.blocker = blocker
        super().__init__("candidate mutation is blocked by data lifecycle state")


def insert_data_lifecycle_control_for_candidate(
    cursor: Any,
    record: CandidatePersistenceRecord,
) -> None:
    access_scope = record.candidate.access_scope
    if access_scope is None:
        raise DataLifecycleWriteBlockedError(
            record.candidate.candidate_id,
            "tenant_scope_missing",
        )
    cursor.execute(
        """INSERT INTO idea_data_lifecycle_control (
               candidate_id, tenant_id, policy_ref, state,
               retention_expires_at_utc, version, updated_at_utc
           ) VALUES (%s, %s, %s, 'active', %s + INTERVAL '7 years', 1, %s)
           ON CONFLICT (candidate_id) DO NOTHING""",
        (
            record.candidate.candidate_id,
            access_scope.tenant_id,
            REGULATED_ADVISORY_POLICY_REF,
            record.persisted_at_utc,
            record.candidate.updated_at_utc,
        ),
    )


def assert_data_lifecycle_allows_candidate_writes(
    cursor: Any,
    candidate_ids: set[str],
) -> None:
    if not candidate_ids:
        return
    ordered_ids = sorted(candidate_ids)
    cursor.execute(
        """SELECT candidate_id
           FROM idea_candidate_record
           WHERE candidate_id = ANY(%s::text[])
           ORDER BY candidate_id
           FOR UPDATE""",
        (ordered_ids,),
    )
    existing_ids = {
        str(row["candidate_id"]) for row in cursor.fetchall() if isinstance(row, Mapping)
    }
    if not existing_ids:
        return
    cursor.execute(
        """SELECT candidate_id, state, held_from_state
           FROM idea_data_lifecycle_control
           WHERE candidate_id = ANY(%s::text[])
           ORDER BY candidate_id
           FOR UPDATE""",
        (sorted(existing_ids),),
    )
    controls = {
        str(row["candidate_id"]): str(row["held_from_state"] or row["state"])
        for row in cursor.fetchall()
        if isinstance(row, Mapping)
    }
    for candidate_id in sorted(existing_ids):
        effective_state = controls.get(candidate_id)
        if effective_state is None:
            raise DataLifecycleWriteBlockedError(candidate_id, "lifecycle_control_missing")
        if effective_state in {DataLifecycleState.ERASED.value, DataLifecycleState.PURGED.value}:
            raise DataLifecycleWriteBlockedError(candidate_id, "candidate_erased")


def _lock_idempotency_key(cursor: Any, idempotency_key: str) -> None:
    cursor.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        (idempotency_key,),
    )


def _load_operation(cursor: Any, idempotency_key: str) -> Mapping[str, Any] | None:
    cursor.execute(
        """SELECT operation_id, request_fingerprint, candidate_id, decision,
                  dry_run, audit_sha256, blockers_json, affected_row_counts_json
           FROM idea_data_lifecycle_operation
           WHERE idempotency_key = %s""",
        (idempotency_key,),
    )
    row = cursor.fetchone()
    return row if isinstance(row, Mapping) else None


def _load_candidate_context(cursor: Any, candidate_id: str) -> DataLifecycleCandidateContext:
    cursor.execute(
        """SELECT candidate_json
           FROM idea_candidate_record
           WHERE candidate_id = %s
           FOR UPDATE""",
        (candidate_id,),
    )
    candidate_row = cursor.fetchone()
    if not isinstance(candidate_row, Mapping):
        return DataLifecycleCandidateContext(
            candidate_exists=False,
            candidate_tenant_id=None,
            control=None,
            active_outbox_count=0,
            active_downstream_count=0,
        )
    candidate_json = _json_object(candidate_row["candidate_json"])
    access_scope = candidate_json.get("access_scope")
    tenant_id = access_scope.get("tenant_id") if isinstance(access_scope, dict) else None
    control = _load_control(cursor, candidate_id)
    if tenant_id is None and control is not None:
        effective_state = control.held_from_state or control.state
        if effective_state in {DataLifecycleState.ERASED, DataLifecycleState.PURGED}:
            tenant_id = control.tenant_id
    active_outbox_count, active_downstream_count = _active_delivery_counts(cursor, candidate_id)
    return DataLifecycleCandidateContext(
        candidate_exists=True,
        candidate_tenant_id=str(tenant_id) if tenant_id else None,
        control=control,
        active_outbox_count=active_outbox_count,
        active_downstream_count=active_downstream_count,
    )


def _load_control(cursor: Any, candidate_id: str) -> DataLifecycleControl | None:
    cursor.execute(
        """SELECT candidate_id, tenant_id, policy_ref, state,
                  retention_expires_at_utc, version, updated_at_utc,
                  held_from_state, hold_authority_ref, hold_change_reference,
                  held_at_utc, erased_at_utc, purged_at_utc, tombstone_sha256
           FROM idea_data_lifecycle_control
           WHERE candidate_id = %s""",
        (candidate_id,),
    )
    row = cursor.fetchone()
    return _control_from_row(row) if isinstance(row, Mapping) else None


def _active_delivery_counts(cursor: Any, candidate_id: str) -> tuple[int, int]:
    cursor.execute(
        """SELECT COUNT(*) AS active_count
           FROM idea_outbox_event
           WHERE aggregate_type = 'idea_candidate'
             AND aggregate_id = %s
             AND status <> 'published'""",
        (candidate_id,),
    )
    outbox_count = _count_from_row(cursor.fetchone())
    cursor.execute(
        """SELECT COUNT(*) AS active_count
           FROM idea_downstream_submission submission
           WHERE submission.status IN ('in_flight', 'reconciliation_required')
             AND ((
                 submission.resource_type = 'conversion_intent'
                 AND submission.resource_id IN (
                     SELECT conversion_intent_id FROM idea_conversion_intent
                     WHERE candidate_id = %s
                 )
             ) OR (
                 submission.resource_type = 'report_evidence_pack'
                 AND submission.resource_id IN (
                     SELECT report_evidence_pack_id FROM idea_report_evidence_pack_request
                     WHERE candidate_id = %s
                 )
             ))""",
        (candidate_id, candidate_id),
    )
    return outbox_count, _count_from_row(cursor.fetchone())


def _apply_evaluation(
    cursor: Any,
    *,
    command: DataLifecycleCommand,
    evaluation: DataLifecycleEvaluation,
    evaluated_at_utc: datetime,
) -> DataLifecycleOperationResult:
    control = evaluation.projected_control
    affected: dict[str, int] = {}
    if evaluation.decision is DataLifecycleDecision.NOT_FOUND:
        return _result_without_persisted_audit(command, evaluation)
    if evaluation.decision is DataLifecycleDecision.APPLIED and control is not None:
        control, affected = _apply_controlled_mutation(
            cursor,
            command=command,
            evaluation=evaluation,
            control=control,
        )
    operation_id = _operation_id(command.idempotency_key)
    audit_sha256 = _audit_sha256(command, evaluation, control, affected)
    _insert_operation(
        cursor,
        operation_id=operation_id,
        command=command,
        evaluation=evaluation,
        control=control,
        affected=affected,
        audit_sha256=audit_sha256,
        evaluated_at_utc=evaluated_at_utc,
    )
    return DataLifecycleOperationResult(
        operation_id=operation_id,
        decision=evaluation.decision,
        control=control,
        blockers=evaluation.blockers,
        dry_run=command.dry_run,
        audit_sha256=audit_sha256,
        affected_row_counts=affected,
    )


def _apply_controlled_mutation(
    cursor: Any,
    *,
    command: DataLifecycleCommand,
    evaluation: DataLifecycleEvaluation,
    control: DataLifecycleControl,
) -> tuple[DataLifecycleControl, dict[str, int]]:
    affected: dict[str, int] = {}
    if evaluation.redaction_required:
        tombstone_sha256 = _tombstone_sha256(command)
        control = replace(control, tombstone_sha256=tombstone_sha256)
        affected.update(
            redact_candidate_graph(
                cursor,
                candidate_id=command.candidate_id,
                tenant_id=command.tenant_id,
                tombstone_sha256=tombstone_sha256,
            )
        )
    if evaluation.purge_required:
        affected.update(purge_expired_candidate_payloads(cursor, candidate_id=command.candidate_id))
    _update_control(cursor, control)
    affected["idea_data_lifecycle_control"] = 1
    return control, affected


def _update_control(cursor: Any, control: DataLifecycleControl) -> None:
    cursor.execute(
        """UPDATE idea_data_lifecycle_control
           SET state = %s, version = %s, updated_at_utc = %s,
               held_from_state = %s, hold_authority_ref = %s,
               hold_change_reference = %s, held_at_utc = %s,
               erased_at_utc = %s, purged_at_utc = %s, tombstone_sha256 = %s
           WHERE candidate_id = %s AND tenant_id = %s""",
        (
            control.state.value,
            control.version,
            control.updated_at_utc,
            control.held_from_state.value if control.held_from_state is not None else None,
            control.hold_authority_ref,
            control.hold_change_reference,
            control.held_at_utc,
            control.erased_at_utc,
            control.purged_at_utc,
            control.tombstone_sha256,
            control.candidate_id,
            control.tenant_id,
        ),
    )
    if int(getattr(cursor, "rowcount", 0)) != 1:
        raise RuntimeError("data lifecycle control update lost tenant-scoped aggregate lock")


def _insert_operation(
    cursor: Any,
    *,
    operation_id: str,
    command: DataLifecycleCommand,
    evaluation: DataLifecycleEvaluation,
    control: DataLifecycleControl | None,
    affected: Mapping[str, int],
    audit_sha256: str,
    evaluated_at_utc: datetime,
) -> None:
    actor_subject = command.actor_subject
    approver_subject = command.approver_subject
    if control is not None and (
        control.state in {DataLifecycleState.ERASED, DataLifecycleState.PURGED}
        or control.held_from_state in {DataLifecycleState.ERASED, DataLifecycleState.PURGED}
    ):
        actor_subject = data_lifecycle_actor_tombstone(command.candidate_id, command.tenant_id)
        approver_subject = actor_subject if approver_subject is not None else None
    cursor.execute(
        """INSERT INTO idea_data_lifecycle_operation (
               operation_id, idempotency_key, request_fingerprint, candidate_id,
               tenant_id, action, decision, dry_run, actor_subject,
               approver_subject, authority_ref, reason, change_reference,
               blockers_json, affected_row_counts_json, audit_sha256,
               requested_at_utc, evaluated_at_utc, control_version
           ) VALUES (
               %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s, %s, %s, %s, %s, %s
           )""",
        (
            operation_id,
            command.idempotency_key,
            command.request_fingerprint,
            command.candidate_id,
            command.tenant_id,
            command.action.value,
            evaluation.decision.value,
            command.dry_run,
            actor_subject,
            approver_subject,
            command.authority_ref,
            command.reason,
            command.change_reference,
            Jsonb([blocker.value for blocker in evaluation.blockers]),
            Jsonb(dict(sorted(affected.items()))),
            audit_sha256,
            command.requested_at_utc,
            evaluated_at_utc,
            control.version if control is not None else None,
        ),
    )


def _replay_or_conflict(
    cursor: Any,
    command: DataLifecycleCommand,
    existing: Mapping[str, Any],
) -> DataLifecycleOperationResult:
    control = _load_control(cursor, str(existing["candidate_id"]))
    if str(existing["request_fingerprint"]) == command.request_fingerprint:
        decision = DataLifecycleDecision.REPLAYED
        blockers: tuple[DataLifecycleBlocker, ...] = ()
    else:
        decision = DataLifecycleDecision.CONFLICT
        blockers = (DataLifecycleBlocker.IDEMPOTENCY_CONFLICT,)
    return DataLifecycleOperationResult(
        operation_id=str(existing["operation_id"]),
        decision=decision,
        control=control,
        blockers=blockers,
        dry_run=bool(existing["dry_run"]),
        audit_sha256=str(existing["audit_sha256"]),
        affected_row_counts=_integer_mapping(existing["affected_row_counts_json"]),
    )


def _result_without_persisted_audit(
    command: DataLifecycleCommand,
    evaluation: DataLifecycleEvaluation,
) -> DataLifecycleOperationResult:
    return DataLifecycleOperationResult(
        operation_id=_operation_id(command.idempotency_key),
        decision=evaluation.decision,
        control=None,
        blockers=evaluation.blockers,
        dry_run=command.dry_run,
        audit_sha256=_audit_sha256(command, evaluation, None, {}),
        affected_row_counts={},
    )


def _control_from_row(row: Mapping[str, Any]) -> DataLifecycleControl:
    return DataLifecycleControl(
        candidate_id=str(row["candidate_id"]),
        tenant_id=str(row["tenant_id"]),
        policy_ref=str(row["policy_ref"]),
        state=DataLifecycleState(str(row["state"])),
        retention_expires_at_utc=row["retention_expires_at_utc"],
        version=int(row["version"]),
        updated_at_utc=row["updated_at_utc"],
        held_from_state=(
            DataLifecycleState(str(row["held_from_state"]))
            if row["held_from_state"] is not None
            else None
        ),
        hold_authority_ref=_optional_text(row["hold_authority_ref"]),
        hold_change_reference=_optional_text(row["hold_change_reference"]),
        held_at_utc=row["held_at_utc"],
        erased_at_utc=row["erased_at_utc"],
        purged_at_utc=row["purged_at_utc"],
        tombstone_sha256=_optional_text(row["tombstone_sha256"]),
    )


def _count_from_row(row: Any) -> int:
    return int(row["active_count"]) if isinstance(row, Mapping) else 0


def _json_object(value: Any) -> dict[str, Any]:
    if hasattr(value, "obj"):
        value = value.obj
    return value if isinstance(value, dict) else {}


def _integer_mapping(value: Any) -> dict[str, int]:
    payload = _json_object(value)
    return {str(key): int(count) for key, count in payload.items()}


def _optional_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def _operation_id(idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"lifecycle-operation-{digest}"


def _tombstone_sha256(command: DataLifecycleCommand) -> str:
    value = ":".join(
        (
            command.tenant_id,
            command.candidate_id,
            command.authority_ref,
            command.change_reference,
        )
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _audit_sha256(
    command: DataLifecycleCommand,
    evaluation: DataLifecycleEvaluation,
    control: DataLifecycleControl | None,
    affected: Mapping[str, int],
) -> str:
    payload = {
        "action": command.action.value,
        "authority_ref": command.authority_ref,
        "blockers": [blocker.value for blocker in evaluation.blockers],
        "candidate_id": command.candidate_id,
        "change_reference": command.change_reference,
        "control_version": control.version if control is not None else None,
        "decision": evaluation.decision.value,
        "dry_run": command.dry_run,
        "request_fingerprint": command.request_fingerprint,
        "tenant_id": command.tenant_id,
        "affected_row_counts": dict(sorted(affected.items())),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
