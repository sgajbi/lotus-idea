from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Mapping

from psycopg.types.json import Jsonb

from app.domain.audit import AuditEvent
from app.domain.outbox.events import EventLineageContext, OutboxEventRecord
from app.domain.downstream_submission import DownstreamSubmissionRecord
from app.domain.conversion_governance import (
    ConversionIntentResult,
    ConversionOutcomeResult,
    GovernedConversionOutcome,
    GovernedConversionIntent,
)
from app.domain.conversion_outcome_policy import ConversionOutcomeIdentity
from app.domain.ideas import IdeaCandidate, IdeaLifecycleStatus
from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord
from app.domain.outbox.delivery import OutboxDeliveryResult
from app.domain.persistence import (
    CandidatePersistenceRecord,
    CandidatePersistenceResult,
    ConversionPersistenceResult,
    EvidencePackPersistenceResult,
    IdeaRepositorySnapshot,
    LifecycleHistoryEntry,
    LifecyclePersistenceResult,
    ReviewPersistenceResult,
)
from app.domain.report_evidence import (
    GovernedReportEvidencePack,
    ReportEvidencePackResult,
)
from app.domain.review_governance import (
    FeedbackResult,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewActionResult,
    ReviewMutationIdentity,
)
from app.infrastructure.postgres_candidate_writes import (
    ConcurrentIdempotencyMutationError,
    update_postgres_candidate_record,
)
from app.infrastructure.postgres_ai_lineage_reads import ai_explanation_lineage_from_row
from app.infrastructure.postgres_ai_lineage_repository import PostgresAIExplanationWriteMixin
from app.infrastructure.postgres_conversion_outcome import (
    insert_postgres_conversion_outcome,
    load_postgres_conversion_outcomes_for_intent,
    precheck_postgres_conversion_outcome_mutation,
)
from app.infrastructure.postgres_codecs import (
    conversion_intent_from_json,
    conversion_intent_to_json,
    conversion_outcome_from_json,
    feedback_event_from_json,
    feedback_event_to_json,
    idea_candidate_to_json,
    read_json_object,
    read_row_value,
    report_evidence_pack_from_json,
    report_evidence_pack_to_json,
    review_decision_from_json,
    review_decision_to_json,
)
from app.infrastructure.postgres_ai_lineage_writes import insert_ai_explanation_lineage_records
from app.infrastructure.outbox.postgres_delivery import (
    claim_outbox_events_for_delivery as claim_postgres_outbox_events_for_delivery,
    mark_outbox_event_failed as mark_postgres_outbox_event_failed,
    mark_outbox_event_published as mark_postgres_outbox_event_published,
    outbox_event_from_row,
)
from app.infrastructure.outbox.postgres_repository import PostgresOutboxRepositoryMixin
from app.infrastructure.postgres_mutation_metadata import idempotency_created_at, operation_name
from app.infrastructure.outbox.postgres_recovery import PostgresOutboxRecoveryRepositoryMixin
from app.infrastructure.postgres_protocols import PostgresConnection as PostgresConnection
from app.infrastructure.postgres_protocols import PostgresCursor
from app.infrastructure.postgres_downstream_lookup import (
    load_candidate_record_for_report_evidence_pack,
    load_candidate_record_for_conversion_intent,
    load_conversion_intent_by_id,
    load_report_evidence_pack_by_id,
)
from app.infrastructure.postgres_downstream_submission import (
    DOWNSTREAM_SUBMISSION_COLUMNS,
    downstream_submission_from_row,
    downstream_submission_values,
)
from app.infrastructure.postgres_downstream_submission_repository import (
    PostgresDownstreamSubmissionRepositoryMixin,
)
from app.infrastructure.postgres_downstream_readiness import (
    load_downstream_realization_readiness_summary,
)
from app.infrastructure.postgres_idempotency_precheck import (
    precheck_postgres_conversion_mutation,
    precheck_postgres_review_mutation,
)
from app.infrastructure.postgres_review_queue import (
    PostgresReviewQueueRepositoryMixin,
    candidate_record_from_row,
)
from app.infrastructure.postgres_review_identity import ConcurrentReviewIdentityMutationError
from app.infrastructure.postgres_runtime_trust_telemetry import (
    load_runtime_trust_telemetry_summary,
)
from app.infrastructure.postgres_slo import execute_observed_postgres_call
from app.infrastructure.postgres_capacity_posture import PostgresCapacityRepositoryMixin
from app.infrastructure.postgres_candidate_detail import PostgresCandidateDetailRepositoryMixin
from app.infrastructure.persistence.postgres_mutation import (
    PostgresBoundedMutationRepositoryMixin,
)
from app.infrastructure.persistence.postgres_replay import (
    PostgresEvidenceReplayRepositoryMixin,
)
from app.infrastructure.data_lifecycle.postgres_policy import (
    PostgresDataLifecycleRepository,
    assert_data_lifecycle_allows_candidate_writes,
    insert_data_lifecycle_control_for_candidate,
)
from app.ports.idea_repository import DownstreamRealizationReadinessRepositorySummary
from app.ports.idea_repository import RuntimeTrustTelemetryRepositorySummary
from app.domain.data_lifecycle import DataLifecycleCommand, DataLifecycleOperationResult
from app.ports.data_lifecycle import DataLifecycleEvaluator


