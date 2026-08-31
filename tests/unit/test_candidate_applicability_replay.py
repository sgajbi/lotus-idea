from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain import (
    EvidenceReplayStatus,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    OpportunityFamily,
)
from tests.support.opportunity_effectiveness_fixture import candidate_fixture


def test_replay_enforces_persisted_applicability_expiry_at_exact_boundary() -> None:
    created_at_utc = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    expires_at_utc = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)
    candidate = candidate_fixture(
        "candidate-applicability-replay-001",
        family=OpportunityFamily.BOND_MATURITY,
        score=Decimal("80"),
        created_at=created_at_utc,
    )
    candidate = replace(
        candidate,
        evidence_packet=replace(
            candidate.evidence_packet,
            applicability_expires_at_utc=expires_at_utc,
        ),
    )
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:expiring-candidate:001",
        payload={"candidate_id": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=created_at_utc,
    )
    assert persisted.record is not None

    before = repository.replay_evidence(
        candidate.candidate_id,
        current_source_refs=candidate.evidence_packet.source_refs,
        evaluated_at_utc=expires_at_utc - timedelta(microseconds=1),
    )
    exactly_at = repository.replay_evidence(
        candidate.candidate_id,
        current_source_refs=candidate.evidence_packet.source_refs,
        evaluated_at_utc=expires_at_utc,
    )

    assert before.status is EvidenceReplayStatus.MATCHED
    assert exactly_at.status is EvidenceReplayStatus.EXPIRED
    assert exactly_at.record is not None
    assert exactly_at.record.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
