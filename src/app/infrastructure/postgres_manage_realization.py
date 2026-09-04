from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from psycopg.types.json import Jsonb

from app.domain import (
    ManageActionRealizationEvent,
    ManageActionRealizationEventType,
    ManageActionRealizationHistory,
    ManageActionRealizationStatus,
    ManageRealizationHistoryMutationDecision,
    ManageRealizationHistoryMutationResult,
    evaluate_manage_realization_history_mutation,
)
from app.domain.persistence_manage_realization import (
    manage_realization_submission_blocker,
)
from app.infrastructure.postgres_codecs import decode_datetime, read_row_value
from app.infrastructure.postgres_downstream_submission import (
    DOWNSTREAM_SUBMISSION_COLUMNS,
    downstream_submission_from_row,
)
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor


def load_postgres_manage_realization_history(
    connection: PostgresConnection,
    support_reference: str,
) -> ManageActionRealizationHistory | None:
    with connection.cursor() as cursor:
        return _load_manage_history(cursor, support_reference, for_update=False)


def persist_postgres_manage_realization_history(
    connection: PostgresConnection,
    *,
    support_reference: str,
    history: ManageActionRealizationHistory,
    persisted_at_utc: datetime,
) -> ManageRealizationHistoryMutationResult:
    try:
        with connection.cursor() as cursor:
            submission = _load_manage_submission_for_update(cursor, support_reference)
            if submission is None:
                connection.commit()
                return ManageRealizationHistoryMutationResult(
                    decision=ManageRealizationHistoryMutationDecision.NOT_FOUND,
                    history=None,
                    blocker="downstream_submission_not_found",
                )
            blocker = manage_realization_submission_blocker(submission, history)
            existing = _load_manage_history(cursor, support_reference, for_update=True)
            if blocker is not None:
                connection.commit()
                return ManageRealizationHistoryMutationResult(
                    decision=ManageRealizationHistoryMutationDecision.CONFLICT,
                    history=existing,
                    blocker=blocker,
                )
            decision = evaluate_manage_realization_history_mutation(existing, history)
            if decision is ManageRealizationHistoryMutationDecision.CONFLICT:
                connection.commit()
                return ManageRealizationHistoryMutationResult(
                    decision=decision,
                    history=existing,
                    blocker="manage_realization_history_conflict",
                )
            if decision is ManageRealizationHistoryMutationDecision.REPLAYED:
                connection.commit()
                return ManageRealizationHistoryMutationResult(
                    decision=decision,
                    history=existing,
                )
            _store_manage_history(
                cursor,
                support_reference=support_reference,
                history=history,
                persisted_at_utc=persisted_at_utc,
            )
        connection.commit()
        return ManageRealizationHistoryMutationResult(decision=decision, history=history)
    except Exception:
        connection.rollback()
        raise


def _load_manage_submission_for_update(cursor: PostgresCursor, support_reference: str) -> Any:
    cursor.execute(
        f"""
        /* lotus-idea manage-realization-submission-lock */
        SELECT {DOWNSTREAM_SUBMISSION_COLUMNS}
        FROM idea_downstream_submission
        WHERE support_reference = %s
        FOR UPDATE
        """,
        (support_reference,),
    )
    rows = cursor.fetchall()
    return downstream_submission_from_row(rows[0]) if rows else None


