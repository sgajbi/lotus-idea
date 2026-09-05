from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

import pytest

from app.domain import (
    CandidatePresentationReceipt,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
)
from app.infrastructure.postgres_presentation_receipts import _record_presentation_receipt
from app.infrastructure.postgres_presentation_receipts import (
    PostgresPresentationReceiptRepositoryMixin,
)


def test_postgres_receipt_insert_is_candidate_tenant_and_version_fenced() -> None:
    connection = _Connection([[{"receipt_id": "receipt-0001"}]])

    result = _record_presentation_receipt(connection, _receipt())

    assert result.decision is PresentationReceiptDecision.ACCEPTED
    assert connection.commits == 1
    assert connection.rollbacks == 0
    sql = connection.cursor_instance.executed_sql[0]
    assert "candidate_json->'access_scope'->>'tenant_id' = %s" in sql
    assert "candidate_json->'identity'->>'material_version'" in sql
    assert "candidate_json->'identity'->>'evidence_version'" in sql
    assert "updated_at_utc <= %s" in sql
    assert "ON CONFLICT (receipt_id) DO NOTHING" in sql


def test_postgres_receipt_replay_lookup_is_candidate_and_tenant_scoped() -> None:
    connection = _Connection([[], []])

    with pytest.raises(PresentationReceiptCandidateStateError):
        _record_presentation_receipt(connection, _receipt())

    lookup_sql = connection.cursor_instance.executed_sql[1]
    assert "receipt_id = %s" in lookup_sql
    assert "candidate_id = %s" in lookup_sql
    assert "tenant_id = %s" in lookup_sql


def test_postgres_receipt_exact_replay_survives_repository_restart() -> None:
    receipt = _receipt()
    connection = _Connection([[], [_row(receipt)]])

    result = _record_presentation_receipt(connection, receipt)

    assert result.decision is PresentationReceiptDecision.REPLAYED
    assert result.receipt == receipt
    assert connection.commits == 1


def test_postgres_receipt_identity_conflict_returns_existing_immutable_receipt() -> None:
    existing = _receipt()
    connection = _Connection([[], [_row(existing)]])

    result = _record_presentation_receipt(
        connection,
        _receipt(rank_at_presentation=3),
    )

    assert result.decision is PresentationReceiptDecision.CONFLICT
    assert result.receipt == existing
    assert connection.commits == 1


def test_postgres_receipt_candidate_state_mismatch_rolls_back() -> None:
    connection = _Connection([[], []])

    with pytest.raises(PresentationReceiptCandidateStateError):
        _record_presentation_receipt(connection, _receipt())

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_postgres_receipt_scoped_lookup_returns_only_exact_candidate_tenant_match() -> None:
    receipt = _receipt()
    repository = _ReceiptRepository(_Connection([[_row(receipt)]]))

    assert (
        repository.presentation_receipt_by_id(
            receipt.receipt_id,
            candidate_id=receipt.candidate_id,
            tenant_id=receipt.tenant_id,
        )
        == receipt
    )
    assert repository.connection.cursor_instance.executed_params[0] == (
        receipt.receipt_id,
        receipt.candidate_id,
        receipt.tenant_id,
    )

    missing_repository = _ReceiptRepository(_Connection([[]]))
    assert (
        missing_repository.presentation_receipt_by_id(
            "receipt-missing",
            candidate_id=receipt.candidate_id,
            tenant_id=receipt.tenant_id,
        )
        is None
    )


def test_postgres_receipt_repository_delegates_mutation_with_observability() -> None:
    repository = _ReceiptRepository(_Connection([[{"receipt_id": "receipt-0001"}]]))

    result = repository.record_presentation_receipt(_receipt())

    assert result.decision is PresentationReceiptDecision.ACCEPTED
    assert repository.connection.commits == 1


class _Cursor:
    def __init__(self, results: list[Sequence[Any]]) -> None:
        self._results = results
        self._current: Sequence[Any] = ()
        self.executed_sql: list[str] = []
        self.executed_params: list[Sequence[Any] | None] = []

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        self.executed_sql.append(query)
        self.executed_params.append(params)
        self._current = self._results.pop(0)

    def fetchall(self) -> Sequence[Any]:
        return self._current

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _Connection:
    def __init__(self, results: list[Sequence[Any]]) -> None:
        self.cursor_instance = _Cursor(results)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> _Cursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _ReceiptRepository(PostgresPresentationReceiptRepositoryMixin):
    def __init__(self, connection: _Connection) -> None:
        self._connection = connection
        self.connection = connection


def _receipt(**overrides: Any) -> CandidatePresentationReceipt:
    values: dict[str, Any] = {
        "receipt_id": "receipt-0001",
        "candidate_id": "candidate-0001",
        "tenant_id": "tenant-0001",
        "presented_at_utc": datetime(2026, 8, 30, 12, tzinfo=UTC),
        "rank_at_presentation": 2,
        "visible_candidate_count": 7,
        "queue_snapshot_digest": f"sha256:{'a' * 64}",
        "queue_policy_version": "idea-review-queue-v1",
        "ranking_policy_version": "idea-score-v2",
        "candidate_material_version": 1,
        "candidate_evidence_version": 1,
        "accepted_at_utc": datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return CandidatePresentationReceipt(**values)


def _row(receipt: CandidatePresentationReceipt) -> dict[str, Any]:
    return {
        "receipt_id": receipt.receipt_id,
        "candidate_id": receipt.candidate_id,
        "tenant_id": receipt.tenant_id,
        "presented_at_utc": receipt.presented_at_utc,
        "rank_at_presentation": receipt.rank_at_presentation,
        "visible_candidate_count": receipt.visible_candidate_count,
        "queue_snapshot_digest": receipt.queue_snapshot_digest,
        "queue_policy_version": receipt.queue_policy_version,
        "ranking_policy_version": receipt.ranking_policy_version,
        "candidate_material_version": receipt.candidate_material_version,
        "candidate_evidence_version": receipt.candidate_evidence_version,
        "accepted_at_utc": receipt.accepted_at_utc,
        "acceptance_time_source": receipt.acceptance_time_source.value,
        "schema_version": receipt.schema_version,
        "surface": receipt.surface,
        "producer": receipt.producer,
    }
