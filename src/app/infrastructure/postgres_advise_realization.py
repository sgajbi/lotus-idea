from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from psycopg.types.json import Jsonb

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    AdviseRealizationHistoryMutationDecision,
    AdviseRealizationHistoryMutationResult,
    evaluate_advise_realization_history_mutation,
)
from app.domain.persistence_advise_realization import (
    advise_realization_submission_blocker,
)
from app.infrastructure.postgres_codecs import decode_datetime, read_row_value
from app.infrastructure.postgres_downstream_submission import (
    DOWNSTREAM_SUBMISSION_COLUMNS,
    downstream_submission_from_row,
)
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor


def load_postgres_advise_realization_history(
    connection: PostgresConnection,
    support_reference: str,
) -> AdviseProposalRealizationHistory | None:
    with connection.cursor() as cursor:
        return _load_history(cursor, support_reference, for_update=False)


def persist_postgres_advise_realization_history(
    connection: PostgresConnection,
    *,
    support_reference: str,
    history: AdviseProposalRealizationHistory,
    persisted_at_utc: datetime,
) -> AdviseRealizationHistoryMutationResult:
    try:
        with connection.cursor() as cursor:
            submission = _load_submission_for_update(cursor, support_reference)
            if submission is None:
                connection.commit()
                return AdviseRealizationHistoryMutationResult(
                    decision=AdviseRealizationHistoryMutationDecision.NOT_FOUND,
                    history=None,
                    blocker="downstream_submission_not_found",
                )
            blocker = advise_realization_submission_blocker(submission, history)
            existing = _load_history(cursor, support_reference, for_update=True)
            if blocker is not None:
                connection.commit()
                return AdviseRealizationHistoryMutationResult(
                    decision=AdviseRealizationHistoryMutationDecision.CONFLICT,
                    history=existing,
                    blocker=blocker,
                )
            decision = evaluate_advise_realization_history_mutation(existing, history)
            if decision is AdviseRealizationHistoryMutationDecision.CONFLICT:
                connection.commit()
                return AdviseRealizationHistoryMutationResult(
                    decision=decision,
                    history=existing,
                    blocker="advise_realization_history_conflict",
                )
            if decision is AdviseRealizationHistoryMutationDecision.REPLAYED:
                connection.commit()
                return AdviseRealizationHistoryMutationResult(
                    decision=decision,
                    history=existing,
                )
            _store_history(
                cursor,
                support_reference=support_reference,
                history=history,
                persisted_at_utc=persisted_at_utc,
            )
        connection.commit()
        return AdviseRealizationHistoryMutationResult(decision=decision, history=history)
    except Exception:
        connection.rollback()
        raise


def _load_submission_for_update(cursor: PostgresCursor, support_reference: str) -> Any:
    cursor.execute(
        f"""
        /* lotus-idea advise-realization-submission-lock */
        SELECT {DOWNSTREAM_SUBMISSION_COLUMNS}
        FROM idea_downstream_submission
        WHERE support_reference = %s
        FOR UPDATE
        """,
        (support_reference,),
    )
    rows = cursor.fetchall()
    return downstream_submission_from_row(rows[0]) if rows else None


