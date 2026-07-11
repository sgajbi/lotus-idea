from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.ai_lineage_persistence import AIExplanationLineageRecord
from app.domain.downstream_submission import (
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
)
from app.domain.events import (
    EventLineageContext,
    EventLineageOrigin,
    OutboxEventRecord,
    build_candidate_outbox_event,
)
from app.domain.outbox_delivery_state import (
    OutboxDeliveryDecision,
    claim_outbox_events_for_delivery,
    mark_owned_outbox_event_failed,
    mark_owned_outbox_event_published,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_record


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_downstream_submission_record_rejects_invalid_runtime_evidence() -> None:
    valid = downstream_submission_record()

    with pytest.raises(ValueError, match="downstream_failure_reason is required"):
        replace(valid, downstream_failure_reason=" ")
    with pytest.raises(ValueError, match="submitted_at_utc must be timezone-aware"):
        replace(valid, submitted_at_utc=datetime(2026, 6, 21, 10, 0))
    with pytest.raises(ValueError, match="submitted_at_utc must be UTC"):
        replace(
            valid,
            submitted_at_utc=datetime(2026, 6, 21, 11, 0, tzinfo=timezone(timedelta(hours=1))),
        )


def test_ai_explanation_lineage_record_rejects_invalid_governance_lineage() -> None:
    valid = ai_lineage_record()

    with pytest.raises(ValueError, match="reason_codes is required"):
        replace(valid, reason_codes=())
    with pytest.raises(ValueError, match="fallback_reason is required"):
        replace(valid, fallback_reason=" ")
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        replace(valid, evaluated_at_utc=datetime(2026, 6, 21, 10, 1))


def test_outbox_delivery_state_rejects_invalid_lease_window_and_timestamp() -> None:
    event = outbox_event()
    events = {event.event_id: event}

    with pytest.raises(ValueError, match="lease_expires_at_utc must be after claimed_at_utc"):
        claim_outbox_events_for_delivery(
            events,
            limit=10,
            max_retry_count=2,
            lease_owner="worker-1",
            lease_attempt_id="attempt-invalid-window",
            claimed_at_utc=EVENT_TIME,
            lease_expires_at_utc=EVENT_TIME,
        )
    with pytest.raises(ValueError, match="published_at_utc must be UTC"):
        mark_owned_outbox_event_published(
            events,
            "event-1",
            lease_owner="worker-1",
            lease_attempt_id="attempt-nonutc-publish",
            published_at_utc=datetime(2026, 6, 21, 11, 0, tzinfo=timezone(timedelta(hours=1))),
        )


def test_outbox_delivery_state_reports_lease_lost_for_wrong_owner() -> None:
    event = outbox_event()
    events = {event.event_id: event}
    claimed = claim_outbox_events_for_delivery(
        events,
        limit=10,
        max_retry_count=2,
        lease_owner="worker-1",
        lease_attempt_id="attempt-1",
        claimed_at_utc=EVENT_TIME,
        lease_expires_at_utc=EVENT_TIME + timedelta(minutes=5),
    )

    published = mark_owned_outbox_event_published(
        events,
        claimed[0].event_id,
        lease_owner="worker-2",
        lease_attempt_id="attempt-2",
        published_at_utc=EVENT_TIME + timedelta(minutes=1),
    )
    failed = mark_owned_outbox_event_failed(
        events,
        claimed[0].event_id,
        lease_owner="worker-2",
        lease_attempt_id="attempt-2",
        failure_reason="publisher_unavailable",
        max_retry_count=2,
    )

    assert published.decision is OutboxDeliveryDecision.LEASE_LOST
    assert failed.decision is OutboxDeliveryDecision.LEASE_LOST


def downstream_submission_record() -> DownstreamSubmissionRecord:
    return build_downstream_submission_record(
        idempotency_key="downstream-submit-001",
        request_fingerprint="sha256:downstream-submit",
        resource_id="conversion-intent-001",
        status=DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        failure_reason="publisher_rejected",
        submitted_at_utc=EVENT_TIME,
    )


def ai_lineage_record() -> AIExplanationLineageRecord:
    return AIExplanationLineageRecord(
        request_id="ai-request-001",
        candidate_id="idea-candidate-001",
        evidence_packet_id="evidence-packet-001",
        evidence_content_hash="sha256:evidence",
        workflow_pack_id="workflow-pack-001",
        workflow_pack_version="v1",
        purpose="advisor_review_support",
        posture="fallback_explanation",
        verifier_outcome="fallback_used",
        fallback_used=True,
        fallback_reason="model_unavailable",
        reason_codes=("deterministic_fallback",),
        output_id=None,
        claim_ids=(),
        proposed_action_types=(),
        action_policy_version="lotus-idea.ai-action-content-policy.v1",
        output_integrity_version="lotus-idea.ai-output-integrity.v1",
        output_content_digest=f"sha256:{'1' * 64}",
        actor_subject="advisor-001",
        requested_at_utc=EVENT_TIME,
        evaluated_at_utc=EVENT_TIME + timedelta(minutes=1),
        grants_downstream_authority=False,
        lineage_hash=f"sha256:{'2' * 64}",
    )


def outbox_event() -> OutboxEventRecord:
    return build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="idea-candidate-001",
        occurred_at_utc=EVENT_TIME,
        payload={"candidateFamily": "high_cash"},
        idempotency_key="idea.candidate.persisted.v1:idempotency",
        lineage=EventLineageContext(
            correlation_id="corr-001",
            trace_id="trace-001",
            causation_id="cause-001",
            origin=EventLineageOrigin.PARENT_EVENT,
        ),
    )
