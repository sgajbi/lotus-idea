from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.data_lifecycle import ExecuteDataLifecycle  # noqa: E402
from app.domain.data_lifecycle import (  # noqa: E402
    DataLifecycleAction,
    DataLifecycleCommand,
    DataLifecycleDecision,
)
from app.domain.ideas import IdeaCandidate  # noqa: E402
from app.infrastructure.postgres_repository import (  # noqa: E402
    PostgresConnection,
    PostgresIdeaRepository,
)
from scripts.postgres_disaster_recovery_fixture_data import (  # noqa: E402
    high_cash_candidate,
)

DATABASE_URL_ENV = "LOTUS_IDEA_DATABASE_URL"
FIXTURE_TIME = datetime(2026, 7, 12, 4, 0, tzinfo=UTC)
FIXTURE_CANDIDATE_PREFIX = "idea_scheduled_lifecycle_fixture"


def seed_scheduled_data_lifecycle_fixture(
    database_url: str,
    *,
    confirm_disposable_database: bool,
    connect: Any = psycopg.connect,
) -> dict[str, int]:
    if not confirm_disposable_database:
        raise ValueError("explicit disposable-database confirmation is required")
    with connect(database_url, row_factory=dict_row) as connection:
        _assert_empty_candidate_store(connection)
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        candidates = tuple(
            replace(
                high_cash_candidate(),
                candidate_id=f"{FIXTURE_CANDIDATE_PREFIX}_{posture}",
            )
            for posture in ("ready", "held", "active_delivery")
        )
        for index, candidate in enumerate(candidates):
            _persist_candidate(repository, candidate, index=index)
        ready, held, _active_delivery = candidates
        _mark_candidate_outbox_published(connection, (ready.candidate_id, held.candidate_id))
        _apply_lifecycle_action(repository, ready, DataLifecycleAction.ERASE, sequence=1)
        _apply_lifecycle_action(repository, held, DataLifecycleAction.ERASE, sequence=2)
        _apply_lifecycle_action(repository, held, DataLifecycleAction.APPLY_HOLD, sequence=3)
        _expire_fixture_controls(connection)
        return _fixture_state_counts(connection)


def _assert_empty_candidate_store(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS candidate_count FROM idea_candidate_record")
        row = cursor.fetchone()
    if not isinstance(row, dict) or int(row["candidate_count"]) != 0:
        raise ValueError("scheduled lifecycle fixture requires an empty disposable database")


def _persist_candidate(
    repository: PostgresIdeaRepository,
    candidate: IdeaCandidate,
    *,
    index: int,
) -> None:
    result = repository.persist_candidate(
        candidate,
        idempotency_key=f"scheduled-lifecycle-fixture-persist-{index}",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="scheduled-lifecycle-fixture-ingestion",
        occurred_at_utc=FIXTURE_TIME,
    )
    if result.record is None:
        raise RuntimeError("scheduled lifecycle fixture candidate was not persisted")


def _mark_candidate_outbox_published(connection: Any, candidate_ids: tuple[str, ...]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE idea_outbox_event
               SET status = 'published',
                   published_at_utc = %s,
                   failure_reason = NULL,
                   lease_owner = NULL,
                   lease_attempt_id = NULL,
                   lease_expires_at_utc = NULL
               WHERE aggregate_type = 'idea_candidate'
                 AND aggregate_id = ANY(%s::text[])""",
            (FIXTURE_TIME + timedelta(minutes=1), list(candidate_ids)),
        )
        if cursor.rowcount != len(candidate_ids):
            raise RuntimeError("scheduled lifecycle fixture outbox publication drifted")
    connection.commit()


def _apply_lifecycle_action(
    repository: PostgresIdeaRepository,
    candidate: IdeaCandidate,
    action: DataLifecycleAction,
    *,
    sequence: int,
) -> None:
    is_hold = action is DataLifecycleAction.APPLY_HOLD
    result = ExecuteDataLifecycle(
        repository,
        now=lambda: FIXTURE_TIME + timedelta(minutes=sequence + 1),
    ).execute(
        DataLifecycleCommand(
            candidate_id=candidate.candidate_id,
            tenant_id="tenant-dr-fixture",
            action=action,
            actor_subject="synthetic-privacy-reviewer",
            approver_subject=None if is_hold else "synthetic-privacy-approver",
            authority_ref=(
                "bank-legal-and-records-governance:synthetic-fixture-hold"
                if is_hold
                else "bank-privacy-governance:synthetic-fixture-erasure"
            ),
            reason="synthetic_scheduled_lifecycle_proof",
            change_reference=f"synthetic-lifecycle-fixture-{sequence}",
            idempotency_key=f"scheduled-lifecycle-fixture-action-{sequence}",
            request_fingerprint=f"{sequence}" * 64,
            correlation_id=f"corr-scheduled-lifecycle-fixture-{sequence}",
            trace_id=f"trace-scheduled-lifecycle-fixture-{sequence}",
            requested_at_utc=FIXTURE_TIME + timedelta(minutes=sequence),
            dry_run=False,
        )
    )
    if result.decision is not DataLifecycleDecision.APPLIED:
        raise RuntimeError("scheduled lifecycle fixture action was not applied")


def _expire_fixture_controls(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE idea_data_lifecycle_control
               SET retention_expires_at_utc = %s
               WHERE candidate_id LIKE %s""",
            (FIXTURE_TIME - timedelta(days=1), f"{FIXTURE_CANDIDATE_PREFIX}%"),
        )
        if cursor.rowcount != 3:
            raise RuntimeError("scheduled lifecycle fixture expiry inventory drifted")
    connection.commit()


def _fixture_state_counts(connection: Any) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT state, COUNT(*) AS state_count
               FROM idea_data_lifecycle_control
               WHERE candidate_id LIKE %s
               GROUP BY state
               ORDER BY state""",
            (f"{FIXTURE_CANDIDATE_PREFIX}%",),
        )
        rows = cursor.fetchall()
    return {str(row["state"]): int(row["state_count"]) for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed disposable scheduled lifecycle proof state")
    parser.add_argument("--confirm-disposable-database", action="store_true")
    args = parser.parse_args()
    database_url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if not database_url:
        print(f"Scheduled lifecycle fixture requires {DATABASE_URL_ENV}")
        return 1
    try:
        counts = seed_scheduled_data_lifecycle_fixture(
            database_url,
            confirm_disposable_database=args.confirm_disposable_database,
        )
    except (OSError, TypeError, ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"Scheduled lifecycle fixture failed: {type(exc).__name__}")
        return 1
    print(f"Scheduled lifecycle fixture seeded: state_counts={counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
