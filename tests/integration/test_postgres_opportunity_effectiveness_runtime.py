from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from app.application.opportunity_effectiveness import (
    build_opportunity_effectiveness_snapshot,
    build_opportunity_effectiveness_snapshot_from_summary,
)
from app.domain import OpportunityFamily
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.support.opportunity_effectiveness_fixture import (
    FIXTURE_EVALUATED_AT,
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    candidate_fixture,
    golden_effectiveness_snapshot,
    record_fixture,
    snapshot_fixture,
)


def test_postgres_effectiveness_matches_golden_methodology_and_isolates_tenant(
    postgres_database_url: str,
) -> None:
    golden = golden_effectiveness_snapshot()
    other_tenant = record_fixture(
        candidate_fixture(
            "idea-other-tenant-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("99"),
            created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
            tenant_id="tenant-b",
        )
    )
    persisted = snapshot_fixture(*golden.candidate_records.values(), other_tenant)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        repository.replace_snapshot(persisted)
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-a",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )
        other_tenant_summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-b",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    expected = build_opportunity_effectiveness_snapshot(
        persisted,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-a",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected
    assert actual.snapshot_digest == expected.snapshot_digest
    assert other_tenant_summary.generated_opportunity_count == 1
    assert other_tenant_summary.family_counts == {OpportunityFamily.HIGH_CASH.value: 1}


def test_postgres_effectiveness_empty_cohort_matches_in_memory_methodology(
    postgres_database_url: str,
) -> None:
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        summary = repository.opportunity_effectiveness_summary(
            tenant_id="tenant-with-no-opportunities",
            window_start_utc=FIXTURE_WINDOW_START,
            window_end_utc=FIXTURE_WINDOW_END,
            evaluated_at_utc=FIXTURE_EVALUATED_AT,
            max_opportunities=100,
        )

    actual = build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id="tenant-with-no-opportunities",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )
    expected = build_opportunity_effectiveness_snapshot(
        snapshot_fixture(),
        tenant_id="tenant-with-no-opportunities",
        window_start_utc=FIXTURE_WINDOW_START,
        window_end_utc=FIXTURE_WINDOW_END,
        evaluated_at_utc=FIXTURE_EVALUATED_AT,
        max_opportunities=100,
    )

    assert actual == expected
