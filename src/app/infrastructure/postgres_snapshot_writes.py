from __future__ import annotations

from psycopg.types.json import Jsonb

from app.domain.audit import AuditEvent
from app.domain.conversion_governance import (
    GovernedConversionIntent,
    GovernedConversionOutcome,
)
from app.domain.downstream_submission import DownstreamSubmissionRecord
from app.domain.idempotency import IdempotencyRecord
from app.domain.persistence import (
    CandidatePersistenceRecord,
    IdeaRepositorySnapshot,
    LifecycleHistoryEntry,
)
from app.domain.report_evidence import GovernedReportEvidencePack
from app.domain.review_governance import GovernedFeedbackEvent, GovernedReviewDecision
from app.infrastructure.data_lifecycle.postgres_policy import (
    insert_data_lifecycle_control_for_candidate,
)
from app.infrastructure.postgres_ai_lineage_writes import (
    insert_ai_explanation_lineage_records,
)
from app.infrastructure.postgres_candidate_writes import (
    ConcurrentIdempotencyMutationError,
)
from app.infrastructure.postgres_codecs import (
    conversion_intent_to_json,
    feedback_event_to_json,
    idea_candidate_to_json,
    report_evidence_pack_to_json,
    review_decision_to_json,
)
from app.infrastructure.postgres_conversion_outcome import (
    insert_postgres_conversion_outcome,
)
from app.infrastructure.postgres_downstream_submission import (
    DOWNSTREAM_SUBMISSION_COLUMNS,
    downstream_submission_values,
)
from app.infrastructure.postgres_mutation_metadata import (
    idempotency_created_at,
    operation_name,
)
from app.infrastructure.postgres_protocols import PostgresCursor
from app.infrastructure.postgres_review_identity import (
    ConcurrentReviewIdentityMutationError,
)


class PostgresSnapshotWriteRepositoryMixin:
    """Snapshot replacement write helpers for PostgreSQL idea persistence."""

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
        insert_data_lifecycle_control_for_candidate(cursor, record)

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
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING idempotency_key
            """,
            (
                record.key,
                operation_name(record.key),
                record.payload_hash,
                candidate_id,
                idempotency_created_at(candidate_id, snapshot),
            ),
        )
        if not cursor.fetchall():
            raise ConcurrentIdempotencyMutationError(record.key)

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
        insert_ai_explanation_lineage_records(cursor, record)

    def _insert_downstream_submission_record(
        self,
        cursor: PostgresCursor,
        record: DownstreamSubmissionRecord,
    ) -> None:
        cursor.execute(
            f"""
            INSERT INTO idea_downstream_submission (
                {DOWNSTREAM_SUBMISSION_COLUMNS}
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            downstream_submission_values(record),
        )

    def _insert_lifecycle_history(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for index, entry in enumerate(record.lifecycle_history, start=1):
            self._insert_lifecycle_history_entry(cursor, candidate_id, entry, index)

    def _insert_lifecycle_history_entry(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        entry: LifecycleHistoryEntry,
        index: int,
    ) -> None:
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
            self._insert_audit_event(cursor, candidate_id, event, index)

    def _insert_audit_event(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        event: AuditEvent,
        index: int,
    ) -> None:
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
            self._insert_review_decision(cursor, candidate_id, decision)

    def _insert_review_decision(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        decision: GovernedReviewDecision,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO idea_review_decision (
                review_decision_id, candidate_id, action, actor_subject,
                decision_json, decided_at_utc
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (review_decision_id) DO NOTHING
            RETURNING review_decision_id
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
        if not cursor.fetchall():
            raise ConcurrentReviewIdentityMutationError(decision.mutation_identity)

    def _insert_feedback_events(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for feedback in record.feedback_events:
            self._insert_feedback_event(cursor, candidate_id, feedback)

    def _insert_feedback_event(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        feedback: GovernedFeedbackEvent,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO idea_feedback_event (
                feedback_event_id, candidate_id, actor_subject, feedback_json,
                recorded_at_utc
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (feedback_event_id) DO NOTHING
            RETURNING feedback_event_id
            """,
            (
                feedback.feedback.feedback_id,
                candidate_id,
                feedback.actor_subject,
                Jsonb(feedback_event_to_json(feedback)),
                feedback.feedback.recorded_at_utc,
            ),
        )
        if not cursor.fetchall():
            raise ConcurrentReviewIdentityMutationError(feedback.mutation_identity)

    def _insert_conversion_intents(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for intent in record.conversion_intents:
            self._insert_conversion_intent(cursor, candidate_id, intent)

    def _insert_conversion_intent(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        intent: GovernedConversionIntent,
    ) -> None:
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
            self._insert_conversion_outcome(cursor, outcome)

    def _insert_conversion_outcome(
        self,
        cursor: PostgresCursor,
        outcome: GovernedConversionOutcome,
    ) -> None:
        insert_postgres_conversion_outcome(cursor, outcome)

    def _insert_report_evidence_packs(
        self,
        cursor: PostgresCursor,
        record: CandidatePersistenceRecord,
    ) -> None:
        candidate_id = record.candidate.candidate_id
        for evidence_pack in record.report_evidence_packs:
            self._insert_report_evidence_pack(cursor, candidate_id, evidence_pack)

    def _insert_report_evidence_pack(
        self,
        cursor: PostgresCursor,
        candidate_id: str,
        evidence_pack: GovernedReportEvidencePack,
    ) -> None:
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
