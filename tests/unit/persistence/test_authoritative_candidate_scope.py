from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain import InMemoryIdeaRepository, UnscopedCandidatePersistenceError
from tests.unit.test_idea_persistence import EVALUATED_AT, high_cash_candidate


@pytest.mark.parametrize("field_name", ("tenant_id", "book_id", "portfolio_id", "client_id"))
@pytest.mark.parametrize("placeholder", ("unknown", " UNKNOWN "))
def test_persist_candidate_rejects_placeholder_scope_before_any_mutation(
    field_name: str,
    placeholder: str,
) -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    assert candidate.access_scope is not None
    invalid_scope = replace(candidate.access_scope, **{field_name: placeholder})

    with pytest.raises(
        UnscopedCandidatePersistenceError,
        match="candidate access scope must be authoritative for persistence",
    ):
        repository.persist_candidate(
            replace(candidate, access_scope=invalid_scope),
            idempotency_key=f"signal-ingestion:placeholder-scope:{field_name}",
            payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )

    snapshot = repository.snapshot()
    assert snapshot.candidate_records == {}
    assert snapshot.idempotency_records == {}
    assert snapshot.idempotency_candidates == {}
    assert snapshot.outbox_events == {}
