from __future__ import annotations

from datetime import datetime

from app.domain.persistence_models import IdeaRepositorySnapshot


def operation_name(idempotency_key: str) -> str:
    return idempotency_key.split(":", 1)[0]


def idempotency_created_at(
    candidate_id: str | None,
    snapshot: IdeaRepositorySnapshot,
) -> datetime:
    if candidate_id is not None and candidate_id in snapshot.candidate_records:
        return snapshot.candidate_records[candidate_id].persisted_at_utc
    return datetime.now().astimezone()