class PostgresIdeaRepository(
    PostgresBoundedMutationRepositoryMixin,
    PostgresEvidenceReplayRepositoryMixin,
    PostgresAIExplanationWriteMixin,
    PostgresCapacityRepositoryMixin,
    PostgresCandidateDetailRepositoryMixin,
    PostgresReviewQueueRepositoryMixin,
    PostgresOutboxRepositoryMixin,
    PostgresOutboxRecoveryRepositoryMixin,
    PostgresDownstreamSubmissionRepositoryMixin,
):
    """PostgreSQL-backed implementation of the governed idea repository ports."""

    durable_storage_backed = True

    def __init__(self, connection: PostgresConnection) -> None:
        self._connection = connection

    def downstream_realization_readiness_summary(
        self,
    ) -> DownstreamRealizationReadinessRepositorySummary:
        return load_downstream_realization_readiness_summary(self._connection)

    def runtime_trust_telemetry_summary(self) -> RuntimeTrustTelemetryRepositorySummary:
        return load_runtime_trust_telemetry_summary(self._connection)

    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: DataLifecycleEvaluator,
    ) -> DataLifecycleOperationResult:
        return PostgresDataLifecycleRepository(self._connection).execute_data_lifecycle(
            command,
            evaluated_at_utc=evaluated_at_utc,
            evaluator=evaluator,
        )

    def persist_candidate(
        self,
        candidate: IdeaCandidate,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        actor_subject: str,
        occurred_at_utc: datetime | None = None,
        event_lineage: EventLineageContext | None = None,
    ) -> CandidatePersistenceResult:
        return self._mutate_candidate(
            candidate_ids=(candidate.candidate_id,),
            idempotency_key=idempotency_key,
            operation=lambda repository: repository.persist_candidate(
                candidate,
                idempotency_key=idempotency_key,
                payload=payload,
                actor_subject=actor_subject,
                occurred_at_utc=occurred_at_utc,
                event_lineage=event_lineage,
            ),
        )

    def record_outbox_delivery_run_request(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> IdempotencyDecision:
        return self._mutate_idempotency(
            idempotency_key,
            operation=lambda repository: repository.record_outbox_delivery_run_request(
                idempotency_key=idempotency_key,
                payload=payload,
            ),
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
        event_lineage: EventLineageContext | None = None,
    ) -> LifecyclePersistenceResult:
        return self._mutate_candidate(
            candidate_ids=(candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=(f"lifecycle-transition:{transition_id or idempotency_key}",),
            operation=lambda repository: repository.record_lifecycle_transition(
                candidate_id,
                target_status,
                idempotency_key=idempotency_key,
                payload=payload,
                actor_subject=actor_subject,
                occurred_at_utc=occurred_at_utc,
                transition_id=transition_id,
                reason_codes=reason_codes,
                event_lineage=event_lineage,
            ),
        )

    def precheck_review_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        identity: ReviewMutationIdentity,
    ) -> ReviewPersistenceResult | None:
        return precheck_postgres_review_mutation(
            self._connection,
            idempotency_key=idempotency_key,
            payload=payload,
            identity=identity,
        )

    def record_review_action(
        self,
        result: ReviewActionResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
    ) -> ReviewPersistenceResult:
        identity = result.decision.mutation_identity
        return self._mutate_candidate(
            candidate_ids=(result.decision.candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=(f"{identity.mutation_type.value}:{identity.resource_id}",),
            related_candidate_ids_loader=lambda: self._review_identity_candidate_ids(identity),
            operation=lambda repository: repository.record_review_action(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                event_lineage=event_lineage,
            ),
        )

    def record_feedback_event(
        self,
        result: FeedbackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
    ) -> ReviewPersistenceResult:
        identity = result.feedback_event.mutation_identity
        return self._mutate_candidate(
            candidate_ids=(result.feedback_event.candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=(f"{identity.mutation_type.value}:{identity.resource_id}",),
            related_candidate_ids_loader=lambda: self._review_identity_candidate_ids(identity),
            operation=lambda repository: repository.record_feedback_event(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                event_lineage=event_lineage,
            ),
        )

    def precheck_conversion_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> ConversionPersistenceResult | None:
        return precheck_postgres_conversion_mutation(
            self._connection,
            idempotency_key=idempotency_key,
            payload=payload,
        )

    def record_conversion_intent(
        self,
        result: ConversionIntentResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
    ) -> ConversionPersistenceResult:
        candidate_id = result.conversion_intent.intent.candidate_id
        conversion_intent_id = result.conversion_intent.intent.conversion_intent_id
        return self._mutate_candidate(
            candidate_ids=(candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=(f"conversion-intent:{conversion_intent_id}",),
            related_candidate_ids_loader=lambda: self._conversion_intent_candidate_ids(
                conversion_intent_id
            ),
            operation=lambda repository: repository.record_conversion_intent(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                event_lineage=event_lineage,
            ),
        )

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None:
        return load_conversion_intent_by_id(self._connection, conversion_intent_id)

    def conversion_outcomes_for_intent(
        self,
        conversion_intent_id: str,
    ) -> tuple[GovernedConversionOutcome, ...]:
        return load_postgres_conversion_outcomes_for_intent(
            self._connection,
            conversion_intent_id,
        )

    def precheck_conversion_outcome_mutation(
        self,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        identity: ConversionOutcomeIdentity,
    ) -> ConversionPersistenceResult | None:
        return precheck_postgres_conversion_outcome_mutation(
            self._connection,
            idempotency_key=idempotency_key,
            payload=payload,
            identity=identity,
        )

    def record_conversion_outcome(
        self,
        result: ConversionOutcomeResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
    ) -> ConversionPersistenceResult:
        identity = result.conversion_outcome.identity
        return self._mutate_candidate(
            candidate_ids=(),
            idempotency_key=idempotency_key,
            identity_keys=(
                f"conversion-intent:{identity.conversion_intent_id}",
                f"conversion-outcome:{identity.conversion_outcome_id}",
            ),
            related_candidate_ids_loader=lambda: self._conversion_outcome_candidate_ids(identity),
            operation=lambda repository: repository.record_conversion_outcome(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                event_lineage=event_lineage,
            ),
        )

    def candidate_record_for_conversion_intent(
        self,
        conversion_intent_id: str,
    ) -> CandidatePersistenceRecord | None:
        return load_candidate_record_for_conversion_intent(self._connection, conversion_intent_id)

    def report_evidence_pack_by_id(
        self,
        report_evidence_pack_id: str,
    ) -> GovernedReportEvidencePack | None:
        return load_report_evidence_pack_by_id(self._connection, report_evidence_pack_id)

    def candidate_record_for_report_evidence_pack(
        self,
        report_evidence_pack_id: str,
    ) -> CandidatePersistenceRecord | None:
        return load_candidate_record_for_report_evidence_pack(
            self._connection,
            report_evidence_pack_id,
        )

    def record_report_evidence_pack(
        self,
        result: ReportEvidencePackResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        event_lineage: EventLineageContext | None = None,
    ) -> EvidencePackPersistenceResult:
        candidate_id = result.evidence_pack.candidate_id
        return self._mutate_candidate(
            candidate_ids=(candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=(f"report-evidence-pack:{result.evidence_pack.report_evidence_pack_id}",),
            operation=lambda repository: repository.record_report_evidence_pack(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                event_lineage=event_lineage,
            ),
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
        failed_at_utc: datetime | None = None,
        max_retry_count: int = 3,
        next_attempt_at_utc: datetime | None = None,
    ) -> OutboxDeliveryResult:
        return mark_postgres_outbox_event_failed(
            self._connection,
            event_id,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            failure_reason=failure_reason,
            failed_at_utc=failed_at_utc,
            max_retry_count=max_retry_count,
            next_attempt_at_utc=next_attempt_at_utc,
        )

    def snapshot(self) -> IdeaRepositorySnapshot:
        return execute_observed_postgres_call("snapshot_read", self._load_snapshot)

    def _load_snapshot(self) -> IdeaRepositorySnapshot:
        with self._connection.cursor() as cursor:
            candidate_records = self._load_candidate_records(cursor)
            idempotency_records, idempotency_candidates = self._load_idempotency(cursor)
            self._attach_lifecycle_history(cursor, candidate_records)
            self._attach_audit_events(cursor, candidate_records)
            outbox_events = self._load_outbox_events(cursor)
            downstream_submission_records = self._load_downstream_submission_records(cursor)
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
            downstream_submission_records=downstream_submission_records,
        )

    def replace_snapshot(self, snapshot: IdeaRepositorySnapshot) -> None:
        try:
            with self._connection.cursor() as cursor:
                for table_name in (
                    "idea_data_lifecycle_operation",
                    "idea_data_lifecycle_control",
                    "idea_ai_explanation_lineage",
                    "idea_report_evidence_pack_request",
                    "idea_conversion_outcome",
                    "idea_conversion_intent",
                    "idea_feedback_event",
                    "idea_review_decision",
                    "idea_downstream_submission",
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
                for record in snapshot.downstream_submission_records.values():
                    self._insert_downstream_submission_record(cursor, record)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _load_candidate_records(
        self,
        cursor: PostgresCursor,
    ) -> dict[str, CandidatePersistenceRecord]:
        cursor.execute(
            """
            SELECT candidate.candidate_id, candidate.evidence_hash,
                   candidate.candidate_json, candidate.persisted_at_utc
            FROM idea_candidate_record candidate
            LEFT JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = candidate.candidate_id
            WHERE COALESCE(lifecycle.held_from_state, lifecycle.state, 'active')
                  NOT IN ('erased', 'purged')
            ORDER BY candidate.persisted_at_utc, candidate.candidate_id
            """
        )
        records: dict[str, CandidatePersistenceRecord] = {}
        for row in cursor.fetchall():
            candidate_id = read_row_value(row, "candidate_id")
            records[candidate_id] = candidate_record_from_row(row)
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
                   idempotency_fingerprint, correlation_id, trace_id, causation_id,
                   lineage_origin,
                   published_at_utc, failure_reason, retry_count,
                   first_failed_at_utc, last_failed_at_utc, next_attempt_at_utc,
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

    def _load_downstream_submission_records(
        self,
        cursor: PostgresCursor,
    ) -> dict[str, DownstreamSubmissionRecord]:
        cursor.execute(
            """
            SELECT idempotency_key, request_fingerprint, resource_type, resource_id,
                   target, source_authority, status, downstream_failure_reason,
                   correlation_id, trace_id, submitted_at_utc, support_reference,
                   attempt_count, updated_at_utc, lease_owner, lease_attempt_id,
                   lease_expires_at_utc, audit_json
            FROM idea_downstream_submission
            ORDER BY submitted_at_utc, idempotency_key
            """
        )
        records: dict[str, DownstreamSubmissionRecord] = {}
        for row in cursor.fetchall():
            record = downstream_submission_from_row(row)
            records[record.idempotency_key] = record
        return records

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
            SELECT ai_explanation_request_id, candidate_id, output_integrity_version,
                   output_content_digest, execution_provenance_posture, lineage_json
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
            lineage_record = ai_explanation_lineage_from_row(row)
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
        insert_data_lifecycle_control_for_candidate(cursor, record)

    def _assert_data_lifecycle_write_allowed(
        self,
        cursor: Any,
        candidate_ids: set[str],
    ) -> None:
        assert_data_lifecycle_allows_candidate_writes(cursor, candidate_ids)

    def _update_candidate_record(
        self,
        cursor: PostgresCursor,
        before: CandidatePersistenceRecord,
        record: CandidatePersistenceRecord,
    ) -> None:
        update_postgres_candidate_record(cursor, before=before, record=record)

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
