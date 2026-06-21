from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol, Sequence, TypeVar

from psycopg.types.json import Jsonb

from app.domain.audit import AuditEvent
from app.domain.conversion_governance import (
    ConversionBoundary,
    ConversionIntentResult,
    ConversionOutcomeResult,
    GovernedConversionIntent,
    GovernedConversionOutcome,
)
from app.domain.ideas import (
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaConversionIntent,
    IdeaConversionOutcome,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
)
from app.domain.idempotency import IdempotencyRecord
from app.domain.persistence import (
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    ConversionPersistenceResult,
    EvidencePackPersistenceResult,
    EvidenceReplayResult,
    InMemoryIdeaRepository,
    IdeaRepositorySnapshot,
    LifecycleHistoryEntry,
    LifecyclePersistenceResult,
    ReviewPersistenceResult,
)
from app.domain.report_evidence import (
    GovernedReportEvidencePack,
    ReportEvidencePackBoundary,
    ReportEvidencePackPurpose,
    ReportEvidencePackResult,
    ReportEvidenceSourceSummary,
)
from app.domain.review_governance import (
    FeedbackResult,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewAction,
    ReviewActionResult,
    ReviewActorRole,
)


class PostgresCursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...

    def fetchall(self) -> Sequence[Any]: ...

    def __enter__(self) -> PostgresCursor: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class PostgresConnection(Protocol):
    def cursor(self) -> PostgresCursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


_T = TypeVar("_T")


