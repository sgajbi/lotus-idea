from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import psycopg

from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    ReviewAccessScope,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)
from tests.integration.postgres_runtime_support import run_concurrent_repository_mutations


def test_postgres_runtime_serializes_candidate_identity_and_idempotency_races(
    postgres_database_url: str,
) -> None:
    candidate = _high_cash_candidate("postgres-concurrent-candidate-same-key")

    same_key_results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: repository.persist_candidate(
            candidate,
            idempotency_key=key,
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        ),
        ("candidate:postgres-concurrent-same-key",) * 2,
    )

    assert {result.decision for result in same_key_results} == {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.REPLAYED,
    }

    duplicate_candidate = _high_cash_candidate("postgres-concurrent-candidate-different-keys")
    different_key_results = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: repository.persist_candidate(
            duplicate_candidate,
            idempotency_key=key,
            payload={"candidateId": duplicate_candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        ),
        ("candidate:postgres-concurrent-first", "candidate:postgres-concurrent-second"),
    )

    assert {result.decision for result in different_key_results} == {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
    }
    assert _table_count(postgres_database_url, "idea_candidate_record") == 2
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 2
    assert _table_count(postgres_database_url, "idea_audit_event") == 2
    assert _table_count(postgres_database_url, "idea_outbox_event") == 2


def _high_cash_candidate(candidate_id: str) -> IdeaCandidate:
    evaluated_at = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    source_refs = tuple(
        SourceRef(
            product_id=product_id,
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route=f"/source/{product_id}",
            as_of_date=date(2026, 6, 21),
            generated_at_utc=evaluated_at,
            content_hash=f"sha256:{product_id}",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )
        for product_id in (
            "lotus-core:PortfolioStateSnapshot:v1",
            "lotus-core:HoldingsAsOf:v1",
            "lotus-core:PortfolioCashMovementSummary:v1",
            "lotus-core:PortfolioCashflowProjection:v1",
        )
    )
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=date(2026, 6, 21),
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=source_refs[0],
            holdings_ref=source_refs[1],
            cash_movement_ref=source_refs[2],
            cashflow_projection_ref=source_refs[3],
            evaluated_at_utc=evaluated_at,
            access_scope=ReviewAccessScope(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                client_id="client-001",
            ),
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    assert result.candidate is not None
    return replace(result.candidate, candidate_id=candidate_id)


def _table_count(database_url: str, table_name: str) -> int:
    allowed_tables = {
        "idea_candidate_record",
        "idea_idempotency_record",
        "idea_audit_event",
        "idea_outbox_event",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported test table: {table_name}")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])