def _load_manage_history(
    cursor: PostgresCursor,
    support_reference: str,
    *,
    for_update: bool,
) -> ManageActionRealizationHistory | None:
    lock = "FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        /* lotus-idea manage-realization-history-load */
        SELECT history_json
        FROM idea_manage_realization_history
        WHERE support_reference = %s
        {lock}
        """,
        (support_reference,),
    )
    rows = cursor.fetchall()
    return _history_from_json(read_row_value(rows[0], "history_json")) if rows else None


def _store_manage_history(
    cursor: PostgresCursor,
    *,
    support_reference: str,
    history: ManageActionRealizationHistory,
    persisted_at_utc: datetime,
) -> None:
    cursor.execute(
        """
        /* lotus-idea manage-realization-history-store */
        INSERT INTO idea_manage_realization_history (
            support_reference, management_action_id, intake_id,
            current_source_event_version, history_json, persisted_at_utc
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (support_reference) DO UPDATE
        SET current_source_event_version = EXCLUDED.current_source_event_version,
            history_json = EXCLUDED.history_json,
            persisted_at_utc = EXCLUDED.persisted_at_utc
        WHERE idea_manage_realization_history.management_action_id
              = EXCLUDED.management_action_id
          AND idea_manage_realization_history.intake_id = EXCLUDED.intake_id
          AND idea_manage_realization_history.current_source_event_version
              < EXCLUDED.current_source_event_version
        RETURNING history_json
        """,
        (
            support_reference,
            history.management_action_id,
            history.intake_id,
            history.source_event_version,
            Jsonb(_history_to_json(history)),
            persisted_at_utc,
        ),
    )
    if not cursor.fetchall():
        raise RuntimeError("Manage realization history compare-and-set failed")


def _history_to_json(history: ManageActionRealizationHistory) -> dict[str, Any]:
    return {
        "contract_version": history.contract_version,
        "intake_id": history.intake_id,
        "management_action_id": history.management_action_id,
        "source_authority": history.source_authority,
        "portfolio_id": history.portfolio_id,
        "idea_candidate_id": history.idea_candidate_id,
        "conversion_intent_id": history.conversion_intent_id,
        "status": history.status.value,
        "source_event_version": history.source_event_version,
        "rebalance_execution_proven": history.rebalance_execution_proven,
        "order_execution_proven": history.order_execution_proven,
        "client_publication_proven": history.client_publication_proven,
        "events": [_event_to_json(event) for event in history.events],
    }


def _event_to_json(event: ManageActionRealizationEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "action_id": event.action_id,
        "source_event_version": event.source_event_version,
        "event_type": event.event_type.value,
        "previous_status": (
            event.previous_status.value if event.previous_status is not None else None
        ),
        "status": event.status.value,
        "occurred_at": event.occurred_at_utc.isoformat(),
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "reason_code": event.reason_code,
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
    }


def _history_from_json(value: Any) -> ManageActionRealizationHistory:
    payload = _mapping(value, "history_json")
    events = payload.get("events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        raise ValueError("history_json events must be an array")
    return ManageActionRealizationHistory(
        contract_version=_text(payload, "contract_version"),
        intake_id=_text(payload, "intake_id"),
        management_action_id=_text(payload, "management_action_id"),
        source_authority=_text(payload, "source_authority"),
        portfolio_id=_text(payload, "portfolio_id"),
        idea_candidate_id=_text(payload, "idea_candidate_id"),
        conversion_intent_id=_text(payload, "conversion_intent_id"),
        status=ManageActionRealizationStatus(_text(payload, "status")),
        source_event_version=_positive_int(payload, "source_event_version"),
        rebalance_execution_proven=_bool(payload, "rebalance_execution_proven"),
        order_execution_proven=_bool(payload, "order_execution_proven"),
        client_publication_proven=_bool(payload, "client_publication_proven"),
        events=tuple(_event_from_json(event) for event in events),
    )


def _event_from_json(value: Any) -> ManageActionRealizationEvent:
    payload = _mapping(value, "event")
    previous_status = _optional_text(payload, "previous_status")
    return ManageActionRealizationEvent(
        event_id=_text(payload, "event_id"),
        action_id=_text(payload, "action_id"),
        source_event_version=_positive_int(payload, "source_event_version"),
        event_type=ManageActionRealizationEventType(_text(payload, "event_type")),
        previous_status=(
            ManageActionRealizationStatus(previous_status) if previous_status is not None else None
        ),
        status=ManageActionRealizationStatus(_text(payload, "status")),
        occurred_at_utc=decode_datetime(payload.get("occurred_at")),
        actor_id=_text(payload, "actor_id"),
        actor_role=_text(payload, "actor_role"),
        reason_code=_text(payload, "reason_code"),
        correlation_id=_text(payload, "correlation_id"),
        causation_id=_text(payload, "causation_id"),
    )


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _text(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _optional_text(payload: Mapping[str, Any], field_name: str) -> str | None:
    return None if payload.get(field_name) is None else _text(payload, field_name)


def _positive_int(payload: Mapping[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _bool(payload: Mapping[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value
