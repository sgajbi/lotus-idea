from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.persistence import (
    CandidatePersistenceRecord,
    InMemoryIdeaRepository,
    LifecycleHistoryEntry,
)
from app.domain.ideas import IdeaLifecycleStatus
from tests.unit.test_postgres_repository import high_cash_candidate


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_persistence_records_fail_closed_for_invalid_values() -> None:
    candidate = high_cash_candidate()

    with pytest.raises(ValueError, match="evidence_hash is required"):
        CandidatePersistenceRecord(
            candidate=candidate, evidence_hash=" ", persisted_at_utc=EVENT_TIME
        )
    with pytest.raises(ValueError, match="persisted_at_utc must be timezone-aware"):
        CandidatePersistenceRecord(
            candidate=candidate,
            evidence_hash="sha256:evidence",
            persisted_at_utc=datetime(2026, 6, 21, 10, 0),
        )
    with pytest.raises(ValueError, match="changed_at_utc must be UTC"):
        LifecycleHistoryEntry(
            candidate_id=candidate.candidate_id,
            source_status=IdeaLifecycleStatus.DETECTED,
            target_status=IdeaLifecycleStatus.ENRICHED,
            actor_subject="worker-1",
            changed_at_utc=datetime(2026, 6, 21, 11, 0, tzinfo=timezone(timedelta(hours=1))),
        )


def test_persistence_public_prechecks_treat_missing_idempotency_as_absent() -> None:
    repository = InMemoryIdeaRepository()

    assert (
        repository.precheck_review_mutation(
            idempotency_key="missing-review-idempotency",
            payload={"reviewId": "review-001"},
        )
        is None
    )
    assert (
        repository.precheck_conversion_mutation(
            idempotency_key="missing-conversion-idempotency",
            payload={"conversionIntentId": "conversion-001"},
        )
        is None
    )