class PostgresIdeaRepository:
    """PostgreSQL-backed implementation of the governed idea repository ports."""

    durable_storage_backed = True

    def __init__(self, connection: PostgresConnection) -> None:
        self._connection = connection

    def persist_candidate(
        self,
        candidate: IdeaCandidate,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
    ) -> CandidatePersistenceResult:
        return self._mutate(
            lambda repository: repository.persist_candidate(
                candidate,
                idempotency_key=idempotency_key,
                payload=payload,
                actor_subject=actor_subject,
                occurred_at_utc=occurred_at_utc,
            )
        )

    def record_lifecycle_transition(
        self,
        candidate_id: str,
        target_status: IdeaLifecycleStatus,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
        transition_id: str | None = None,
        reason_codes: tuple[str, ...] = (),
    ) -> LifecyclePersistenceResult:
        return self._mutate(
            lambda repository: repository.record_lifecycle_transition(
                candidate_id,
                target_status,
                idempotency_key=idempotency_key,
                payload=payload,
                actor_subject=actor_subject,
                occurred_at_utc=occurred_at_utc,
                transition_id=transition_id,
                reason_codes=reason_codes,
            )
        )

    def replay_evidence(
        self,
        candidate_id: str,
        *,
        current_source_refs: tuple[SourceRef, ...],
        evaluated_at_utc: datetime | None = None,
    ) -> EvidenceReplayResult:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.replay_evidence(
            candidate_id,
            current_source_refs=current_source_refs,
            evaluated_at_utc=evaluated_at_utc,
        )

    def precheck_review_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult | None:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.precheck_review_mutation(
            idempotency_key=idempotency_key,
            payload=payload,
        )

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult:
        return self._mutate(
            lambda repository: repository.record_review_action(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    def record_feedback_event(
        self,
        result: FeedbackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ReviewPersistenceResult:
        return self._mutate(
            lambda repository: repository.record_feedback_event(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    def precheck_conversion_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult | None:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.precheck_conversion_mutation(
            idempotency_key=idempotency_key,
            payload=payload,
        )

    def record_conversion_intent(
        self,
        result: ConversionIntentResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult:
        return self._mutate(
            lambda repository: repository.record_conversion_intent(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.conversion_intent_by_id(conversion_intent_id)

    def record_conversion_outcome(
        self,
        result: ConversionOutcomeResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult:
        return self._mutate(
            lambda repository: repository.record_conversion_outcome(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    def precheck_evidence_pack_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> EvidencePackPersistenceResult | None:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.precheck_evidence_pack_mutation(
            idempotency_key=idempotency_key,
            payload=payload,
        )

    def candidate_record_for_conversion_intent(
        self,
        conversion_intent_id: str,
    ) -> CandidatePersistenceRecord | None:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.candidate_record_for_conversion_intent(conversion_intent_id)

    def record_report_evidence_pack(
        self,
        result: ReportEvidencePackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> EvidencePackPersistenceResult:
        return self._mutate(
            lambda repository: repository.record_report_evidence_pack(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    def snapshot(self) -> IdeaRepositorySnapshot:
        with self._connection.cursor() as cursor:
            candidate_records = self._load_candidate_records(cursor)
            idempotency_records, idempotency_candidates = self._load_idempotency(cursor)
            self._attach_lifecycle_history(cursor, candidate_records)
            self._attach_audit_events(cursor, candidate_records)
            self._attach_review_decisions(cursor, candidate_records)
            self._attach_feedback_events(cursor, candidate_records)
            conversion_intent_candidates = self._attach_conversion_intents(
                cursor,
                candidate_records,
            )
            self._attach_conversion_outcomes(cursor, candidate_records)
            report_evidence_pack_candidates = self._attach_report_evidence_packs(
                cursor,
                candidate_records,
            )
        return IdeaRepositorySnapshot(
            candidate_records=candidate_records,
            idempotency_records=idempotency_records,
            idempotency_candidates=idempotency_candidates,
            conversion_intent_candidates=conversion_intent_candidates,
            report_evidence_pack_candidates=report_evidence_pack_candidates,
        )

    def replace_snapshot(self, snapshot: IdeaRepositorySnapshot) -> None:
        with self._connection.cursor() as cursor:
            for table_name in (
                "idea_report_evidence_pack_request",
                "idea_conversion_outcome",
                "idea_conversion_intent",
                "idea_feedback_event",
                "idea_review_decision",
                "idea_audit_event",
                "idea_lifecycle_history",
                "idea_idempotency_record",
                "idea_candidate_record",
            ):
                cursor.execute(f"DELETE FROM {table_name}")
            for candidate_record in snapshot.candidate_records.values():
                self._insert_candidate_record(cursor, candidate_record)
            for key, idempotency_record in snapshot.idempotency_records.items():
                self._insert_idempotency_record(
                    cursor,
                    idempotency_record,
                    candidate_id=snapshot.idempotency_candidates.get(key),
                    snapshot=snapshot,
                )
            for candidate_record in snapshot.candidate_records.values():
                self._insert_record_details(cursor, candidate_record)

    def _mutate(self, operation: Callable[[InMemoryIdeaRepository], _T]) -> _T:
        try:
            repository = InMemoryIdeaRepository(self.snapshot())
            result = operation(repository)
            self.replace_snapshot(repository.snapshot())
            self._connection.commit()
            return result
        except Exception:
            self._connection.rollback()
            raise

    def _load_candidate_records(
        self,
        cursor: PostgresCursor,
    ) -> dict[str, CandidatePersistenceRecord]:
        cursor.execute(
            """
            SELECT candidate_id, evidence_hash, candidate_json, persisted_at_utc
            FROM idea_candidate_record
            ORDER BY persisted_at_utc, candidate_id
            """
        )
        records: dict[str, CandidatePersistenceRecord] = {}
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            records[candidate_id] = CandidatePersistenceRecord(
                candidate=_candidate_from_json(_json(row, "candidate_json")),
                evidence_hash=_row(row, "evidence_hash"),
                persisted_at_utc=_row(row, "persisted_at_utc"),
            )
        return records

    def _load_idempotency(
        self,
        cursor: PostgresCursor,
    ) -> tuple[dict[str, IdempotencyRecord], dict[str, str]]:
        cursor.execute(
            """
            SELECT idempotency_key, payload_hash, candidate_id
            FROM idea_idempotency_record
            ORDER BY created_at_utc, idempotency_key
            """
        )
        records: dict[str, IdempotencyRecord] = {}
        candidates: dict[str, str] = {}
        for row in cursor.fetchall():
            key = _row(row, "idempotency_key")
            records[key] = IdempotencyRecord(
                key=key,
                payload_hash=_row(row, "payload_hash"),
            )
            candidate_id = _row(row, "candidate_id")
            if candidate_id is not None:
                candidates[key] = candidate_id
        return records, candidates

    def _attach_lifecycle_history(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> None:
        cursor.execute(
            """
            SELECT candidate_id, source_status, target_status, actor_subject, changed_at_utc
            FROM idea_lifecycle_history
            ORDER BY changed_at_utc, lifecycle_history_id
            """
        )
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            entry = LifecycleHistoryEntry(
                candidate_id=candidate_id,
                source_status=IdeaLifecycleStatus(_row(row, "source_status")),
                target_status=IdeaLifecycleStatus(_row(row, "target_status")),
                actor_subject=_row(row, "actor_subject"),
                changed_at_utc=_row(row, "changed_at_utc"),
            )
            records[candidate_id] = replace(
                record,
                lifecycle_history=(*record.lifecycle_history, entry),
            )

    def _attach_audit_events(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> None:
        cursor.execute(
            """
            SELECT candidate_id, event_type, actor_subject, outcome, attributes_json,
                   occurred_at_utc
            FROM idea_audit_event
            ORDER BY occurred_at_utc, audit_event_id
            """
        )
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            if candidate_id is None or candidate_id not in records:
                continue
            record = records[candidate_id]
            event = AuditEvent(
                event_type=_row(row, "event_type"),
                actor_subject=_row(row, "actor_subject"),
                outcome=_row(row, "outcome"),
                attributes=_json(row, "attributes_json"),
                occurred_at_utc=_row(row, "occurred_at_utc"),
            )
            records[candidate_id] = replace(
                record,
                audit_events=(*record.audit_events, event),
            )

    def _attach_review_decisions(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> None:
        cursor.execute(
            """
            SELECT candidate_id, decision_json
            FROM idea_review_decision
            ORDER BY decided_at_utc, review_decision_id
            """
        )
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            decision = _review_decision_from_json(_json(row, "decision_json"))
            records[candidate_id] = replace(
                record,
                review_decisions=(*record.review_decisions, decision),
            )

    def _attach_feedback_events(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> None:
        cursor.execute(
            """
            SELECT candidate_id, feedback_json
            FROM idea_feedback_event
            ORDER BY recorded_at_utc, feedback_event_id
            """
        )
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            feedback = _feedback_event_from_json(_json(row, "feedback_json"))
            records[candidate_id] = replace(
                record,
                feedback_events=(*record.feedback_events, feedback),
            )

    def _attach_conversion_intents(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> dict[str, str]:
        cursor.execute(
            """
            SELECT conversion_intent_id, candidate_id, intent_json
            FROM idea_conversion_intent
            ORDER BY requested_at_utc, conversion_intent_id
            """
        )
        candidates: dict[str, str] = {}
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            intent_id = _row(row, "conversion_intent_id")
            intent = _conversion_intent_from_json(_json(row, "intent_json"))
            records[candidate_id] = replace(
                record,
                conversion_intents=(*record.conversion_intents, intent),
            )
            candidates[intent_id] = candidate_id
        return candidates

    def _attach_conversion_outcomes(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> None:
        cursor.execute(
            """
            SELECT conversion_intent_id, outcome_json
            FROM idea_conversion_outcome
            ORDER BY recorded_at_utc, conversion_outcome_id
            """
        )
        intent_candidates = {
            intent.intent.conversion_intent_id: candidate_id
            for candidate_id, record in records.items()
            for intent in record.conversion_intents
        }
        for row in cursor.fetchall():
            candidate_id = intent_candidates.get(_row(row, "conversion_intent_id"))
            if candidate_id is None:
                continue
            record = records[candidate_id]
            outcome = _conversion_outcome_from_json(_json(row, "outcome_json"))
            records[candidate_id] = replace(
                record,
                conversion_outcomes=(*record.conversion_outcomes, outcome),
            )

    def _attach_report_evidence_packs(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> dict[str, str]:
        cursor.execute(
            """
            SELECT report_evidence_pack_id, candidate_id, evidence_pack_json
            FROM idea_report_evidence_pack_request
            ORDER BY requested_at_utc, report_evidence_pack_id
            """
        )
        candidates: dict[str, str] = {}
        for row in cursor.fetchall():
            candidate_id = _row(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            pack_id = _row(row, "report_evidence_pack_id")
            evidence_pack = _report_evidence_pack_from_json(_json(row, "evidence_pack_json"))
            records[candidate_id] = replace(
                record,
                report_evidence_packs=(*record.report_evidence_packs, evidence_pack),
            )
            candidates[pack_id] = candidate_id
        return candidates

    def _insert_candidate_record(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate = record.candidate
        cursor.execute(
            """
            INSERT INTO idea_candidate_record (
                candidate_id, family, lifecycle_status, review_posture,
                evidence_packet_id, evidence_hash, candidate_json,
                persisted_at_utc, updated_at_utc
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                candidate.candidate_id,
                candidate.family.value,
                candidate.lifecycle_status.value,
                candidate.review_posture.value,
                candidate.evidence_packet.evidence_packet_id,
                record.evidence_hash,
                Jsonb(_candidate_to_json(candidate)),
                record.persisted_at_utc,
                candidate.updated_at_utc,
            ),
        )

    def _insert_idempotency_record(
        self,
        cursor: PostgresCursor,
        record: IdempotencyRecord,
        *,
        candidate_id: str | None,
        snapshot: IdeaRepositorySnapshot,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO idea_idempotency_record (
                idempotency_key, operation_name, payload_hash, candidate_id,
                created_at_utc
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                record.key,
                _operation_name(record.key),
                record.payload_hash,
                candidate_id,
                _idempotency_created_at(candidate_id, snapshot),
            ),
        )

    def _insert_record_details(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for index, entry in enumerate(record.lifecycle_history, start=1):
            cursor.execute(
                """
                INSERT INTO idea_lifecycle_history (
                    lifecycle_history_id, candidate_id, source_status, target_status,
                    actor_subject, changed_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    f"{candidate_id}:lifecycle:{index}",
                    candidate_id,
                    entry.source_status.value,
                    entry.target_status.value,
                    entry.actor_subject,
                    entry.changed_at_utc,
                ),
            )
        for index, event in enumerate(record.audit_events, start=1):
            cursor.execute(
                """
                INSERT INTO idea_audit_event (
                    audit_event_id, candidate_id, event_type, actor_subject, outcome,
                    attributes_json, occurred_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f"{candidate_id}:audit:{index}",
                    candidate_id,
                    event.event_type,
                    event.actor_subject,
                    event.outcome,
                    Jsonb(dict(event.attributes)),
                    event.occurred_at_utc,
                ),
            )
        for decision in record.review_decisions:
            cursor.execute(
                """
                INSERT INTO idea_review_decision (
                    review_decision_id, candidate_id, action, actor_subject,
                    decision_json, decided_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    decision.review_id,
                    candidate_id,
                    decision.action.value,
                    decision.actor_subject,
                    Jsonb(_review_decision_to_json(decision)),
                    decision.decided_at_utc,
                ),
            )
        for feedback in record.feedback_events:
            cursor.execute(
                """
                INSERT INTO idea_feedback_event (
                    feedback_event_id, candidate_id, actor_subject, feedback_json,
                    recorded_at_utc
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    feedback.feedback.feedback_id,
                    candidate_id,
                    feedback.actor_subject,
                    Jsonb(_feedback_event_to_json(feedback)),
                    feedback.feedback.recorded_at_utc,
                ),
            )
        for intent in record.conversion_intents:
            cursor.execute(
                """
                INSERT INTO idea_conversion_intent (
                    conversion_intent_id, candidate_id, target, actor_subject,
                    intent_json, requested_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    intent.intent.conversion_intent_id,
                    candidate_id,
                    intent.intent.target.value,
                    intent.actor_subject,
                    Jsonb(_conversion_intent_to_json(intent)),
                    intent.intent.requested_at_utc,
                ),
            )
        for outcome in record.conversion_outcomes:
            cursor.execute(
                """
                INSERT INTO idea_conversion_outcome (
                    conversion_outcome_id, conversion_intent_id, source_system,
                    status, outcome_json, recorded_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    outcome.outcome.conversion_outcome_id,
                    outcome.conversion_intent_id,
                    outcome.source_system.value,
                    outcome.outcome.status.value,
                    Jsonb(_conversion_outcome_to_json(outcome)),
                    outcome.outcome.recorded_at_utc,
                ),
            )
        for evidence_pack in record.report_evidence_packs:
            cursor.execute(
                """
                INSERT INTO idea_report_evidence_pack_request (
                    report_evidence_pack_id, candidate_id, conversion_intent_id,
                    purpose, evidence_hash, evidence_pack_json, requested_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evidence_pack.report_evidence_pack_id,
                    candidate_id,
                    evidence_pack.conversion_intent_id,
                    evidence_pack.purpose.value,
                    evidence_pack.evidence_content_hash,
                    Jsonb(_report_evidence_pack_to_json(evidence_pack)),
                    evidence_pack.requested_at_utc,
                ),
            )


def _operation_name(idempotency_key: str) -> str:
    return idempotency_key.split(":", 1)[0]


def _idempotency_created_at(
    candidate_id: str | None,
    snapshot: IdeaRepositorySnapshot,
) -> datetime:
    if candidate_id is not None and candidate_id in snapshot.candidate_records:
        return snapshot.candidate_records[candidate_id].persisted_at_utc
    return datetime.now().astimezone()


def _row(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row[key]
    raise TypeError("PostgresIdeaRepository requires mapping rows")


def _json(row: Any, key: str) -> dict[str, Any]:
    value = _row(row, key)
    if hasattr(value, "obj"):
        value = value.obj
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a JSON object")
    return value


def _candidate_to_json(candidate: IdeaCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "family": candidate.family.value,
        "lifecycle_status": candidate.lifecycle_status.value,
        "review_posture": candidate.review_posture.value,
        "evidence_packet": _evidence_packet_to_json(candidate.evidence_packet),
        "source_signal_ids": list(candidate.source_signal_ids),
        "score": _score_to_json(candidate.score) if candidate.score is not None else None,
        "suppression_reason": (
            candidate.suppression_reason.value if candidate.suppression_reason is not None else None
        ),
        "created_at_utc": candidate.created_at_utc.isoformat(),
        "updated_at_utc": candidate.updated_at_utc.isoformat(),
    }


def _candidate_from_json(payload: Mapping[str, Any]) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=str(payload["candidate_id"]),
        family=OpportunityFamily(payload["family"]),
        lifecycle_status=IdeaLifecycleStatus(payload["lifecycle_status"]),
        review_posture=ReviewPosture(payload["review_posture"]),
        evidence_packet=_evidence_packet_from_json(payload["evidence_packet"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        score=(_score_from_json(payload["score"]) if payload.get("score") is not None else None),
        suppression_reason=(
            SuppressionReason(payload["suppression_reason"])
            if payload.get("suppression_reason") is not None
            else None
        ),
        created_at_utc=_datetime(payload["created_at_utc"]),
        updated_at_utc=_datetime(payload["updated_at_utc"]),
    )


def _evidence_packet_to_json(packet: IdeaEvidencePacket) -> dict[str, Any]:
    return {
        "evidence_packet_id": packet.evidence_packet_id,
        "supportability": packet.supportability.value,
        "source_refs": [_source_ref_to_json(source_ref) for source_ref in packet.source_refs],
        "lineage_ref": _lineage_ref_to_json(packet.lineage_ref),
        "reason_codes": [reason.value for reason in packet.reason_codes],
        "unsupported_reasons": [reason.value for reason in packet.unsupported_reasons],
        "created_at_utc": packet.created_at_utc.isoformat(),
    }


def _evidence_packet_from_json(payload: Mapping[str, Any]) -> IdeaEvidencePacket:
    return IdeaEvidencePacket(
        evidence_packet_id=str(payload["evidence_packet_id"]),
        supportability=EvidenceSupportability(payload["supportability"]),
        source_refs=tuple(_source_ref_from_json(item) for item in payload["source_refs"]),
        lineage_ref=_lineage_ref_from_json(payload["lineage_ref"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        unsupported_reasons=tuple(
            UnsupportedEvidenceReason(value) for value in payload["unsupported_reasons"]
        ),
        created_at_utc=_datetime(payload["created_at_utc"]),
    )


def _lineage_ref_to_json(lineage_ref: LineageRef) -> dict[str, Any]:
    return {
        "lineage_id": lineage_ref.lineage_id,
        "source_refs": [_source_ref_to_json(source_ref) for source_ref in lineage_ref.source_refs],
        "content_hash": lineage_ref.content_hash,
    }


def _lineage_ref_from_json(payload: Mapping[str, Any]) -> LineageRef:
    return LineageRef(
        lineage_id=str(payload["lineage_id"]),
        source_refs=tuple(_source_ref_from_json(item) for item in payload["source_refs"]),
        content_hash=str(payload["content_hash"]),
    )


def _source_ref_to_json(source_ref: SourceRef) -> dict[str, Any]:
    return {
        "product_id": source_ref.product_id,
        "source_system": source_ref.source_system.value,
        "product_version": source_ref.product_version,
        "route": source_ref.route,
        "as_of_date": source_ref.as_of_date.isoformat(),
        "generated_at_utc": source_ref.generated_at_utc.isoformat(),
        "content_hash": source_ref.content_hash,
        "data_quality_status": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
    }


def _source_ref_from_json(payload: Mapping[str, Any]) -> SourceRef:
    return SourceRef(
        product_id=str(payload["product_id"]),
        source_system=SourceSystem(payload["source_system"]),
        product_version=str(payload["product_version"]),
        route=str(payload["route"]),
        as_of_date=date.fromisoformat(str(payload["as_of_date"])),
        generated_at_utc=_datetime(payload["generated_at_utc"]),
        content_hash=str(payload["content_hash"]),
        data_quality_status=str(payload["data_quality_status"]),
        freshness=EvidenceFreshness(payload["freshness"]),
    )


def _score_to_json(score: IdeaScore) -> dict[str, Any]:
    return {
        "policy_version": score.policy_version,
        "score": str(score.score),
        "reason_codes": [reason.value for reason in score.reason_codes],
    }


def _score_from_json(payload: Mapping[str, Any]) -> IdeaScore:
    return IdeaScore(
        policy_version=str(payload["policy_version"]),
        score=Decimal(str(payload["score"])),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
    )


def _review_decision_to_json(decision: GovernedReviewDecision) -> dict[str, Any]:
    return {
        "review_id": decision.review_id,
        "candidate_id": decision.candidate_id,
        "evidence_packet_id": decision.evidence_packet_id,
        "evidence_content_hash": decision.evidence_content_hash,
        "action": decision.action.value,
        "resulting_posture": decision.resulting_posture.value,
        "actor_subject": decision.actor_subject,
        "actor_role": decision.actor_role.value,
        "reason_codes": [reason.value for reason in decision.reason_codes],
        "decided_at_utc": decision.decided_at_utc.isoformat(),
        "suppression_reason": (
            decision.suppression_reason.value if decision.suppression_reason is not None else None
        ),
        "snoozed_until_utc": (
            decision.snoozed_until_utc.isoformat()
            if decision.snoozed_until_utc is not None
            else None
        ),
    }


def _review_decision_from_json(payload: Mapping[str, Any]) -> GovernedReviewDecision:
    return GovernedReviewDecision(
        review_id=str(payload["review_id"]),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        action=ReviewAction(payload["action"]),
        resulting_posture=ReviewPosture(payload["resulting_posture"]),
        actor_subject=str(payload["actor_subject"]),
        actor_role=ReviewActorRole(payload["actor_role"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        decided_at_utc=_datetime(payload["decided_at_utc"]),
        suppression_reason=(
            SuppressionReason(payload["suppression_reason"])
            if payload.get("suppression_reason") is not None
            else None
        ),
        snoozed_until_utc=(
            _datetime(payload["snoozed_until_utc"])
            if payload.get("snoozed_until_utc") is not None
            else None
        ),
    )


def _feedback_event_to_json(feedback: GovernedFeedbackEvent) -> dict[str, Any]:
    return {
        "feedback": {
            "feedback_id": feedback.feedback.feedback_id,
            "outcome": feedback.feedback.outcome.value,
            "actor_role": feedback.feedback.actor_role,
            "reason_codes": [reason.value for reason in feedback.feedback.reason_codes],
            "recorded_at_utc": feedback.feedback.recorded_at_utc.isoformat(),
        },
        "candidate_id": feedback.candidate_id,
        "evidence_packet_id": feedback.evidence_packet_id,
        "evidence_content_hash": feedback.evidence_content_hash,
        "source_signal_ids": list(feedback.source_signal_ids),
        "actor_subject": feedback.actor_subject,
        "actor_role": feedback.actor_role.value,
    }


def _feedback_event_from_json(payload: Mapping[str, Any]) -> GovernedFeedbackEvent:
    from app.domain.ideas import FeedbackOutcome, IdeaFeedback

    feedback = payload["feedback"]
    return GovernedFeedbackEvent(
        feedback=IdeaFeedback(
            feedback_id=str(feedback["feedback_id"]),
            outcome=FeedbackOutcome(feedback["outcome"]),
            actor_role=str(feedback["actor_role"]),
            reason_codes=tuple(ReasonCode(value) for value in feedback["reason_codes"]),
            recorded_at_utc=_datetime(feedback["recorded_at_utc"]),
        ),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        actor_subject=str(payload["actor_subject"]),
        actor_role=ReviewActorRole(payload["actor_role"]),
    )


def _conversion_intent_to_json(intent: GovernedConversionIntent) -> dict[str, Any]:
    return {
        "intent": {
            "conversion_intent_id": intent.intent.conversion_intent_id,
            "candidate_id": intent.intent.candidate_id,
            "target": intent.intent.target.value,
            "source_status": intent.intent.source_status.value,
            "requested_at_utc": intent.intent.requested_at_utc.isoformat(),
        },
        "evidence_packet_id": intent.evidence_packet_id,
        "evidence_content_hash": intent.evidence_content_hash,
        "source_signal_ids": list(intent.source_signal_ids),
        "actor_subject": intent.actor_subject,
        "idempotency_key": intent.idempotency_key,
        "reason_codes": [reason.value for reason in intent.reason_codes],
        "target_source_authority": intent.target_source_authority.value,
        "boundary": intent.boundary.value,
    }


def _conversion_intent_from_json(payload: Mapping[str, Any]) -> GovernedConversionIntent:
    intent = payload["intent"]
    return GovernedConversionIntent(
        intent=IdeaConversionIntent(
            conversion_intent_id=str(intent["conversion_intent_id"]),
            candidate_id=str(intent["candidate_id"]),
            target=ConversionTarget(intent["target"]),
            source_status=IdeaLifecycleStatus(intent["source_status"]),
            requested_at_utc=_datetime(intent["requested_at_utc"]),
        ),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        actor_subject=str(payload["actor_subject"]),
        idempotency_key=str(payload["idempotency_key"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        target_source_authority=SourceSystem(payload["target_source_authority"]),
        boundary=ConversionBoundary(payload["boundary"]),
    )


def _conversion_outcome_to_json(outcome: GovernedConversionOutcome) -> dict[str, Any]:
    return {
        "outcome": {
            "conversion_outcome_id": outcome.outcome.conversion_outcome_id,
            "conversion_intent_id": outcome.outcome.conversion_intent_id,
            "status": outcome.outcome.status.value,
            "downstream_reference": outcome.outcome.downstream_reference,
            "recorded_at_utc": outcome.outcome.recorded_at_utc.isoformat(),
        },
        "conversion_intent_id": outcome.conversion_intent_id,
        "target": outcome.target.value,
        "source_system": outcome.source_system.value,
        "boundary": outcome.boundary.value,
    }


def _conversion_outcome_from_json(payload: Mapping[str, Any]) -> GovernedConversionOutcome:
    outcome = payload["outcome"]
    return GovernedConversionOutcome(
        outcome=IdeaConversionOutcome(
            conversion_outcome_id=str(outcome["conversion_outcome_id"]),
            conversion_intent_id=str(outcome["conversion_intent_id"]),
            status=ConversionOutcomeStatus(outcome["status"]),
            downstream_reference=outcome.get("downstream_reference"),
            recorded_at_utc=_datetime(outcome["recorded_at_utc"]),
        ),
        conversion_intent_id=str(payload["conversion_intent_id"]),
        target=ConversionTarget(payload["target"]),
        source_system=SourceSystem(payload["source_system"]),
        boundary=ConversionBoundary(payload["boundary"]),
    )


def _report_evidence_pack_to_json(pack: GovernedReportEvidencePack) -> dict[str, Any]:
    return {
        "report_evidence_pack_id": pack.report_evidence_pack_id,
        "conversion_intent_id": pack.conversion_intent_id,
        "candidate_id": pack.candidate_id,
        "evidence_packet_id": pack.evidence_packet_id,
        "evidence_content_hash": pack.evidence_content_hash,
        "source_signal_ids": list(pack.source_signal_ids),
        "source_summaries": [
            _report_source_summary_to_json(summary) for summary in pack.source_summaries
        ],
        "purpose": pack.purpose.value,
        "actor_subject": pack.actor_subject,
        "idempotency_key": pack.idempotency_key,
        "reason_codes": [reason.value for reason in pack.reason_codes],
        "requested_at_utc": pack.requested_at_utc.isoformat(),
        "retention_policy_ref": pack.retention_policy_ref,
        "report_source_authority": pack.report_source_authority.value,
        "render_source_authority": pack.render_source_authority.value,
        "archive_source_authority": pack.archive_source_authority.value,
        "boundary": pack.boundary.value,
    }


def _report_evidence_pack_from_json(payload: Mapping[str, Any]) -> GovernedReportEvidencePack:
    return GovernedReportEvidencePack(
        report_evidence_pack_id=str(payload["report_evidence_pack_id"]),
        conversion_intent_id=str(payload["conversion_intent_id"]),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        source_summaries=tuple(
            _report_source_summary_from_json(summary) for summary in payload["source_summaries"]
        ),
        purpose=ReportEvidencePackPurpose(payload["purpose"]),
        actor_subject=str(payload["actor_subject"]),
        idempotency_key=str(payload["idempotency_key"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        requested_at_utc=_datetime(payload["requested_at_utc"]),
        retention_policy_ref=str(payload["retention_policy_ref"]),
        report_source_authority=SourceSystem(payload["report_source_authority"]),
        render_source_authority=SourceSystem(payload["render_source_authority"]),
        archive_source_authority=SourceSystem(payload["archive_source_authority"]),
        boundary=ReportEvidencePackBoundary(payload["boundary"]),
    )


def _report_source_summary_to_json(summary: ReportEvidenceSourceSummary) -> dict[str, Any]:
    return {
        "product_id": summary.product_id,
        "source_system": summary.source_system.value,
        "product_version": summary.product_version,
        "as_of_date": summary.as_of_date,
        "generated_at_utc": summary.generated_at_utc.isoformat(),
        "content_hash": summary.content_hash,
        "data_quality_status": summary.data_quality_status,
        "freshness": summary.freshness,
    }


def _report_source_summary_from_json(
    payload: Mapping[str, Any],
) -> ReportEvidenceSourceSummary:
    return ReportEvidenceSourceSummary(
        product_id=str(payload["product_id"]),
        source_system=SourceSystem(payload["source_system"]),
        product_version=str(payload["product_version"]),
        as_of_date=str(payload["as_of_date"]),
        generated_at_utc=_datetime(payload["generated_at_utc"]),
        content_hash=str(payload["content_hash"]),
        data_quality_status=str(payload["data_quality_status"]),
        freshness=str(payload["freshness"]),
    )


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
