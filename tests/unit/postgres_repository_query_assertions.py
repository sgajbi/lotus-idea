from __future__ import annotations

from collections.abc import Iterable


def assert_no_whole_store_snapshot(executed_sql: Iterable[str]) -> None:
    combined = "\n".join(executed_sql)
    assert "order by candidate.persisted_at_utc, candidate.candidate_id" not in combined
    assert "order by created_at_utc, idempotency_key" not in combined
    assert "order by occurred_at_utc, outbox_event_id" not in combined
