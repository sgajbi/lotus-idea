from __future__ import annotations

from typing import Any, Protocol, Sequence

from app.infrastructure.postgres_codecs import read_row_value
from app.ports.idea_repository import DownstreamRealizationReadinessRepositorySummary


class PostgresCursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...

    def fetchall(self) -> Sequence[Any]: ...

    def __enter__(self) -> PostgresCursor: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class PostgresConnection(Protocol):
    def cursor(self) -> PostgresCursor: ...


def load_downstream_realization_readiness_summary(
    connection: PostgresConnection,
) -> DownstreamRealizationReadinessRepositorySummary:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea downstream-realization-readiness-summary */
            SELECT
                (SELECT COUNT(*) FROM idea_conversion_intent)::integer
                    AS conversion_intent_count,
                (SELECT COUNT(*) FROM idea_conversion_outcome)::integer
                    AS conversion_outcome_count,
                (SELECT COUNT(*) FROM idea_report_evidence_pack_request)::integer
                    AS report_evidence_pack_request_count
            """
        )
        rows = cursor.fetchall()
    if not rows:
        return DownstreamRealizationReadinessRepositorySummary(
            conversion_intent_count=0,
            conversion_outcome_count=0,
            report_evidence_pack_request_count=0,
        )
    row = rows[0]
    return DownstreamRealizationReadinessRepositorySummary(
        conversion_intent_count=read_row_value(row, "conversion_intent_count"),
        conversion_outcome_count=read_row_value(row, "conversion_outcome_count"),
        report_evidence_pack_request_count=read_row_value(
            row, "report_evidence_pack_request_count"
        ),
    )
