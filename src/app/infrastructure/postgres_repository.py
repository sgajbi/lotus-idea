from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Callable, Mapping, Protocol, Sequence, TypeVar

from psycopg.types.json import Jsonb

from app.domain.ai_governance import AIExplanationResult
from app.domain.audit import AuditEvent
from app.domain.events import OutboxEventRecord
from app.domain.conversion_governance import (
    ConversionIntentResult,
    ConversionOutcomeResult,
    GovernedConversionIntent,
)
from app.domain.ideas import (
    IdeaCandidate,
    IdeaLifecycleStatus,
    SourceRef,
)
from app.domain.ai_lineage_persistence import AIExplanationLineagePersistenceResult
from app.domain.idempotency import IdempotencyRecord
from app.domain.outbox_delivery_state import OutboxDeliveryResult
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
    ReportEvidencePackResult,
)
from app.domain.review_governance import (
    FeedbackResult,
    ReviewActionResult,
)
from app.infrastructure.postgres_codecs import (
    ai_explanation_lineage_from_json,
    ai_explanation_lineage_to_json,
    conversion_intent_from_json,
    conversion_intent_to_json,
    conversion_outcome_from_json,
    conversion_outcome_to_json,
    feedback_event_from_json,
    feedback_event_to_json,
    idea_candidate_from_json,
    idea_candidate_to_json,
    read_json_object,
    read_row_value,
    report_evidence_pack_from_json,
    report_evidence_pack_to_json,
    review_decision_from_json,
    review_decision_to_json,
)
from app.infrastructure.postgres_outbox_delivery import (
    claim_outbox_events_for_delivery as claim_postgres_outbox_events_for_delivery,
    mark_outbox_event_failed as mark_postgres_outbox_event_failed,
    mark_outbox_event_published as mark_postgres_outbox_event_published,
    outbox_event_from_row,
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

    def outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        evaluated_at_utc: datetime | None = None,
    ) -> tuple[OutboxEventRecord, ...]:
        repository = InMemoryIdeaRepository(self.snapshot())
        return repository.outbox_events_for_delivery(
            limit=limit,
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc,
        )

    def claim_outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        lease_owner: str,
        lease_attempt_id: str,
        claimed_at_utc: datetime,
        lease_expires_at_utc: datetime,
    ) -> tuple[OutboxEventRecord, ...]:
        return claim_postgres_outbox_events_for_delivery(
            self._connection,
            limit=limit,
            max_retry_count=max_retry_count,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            claimed_at_utc=claimed_at_utc,
            lease_expires_at_utc=lease_expires_at_utc,
        )

    def mark_outbox_event_published(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        published_at_utc: datetime,
    ) -> OutboxDeliveryResult:
        return mark_postgres_outbox_event_published(
            self._connection,
            event_id,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            published_at_utc=published_at_utc,
        )

    def mark_outbox_event_failed(
        self,
        event_id: str,
        *,
        lease_owner: str,
        lease_attempt_id: str,
        failure_reason: str,
        max_retry_count: int = 3,
    ) -> OutboxDeliveryResult:
        return mark_postgres_outbox_event_failed(
            self._connection,
            event_id,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            failure_reason=failure_reason,
            max_retry_count=max_retry_count,
        )

    def record_ai_explanation_lineage(
        self,
        result: AIExplanationResult,
    ) -> AIExplanationLineagePersistenceResult:
        return self._mutate(lambda repository: repository.record_ai_explanation_lineage(result))

    def snapshot(self) -> IdeaRepositorySnapshot:
        with self._connection.cursor() as cursor:
            candidate_records = self._load_candidate_records(cursor)
            idempotency_records, idempotency_candidates = self._load_idempotency(cursor)
            self._attach_lifecycle_history(cursor, candidate_records)
            self._attach_audit_events(cursor, candidate_records)
            outbox_events = self._load_outbox_events(cursor)
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
            ai_explanation_lineage_candidates = self._attach_ai_explanation_lineage_records(
                cursor,
                candidate_records,
            )
        return IdeaRepositorySnapshot(
            candidate_records=candidate_records,
            idempotency_records=idempotency_records,
            idempotency_candidates=idempotency_candidates,
            conversion_intent_candidates=conversion_intent_candidates,
            report_evidence_pack_candidates=report_evidence_pack_candidates,
            ai_explanation_lineage_candidates=ai_explanation_lineage_candidates,
            outbox_events=outbox_events,
        )

    def replace_snapshot(self, snapshot: IdeaRepositorySnapshot) -> None:
        with self._connection.cursor() as cursor:
            for table_name in (
                "idea_ai_explanation_lineage",
                "idea_report_evidence_pack_request",
                "idea_conversion_outcome",
                "idea_conversion_intent",
                "idea_feedback_event",
                "idea_review_decision",
                "idea_outbox_event",
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
            for outbox_event in snapshot.outbox_events.values():
                self._insert_outbox_event(cursor, outbox_event)

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
            candidate_id = read_row_value(row, "candidate_id")
            records[candidate_id] = CandidatePersistenceRecord(
                candidate=idea_candidate_from_json(read_json_object(row, "candidate_json")),
                evidence_hash=read_row_value(row, "evidence_hash"),
                persisted_at_utc=read_row_value(row, "persisted_at_utc"),
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
            key = read_row_value(row, "idempotency_key")
            records[key] = IdempotencyRecord(
                key=key,
                payload_hash=read_row_value(row, "payload_hash"),
            )
            candidate_id = read_row_value(row, "candidate_id")
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
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            entry = LifecycleHistoryEntry(
                candidate_id=candidate_id,
                source_status=IdeaLifecycleStatus(read_row_value(row, "source_status")),
                target_status=IdeaLifecycleStatus(read_row_value(row, "target_status")),
                actor_subject=read_row_value(row, "actor_subject"),
                changed_at_utc=read_row_value(row, "changed_at_utc"),
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
            candidate_id = read_row_value(row, "candidate_id")
            if candidate_id is None or candidate_id not in records:
                continue
            record = records[candidate_id]
            event = AuditEvent(
                event_type=read_row_value(row, "event_type"),
                actor_subject=read_row_value(row, "actor_subject"),
                outcome=read_row_value(row, "outcome"),
                attributes=read_json_object(row, "attributes_json"),
                occurred_at_utc=read_row_value(row, "occurred_at_utc"),
            )
            records[candidate_id] = replace(
                record,
                audit_events=(*record.audit_events, event),
            )

    def _load_outbox_events(self, cursor: PostgresCursor) -> dict[str, OutboxEventRecord]:
        cursor.execute(
            """
            SELECT outbox_event_id, event_type, aggregate_type, aggregate_id,
                   schema_version, payload_json, status, occurred_at_utc,
                   idempotency_fingerprint, correlation_id, causation_id,
                   published_at_utc, failure_reason, retry_count,
                   lease_owner, lease_attempt_id, lease_expires_at_utc
            FROM idea_outbox_event
            ORDER BY occurred_at_utc, outbox_event_id
            """
        )
        events: dict[str, OutboxEventRecord] = {}
        for row in cursor.fetchall():
            event = outbox_event_from_row(row)
            events[event.event_id] = event
        return events

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
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            decision = review_decision_from_json(read_json_object(row, "decision_json"))
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
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            feedback = feedback_event_from_json(read_json_object(row, "feedback_json"))
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
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            intent_id = read_row_value(row, "conversion_intent_id")
            intent = conversion_intent_from_json(read_json_object(row, "intent_json"))
            records[candidate_id] = replace(
                record,
                conversion_intents=(*record.conversion_intents, intent),
            )
            candidates[intent_id] = candidate_id
        return candidates

    def _attach_ai_explanation_lineage_records(
        self,
        cursor: PostgresCursor,
        records: dict[str, CandidatePersistenceRecord],
    ) -> dict[str, str]:
        cursor.execute(
            """
            SELECT ai_explanation_request_id, candidate_id, lineage_json
            FROM idea_ai_explanation_lineage
            ORDER BY evaluated_at_utc, ai_explanation_request_id
            """
        )
        candidates: dict[str, str] = {}
        for row in cursor.fetchall():
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            request_id = read_row_value(row, "ai_explanation_request_id")
            lineage_record = ai_explanation_lineage_from_json(read_json_object(row, "lineage_json"))
            records[candidate_id] = replace(
                record,
                ai_explanation_lineage_records=(
                    *record.ai_explanation_lineage_records,
                    lineage_record,
                ),
            )
            candidates[request_id] = candidate_id
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
            candidate_id = intent_candidates.get(read_row_value(row, "conversion_intent_id"))
            if candidate_id is None:
                continue
            record = records[candidate_id]
            outcome = conversion_outcome_from_json(read_json_object(row, "outcome_json"))
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
            candidate_id = read_row_value(row, "candidate_id")
            record = records.get(candidate_id)
            if record is None:
                continue
            pack_id = read_row_value(row, "report_evidence_pack_id")
            evidence_pack = report_evidence_pack_from_json(
                read_json_object(row, "evidence_pack_json")
            )
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
                Jsonb(idea_candidate_to_json(candidate)),
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
        self._insert_lifecycle_history(cursor, record)
        self._insert_audit_events(cursor, record)
        self._insert_review_decisions(cursor, record)
        self._insert_feedback_events(cursor, record)
        self._insert_conversion_intents(cursor, record)
        self._insert_conversion_outcomes(cursor, record)
        self._insert_report_evidence_packs(cursor, record)
        self._insert_ai_explanation_lineage_records(cursor, record)

    def _insert_lifecycle_history(
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

    def _insert_audit_events(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
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

    def _insert_review_decisions(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
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
                    Jsonb(review_decision_to_json(decision)),
                    decision.decided_at_utc,
                ),
            )

    def _insert_feedback_events(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
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
                    Jsonb(feedback_event_to_json(feedback)),
                    feedback.feedback.recorded_at_utc,
                ),
            )

    def _insert_conversion_intents(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
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
                    Jsonb(conversion_intent_to_json(intent)),
                    intent.intent.requested_at_utc,
                ),
            )

    def _insert_conversion_outcomes(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
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
                    Jsonb(conversion_outcome_to_json(outcome)),
                    outcome.outcome.recorded_at_utc,
                ),
            )

    def _insert_report_evidence_packs(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
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
                    Jsonb(report_evidence_pack_to_json(evidence_pack)),
                    evidence_pack.requested_at_utc,
                ),
            )

    def _insert_ai_explanation_lineage_records(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for lineage_record in record.ai_explanation_lineage_records:
            cursor.execute(
                """
                INSERT INTO idea_ai_explanation_lineage (
                    ai_explanation_request_id, candidate_id, evidence_packet_id,
                    evidence_content_hash, workflow_pack_id, workflow_pack_version,
                    purpose, posture, verifier_outcome, fallback_used, fallback_reason,
                    lineage_hash, lineage_json, requested_at_utc, evaluated_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    lineage_record.request_id,
                    candidate_id,
                    lineage_record.evidence_packet_id,
                    lineage_record.evidence_content_hash,
                    lineage_record.workflow_pack_id,
                    lineage_record.workflow_pack_version,
                    lineage_record.purpose,
                    lineage_record.posture,
                    lineage_record.verifier_outcome,
                    lineage_record.fallback_used,
                    lineage_record.fallback_reason,
                    lineage_record.lineage_hash,
                    Jsonb(ai_explanation_lineage_to_json(lineage_record)),
                    lineage_record.requested_at_utc,
                    lineage_record.evaluated_at_utc,
                ),
            )

    def _insert_outbox_event(
        self,
        cursor: PostgresCursor,
        event: OutboxEventRecord,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO idea_outbox_event (
                outbox_event_id, event_type, aggregate_type, aggregate_id,
                schema_version, payload_json, status, occurred_at_utc,
                idempotency_fingerprint, correlation_id, causation_id,
                published_at_utc, failure_reason, retry_count, lease_owner,
                lease_attempt_id, lease_expires_at_utc
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                event.event_id,
                event.event_type,
                event.aggregate_type,
                event.aggregate_id,
                event.schema_version,
                Jsonb(dict(event.payload)),
                event.status.value,
                event.occurred_at_utc,
                event.idempotency_fingerprint,
                event.correlation_id,
                event.causation_id,
                event.published_at_utc,
                event.failure_reason,
                event.retry_count,
                event.lease_owner,
                event.lease_attempt_id,
                event.lease_expires_at_utc,
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
