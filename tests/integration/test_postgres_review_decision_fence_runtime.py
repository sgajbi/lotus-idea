from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
from tests.support.http import managed_test_client

from app.domain import (
    InvalidReviewAction,
    ReasonCode,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    apply_review_action,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
    table_count,
)


TRACKED_TABLES = frozenset(
    {
        "idea_review_decision",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_idempotency_record",
    }
)


def test_postgres_fences_competing_review_decisions(
    postgres_database_url: str,
) -> None:
    candidate_id = _persist_review_ready_candidate()
    candidate = _load_candidate(postgres_database_url, candidate_id)
    actor = _actor_for(candidate)
    competing_results = {
        "review:competing:approve": apply_review_action(
            candidate,
            _review_command(
                review_id="postgres-competing-approval-001",
                action=ReviewAction.APPROVE_FOR_CONVERSION,
                actor=actor,
            ),
        ),
        "review:competing:reject": apply_review_action(
            candidate,
            _review_command(
                review_id="postgres-competing-rejection-001",
                action=ReviewAction.REJECT,
                actor=actor,
            ),
        ),
    }
    before_counts = _tracked_counts(postgres_database_url)

    def persist(
        repository: PostgresIdeaRepository,
        idempotency_key: str,
    ) -> ReviewPersistenceDecision | InvalidReviewAction:
        result = competing_results[idempotency_key]
        try:
            return repository.record_review_action(
                result,
                idempotency_key=idempotency_key,
                payload={"reviewId": result.decision.review_id},
            ).decision
        except InvalidReviewAction as exc:
            return exc

    outcomes = run_concurrent_repository_mutations(
        postgres_database_url,
        persist,
        ("review:competing:approve", "review:competing:reject"),
    )

    assert sum(outcome is ReviewPersistenceDecision.ACCEPTED for outcome in outcomes) == 1
    stale_conflict = next(
        outcome for outcome in outcomes if isinstance(outcome, InvalidReviewAction)
    )
    assert stale_conflict.code == "review_action_conflict"
    assert _tracked_counts(postgres_database_url) == {
        table: count + 1 for table, count in before_counts.items()
    }
    record = _load_record(postgres_database_url, candidate_id)
    assert len(record.review_decisions) == 1
    assert record.review_decisions[0].resulting_posture is record.candidate.review_posture


def _persist_review_ready_candidate() -> str:
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-review-decision-fence-persist-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    for minute, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transitioned = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json={
                "transitionId": f"postgres-review-fence-{target_status}-001",
                "targetLifecycleStatus": target_status,
                "reasonCodes": ["review_required"],
                "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
            },
            headers={
                "X-Caller-Subject": "idea-lifecycle-worker",
                "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
                "X-Correlation-Id": "corr-postgres-review-decision-fence",
                "X-Trace-Id": f"trace-postgres-review-fence-{target_status}",
                "Idempotency-Key": f"postgres-review-fence-{target_status}-001",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["persistence"]["decision"] == "accepted"
        reset_idea_repository_for_tests(reload_from_environment=True)
    return candidate_id


def _review_command(
    *,
    review_id: str,
    action: ReviewAction,
    actor: ReviewActorContext,
) -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id=review_id,
        action=action,
        actor=actor,
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
    )


def _actor_for(candidate: Any) -> ReviewActorContext:
    scope = candidate.access_scope
    assert scope is not None
    return ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({scope.tenant_id}),
        book_ids=frozenset({scope.book_id}),
        portfolio_ids=frozenset({scope.portfolio_id}),
        client_ids=frozenset({scope.client_id}),
    )


def _load_candidate(database_url: str, candidate_id: str) -> Any:
    return _load_record(database_url, candidate_id).candidate


def _load_record(database_url: str, candidate_id: str) -> Any:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        record = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(candidate_id)
    assert record is not None
    return record


def _tracked_counts(database_url: str) -> dict[str, int]:
    return {
        table: table_count(database_url, table, allowed_tables=TRACKED_TABLES)
        for table in TRACKED_TABLES
    }
