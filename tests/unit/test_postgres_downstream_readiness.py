from __future__ import annotations

from typing import Any

from app.infrastructure.postgres_downstream_readiness import (
    load_downstream_realization_readiness_summary,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection


def test_postgres_repository_uses_downstream_only_readiness_projection() -> None:
    connection = FakePostgresConnection()
    connection.rows["idea_conversion_intent"] = [{}, {}]
    connection.rows["idea_conversion_outcome"] = [{}]
    connection.rows["idea_report_evidence_pack_request"] = [{}, {}, {}]

    summary = PostgresIdeaRepository(connection).downstream_realization_readiness_summary()

    executed_sql = " ".join(connection.executed_sql)
    assert summary.conversion_intent_count == 2
    assert summary.conversion_outcome_count == 1
    assert summary.report_evidence_pack_request_count == 3
    assert "/* lotus-idea downstream-realization-readiness-summary */" in executed_sql
    assert "from idea_conversion_intent" in executed_sql
    assert "from idea_conversion_outcome" in executed_sql
    assert "from idea_report_evidence_pack_request" in executed_sql
    for unrelated_table in (
        "idea_candidate_record",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_review_decision",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
    ):
        assert unrelated_table not in executed_sql


def test_downstream_readiness_summary_returns_zeroes_without_count_row() -> None:
    summary = load_downstream_realization_readiness_summary(EmptyReadinessConnection())

    assert summary.conversion_intent_count == 0
    assert summary.conversion_outcome_count == 0
    assert summary.report_evidence_pack_request_count == 0


class EmptyReadinessConnection:
    def cursor(self) -> "EmptyReadinessCursor":
        return EmptyReadinessCursor()


class EmptyReadinessCursor:
    def execute(self, query: str, params: object | None = None) -> None:
        del query, params

    def fetchall(self) -> list[dict[str, Any]]:
        return []

    def __enter__(self) -> "EmptyReadinessCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None
