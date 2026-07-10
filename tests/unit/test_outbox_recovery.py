from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, TypedDict

import pytest

from app.domain import (
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    OutboxEventRecord,
    OutboxEventStatus,
    OutboxRecoveryDecision,
    build_candidate_outbox_event,
    build_outbox_recovery_audit_record,
    dead_letter_summary,
    mark_outbox_event_failed,
    mark_outbox_event_published,
    outbox_dead_letter_support_reference,
    outbox_recovery_eligibility_blocker,
    outbox_recovery_request_payload,
)


EVENT_TIME = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


class RecoveryClaimWithoutKey(TypedDict):
    support_reference: str
    request_payload: Mapping[str, Any]
    actor_subject: str
    reason: str
    change_reference: str
    requested_at_utc: datetime
    lease_owner: str
    lease_attempt_id: str
    lease_expires_at_utc: datetime


def test_dead_letter_summary_is_source_safe_and_recovery_eligible() -> None:
    dead_lettered = _dead_lettered_event()

    summary = dead_letter_summary(dead_lettered)

    assert summary.support_reference.startswith("outbox-dlq-")
    assert dead_lettered.event_id not in summary.support_reference
    assert summary.event_family == "idea.candidate.persisted.v1"
    assert summary.schema_version == "v1"
    assert summary.retry_count == 1
    assert summary.failure_reason == "publisher_rejected"
    assert summary.recovery_eligible is True
    assert summary.recovery_blocker is None
    assert summary.disposition == "quarantined"
    assert summary.owner == "lotus-idea-operations"
    assert not hasattr(summary, "payload")
    assert not hasattr(summary, "aggregate_id")
    assert not hasattr(summary, "idempotency_fingerprint")


def test_recovery_eligibility_fails_closed_for_unknown_contracts() -> None:
    assert (
        outbox_recovery_eligibility_blocker(
            event_type="idea.unsupported.v1",
            schema_version="v1",
        )
        == "unsupported_event_family"
    )
    assert (
        outbox_recovery_eligibility_blocker(
            event_type="idea.candidate.persisted.v1",
            schema_version="v2",
        )
        == "unsupported_schema_version"
    )


def test_recovery_audit_preserves_original_failure_and_hashes_secrets() -> None:
    dead_lettered = _dead_lettered_event()
    request_payload = outbox_recovery_request_payload(
        support_reference=outbox_dead_letter_support_reference(dead_lettered.event_id),
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        actor_subject="platform-operator",
    )

    record = build_outbox_recovery_audit_record(
        dead_lettered,
        idempotency_key="outbox-redrive:secret-key",
        request_payload=request_payload,
        actor_subject="platform-operator",
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        requested_at_utc=EVENT_TIME + timedelta(minutes=5),
        lease_owner="outbox-recovery",
        lease_attempt_id="recovery-attempt-1",
        lease_expires_at_utc=EVENT_TIME + timedelta(minutes=10),
    )

    assert record.recovery_id.startswith("recovery_")
    assert record.original_retry_count == 1
    assert record.original_failure_reason == "publisher_rejected"
    assert record.original_first_failed_at_utc == EVENT_TIME + timedelta(minutes=1)
    assert record.original_last_failed_at_utc == EVENT_TIME + timedelta(minutes=1)
    assert record.idempotency_fingerprint != "outbox-redrive:secret-key"
    assert len(record.idempotency_fingerprint) == 64
    assert len(record.request_fingerprint) == 64


def test_published_event_preserves_prior_retry_history() -> None:
    dead_lettered = _dead_lettered_event()

    published = mark_outbox_event_published(
        dead_lettered,
        published_at_utc=EVENT_TIME + timedelta(minutes=6),
    )

    assert published.status is OutboxEventStatus.PUBLISHED
    assert published.retry_count == dead_lettered.retry_count
    assert published.failure_reason == dead_lettered.failure_reason
    assert published.first_failed_at_utc == dead_lettered.first_failed_at_utc
    assert published.last_failed_at_utc == dead_lettered.last_failed_at_utc


def test_recovery_audit_rejects_invalid_lease_window() -> None:
    dead_lettered = _dead_lettered_event()

    with pytest.raises(ValueError, match="lease_expires_at_utc must be after"):
        build_outbox_recovery_audit_record(
            dead_lettered,
            idempotency_key="outbox-redrive:invalid-window",
            request_payload={"supportReference": "outbox-dlq-test"},
            actor_subject="platform-operator",
            reason="broker_route_corrected",
            change_reference="CHG-2026-0710",
            requested_at_utc=EVENT_TIME + timedelta(minutes=5),
            lease_owner="outbox-recovery",
            lease_attempt_id="recovery-attempt-invalid",
            lease_expires_at_utc=EVENT_TIME + timedelta(minutes=5),
        )