def _load_history(
    cursor: PostgresCursor,
    support_reference: str,
    *,
    for_update: bool,
) -> AdviseProposalRealizationHistory | None:
    lock = "FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        /* lotus-idea advise-realization-history-load */
        SELECT history_json
        FROM idea_advise_realization_history
        WHERE support_reference = %s
        {lock}
        """,
        (support_reference,),
    )
    rows = cursor.fetchall()
    return _history_from_json(read_row_value(rows[0], "history_json")) if rows else None


def _store_history(
    cursor: PostgresCursor,
    *,
    support_reference: str,
    history: AdviseProposalRealizationHistory,
    persisted_at_utc: datetime,
) -> None:
    cursor.execute(
        """
        /* lotus-idea advise-realization-history-store */
        INSERT INTO idea_advise_realization_history (
            support_reference, realization_id, intake_id,
            current_source_event_version, history_json, persisted_at_utc
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (support_reference) DO UPDATE
        SET current_source_event_version = EXCLUDED.current_source_event_version,
            history_json = EXCLUDED.history_json,
            persisted_at_utc = EXCLUDED.persisted_at_utc
        WHERE idea_advise_realization_history.realization_id = EXCLUDED.realization_id
          AND idea_advise_realization_history.intake_id = EXCLUDED.intake_id
          AND idea_advise_realization_history.current_source_event_version
              < EXCLUDED.current_source_event_version
        RETURNING history_json
        """,
        (
            support_reference,
            history.realization_id,
            history.intake_id,
            history.current_source_event_version,
            Jsonb(_history_to_json(history)),
            persisted_at_utc,
        ),
    )
    if not cursor.fetchall():
        raise RuntimeError("Advise realization history compare-and-set failed")


def _history_to_json(history: AdviseProposalRealizationHistory) -> dict[str, Any]:
    return {
        "realization_id": history.realization_id,
        "intake_id": history.intake_id,
        "review_work_id": history.review_work_id,
        "review_work_status": (
            history.review_work_status.value if history.review_work_status else None
        ),
        "source_authority": history.source_authority,
        "realization_authority": history.realization_authority,
        "tenant_id": history.tenant_id,
        "legal_entity_code": history.legal_entity_code,
        "portfolio_id": history.portfolio_id,
        "idea_candidate_id": history.idea_candidate_id,
        "conversion_intent_id": history.conversion_intent_id,
        "source_evidence_fingerprint": history.source_evidence_fingerprint,
        "current_status": history.current_status.value,
        "current_source_event_version": history.current_source_event_version,
        "proposal_id": history.proposal_id,
        "proposal_record_created": history.proposal_record_created,
        "suitability_authority_granted": history.suitability_authority_granted,
        "order_created": history.order_created,
        "client_publication_authorized": history.client_publication_authorized,
        "created_at": history.created_at_utc.isoformat(),
        "updated_at": history.updated_at_utc.isoformat(),
        "outcomes": [_outcome_to_json(outcome) for outcome in history.outcomes],
    }


def _outcome_to_json(outcome: AdviseProposalRealizationOutcome) -> dict[str, Any]:
    return {
        "outcome_id": outcome.outcome_id,
        "source_event_version": outcome.source_event_version,
        "status": outcome.status.value,
        "reason_code": outcome.reason_code,
        "occurred_at": outcome.occurred_at_utc.isoformat(),
        "review_work_id": outcome.review_work_id,
        "proposal_id": outcome.proposal_id,
        "terminal": outcome.terminal,
    }


def _history_from_json(value: Any) -> AdviseProposalRealizationHistory:
    payload = _mapping(value, "history_json")
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes, bytearray)):
        raise ValueError("history_json outcomes must be an array")
    review_status = _optional_text(payload, "review_work_status")
    return AdviseProposalRealizationHistory(
        realization_id=_text(payload, "realization_id"),
        intake_id=_text(payload, "intake_id"),
        review_work_id=_optional_text(payload, "review_work_id"),
        review_work_status=(AdviseProposalReviewWorkStatus(review_status) if review_status else None),
        source_authority=_text(payload, "source_authority"),
        realization_authority=_text(payload, "realization_authority"),
        tenant_id=_text(payload, "tenant_id"),
        legal_entity_code=_text(payload, "legal_entity_code"),
        portfolio_id=_text(payload, "portfolio_id"),
        idea_candidate_id=_text(payload, "idea_candidate_id"),
        conversion_intent_id=_text(payload, "conversion_intent_id"),
        source_evidence_fingerprint=_text(payload, "source_evidence_fingerprint"),
        current_status=AdviseProposalRealizationStatus(_text(payload, "current_status")),
        current_source_event_version=_positive_int(payload, "current_source_event_version"),
        proposal_id=_optional_text(payload, "proposal_id"),
        proposal_record_created=_bool(payload, "proposal_record_created"),
        suitability_authority_granted=_bool(payload, "suitability_authority_granted"),
        order_created=_bool(payload, "order_created"),
        client_publication_authorized=_bool(payload, "client_publication_authorized"),
        created_at_utc=decode_datetime(payload.get("created_at")),
        updated_at_utc=decode_datetime(payload.get("updated_at")),
        outcomes=tuple(_outcome_from_json(outcome) for outcome in outcomes),
    )


def _outcome_from_json(value: Any) -> AdviseProposalRealizationOutcome:
    payload = _mapping(value, "outcome")
    return AdviseProposalRealizationOutcome(
        outcome_id=_text(payload, "outcome_id"),
        source_event_version=_positive_int(payload, "source_event_version"),
        status=AdviseProposalRealizationStatus(_text(payload, "status")),
        reason_code=_text(payload, "reason_code"),
        occurred_at_utc=decode_datetime(payload.get("occurred_at")),
        review_work_id=_optional_text(payload, "review_work_id"),
        proposal_id=_optional_text(payload, "proposal_id"),
        terminal=_bool(payload, "terminal"),
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
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-blank when present")
    return value


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