def test_in_memory_recovery_claim_is_idempotent_and_lease_fenced() -> None:
    dead_lettered = _dead_lettered_event()
    repository = _repository_with_event(dead_lettered)
    support_reference = outbox_dead_letter_support_reference(dead_lettered.event_id)
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        actor_subject="platform-operator",
    )
    claim: RecoveryClaimWithoutKey = {
        "support_reference": support_reference,
        "request_payload": request_payload,
        "actor_subject": "platform-operator",
        "reason": "broker_route_corrected",
        "change_reference": "CHG-2026-0710",
        "requested_at_utc": EVENT_TIME + timedelta(minutes=5),
        "lease_owner": "outbox-recovery",
        "lease_attempt_id": "recovery-attempt-1",
        "lease_expires_at_utc": EVENT_TIME + timedelta(minutes=10),
    }

    accepted = repository.claim_dead_letter_for_recovery(
        idempotency_key="outbox-redrive:accepted",
        **claim,
    )
    replay = repository.claim_dead_letter_for_recovery(
        idempotency_key="outbox-redrive:accepted",
        **claim,
    )
    competing_claim: RecoveryClaimWithoutKey = {
        **claim,
        "lease_attempt_id": "recovery-attempt-2",
    }
    competing = repository.claim_dead_letter_for_recovery(
        idempotency_key="outbox-redrive:competing",
        **competing_claim,
    )

    assert accepted.decision is OutboxRecoveryDecision.ACCEPTED
    assert accepted.event is not None
    assert accepted.event.status is OutboxEventStatus.LEASED
    assert accepted.event.failure_reason == "publisher_rejected"
    assert accepted.event.first_failed_at_utc == dead_lettered.first_failed_at_utc
    assert replay.decision is OutboxRecoveryDecision.REPLAYED
    assert replay.audit_record == accepted.audit_record
    assert competing.decision is OutboxRecoveryDecision.LEASE_CONFLICT
    assert len(repository.outbox_recovery_audit_records()) == 1


def test_in_memory_recovery_rejects_idempotency_conflict_and_attempt_limit() -> None:
    dead_lettered = _dead_lettered_event()
    repository = _repository_with_event(dead_lettered)
    support_reference = outbox_dead_letter_support_reference(dead_lettered.event_id)
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        actor_subject="platform-operator",
    )
    accepted = repository.claim_dead_letter_for_recovery(
        support_reference=support_reference,
        idempotency_key="outbox-redrive:bounded",
        request_payload=request_payload,
        actor_subject="platform-operator",
        reason="broker_route_corrected",
        change_reference="CHG-2026-0710",
        requested_at_utc=EVENT_TIME + timedelta(minutes=5),
        lease_owner="outbox-recovery",
        lease_attempt_id="recovery-attempt-1",
        lease_expires_at_utc=EVENT_TIME + timedelta(minutes=10),
    )
    conflict = repository.claim_dead_letter_for_recovery(
        support_reference=support_reference,
        idempotency_key="outbox-redrive:bounded",
        request_payload={**request_payload, "reason": "different_reason"},
        actor_subject="platform-operator",
        reason="different_reason",
        change_reference="CHG-2026-0710",
        requested_at_utc=EVENT_TIME + timedelta(minutes=5),
        lease_owner="outbox-recovery",
        lease_attempt_id="recovery-attempt-2",
        lease_expires_at_utc=EVENT_TIME + timedelta(minutes=10),
    )
    assert accepted.event is not None
    repository.mark_outbox_event_failed(
        dead_lettered.event_id,
        lease_owner="outbox-recovery",
        lease_attempt_id="recovery-attempt-1",
        failure_reason="publisher_rejected_again",
        failed_at_utc=EVENT_TIME + timedelta(minutes=6),
        max_retry_count=1,
    )
    exhausted = repository.claim_dead_letter_for_recovery(
        support_reference=support_reference,
        idempotency_key="outbox-redrive:second-attempt",
        request_payload={**request_payload, "changeReference": "CHG-2026-0711"},
        actor_subject="platform-operator",
        reason="broker_route_corrected",
        change_reference="CHG-2026-0711",
        requested_at_utc=EVENT_TIME + timedelta(minutes=7),
        lease_owner="outbox-recovery",
        lease_attempt_id="recovery-attempt-3",
        lease_expires_at_utc=EVENT_TIME + timedelta(minutes=12),
    )

    assert conflict.decision is OutboxRecoveryDecision.CONFLICT
    assert exhausted.decision is OutboxRecoveryDecision.RECOVERY_LIMIT_REACHED
    assert exhausted.blocker == "recovery_attempt_limit_reached"


def test_in_memory_dead_letter_inspection_is_bounded_and_source_safe() -> None:
    dead_lettered = _dead_lettered_event()
    repository = _repository_with_event(dead_lettered)

    summaries = repository.dead_letter_summaries(limit=1)

    assert len(summaries) == 1
    assert summaries[0].support_reference == outbox_dead_letter_support_reference(
        dead_lettered.event_id
    )
    with pytest.raises(ValueError, match="limit must be positive"):
        repository.dead_letter_summaries(limit=0)


def _dead_lettered_event() -> OutboxEventRecord:
    event = build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="idea-candidate-sensitive",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
        idempotency_key="candidate-sensitive-key",
    )
    return mark_outbox_event_failed(
        event,
        failure_reason="publisher_rejected",
        failed_at_utc=EVENT_TIME + timedelta(minutes=1),
        max_retry_count=1,
        next_attempt_at_utc=None,
    )


def _repository_with_event(event: OutboxEventRecord) -> InMemoryIdeaRepository:
    return InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={},
            report_evidence_pack_candidates={},
            ai_explanation_lineage_candidates={},
            outbox_events={event.event_id: event},
            downstream_submission_records={},
        )
    )
