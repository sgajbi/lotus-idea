from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from app.application.candidate_expiry import (
    CandidateExpiryDecision,
    ExpireCandidateCommand,
    expire_candidate_if_due,
)
from app.application.source_ingestion import (
    IngestHighCashSourceSignalCommand,
    ingest_high_cash_signal_from_core,
)
from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    SourceRef,
    SourceSystem,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.main import app
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
)
from app.runtime.repository_state import (
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
    table_count,
)
from tests.support.http import managed_test_client
from tests.support.opportunity_effectiveness_fixture import candidate_fixture


_EXPIRY_TABLES = frozenset(
    {"idea_candidate_record", "idea_lifecycle_history", "idea_audit_event", "idea_outbox_event"}
)


def _table_count(database_url: str, table_name: str) -> int:
    return table_count(database_url, table_name, allowed_tables=_EXPIRY_TABLES)


def _review_queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-postgres-expiry-queue",
    }


def test_postgres_runtime_expires_resolved_candidate_and_removes_it_from_queue(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    created = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-high-cash-expiry-created"),
    )
    assert created.status_code == 200
    candidate_id = str(created.json()["persistence"]["candidateId"])
    resolved_payload = high_cash_payload()
    resolved_payload["sourceReportedCashWeight"] = "0.10"

    resolved = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=resolved_payload,
        headers=persistence_headers("postgres-high-cash-expiry-resolved"),
    )
    reset_idea_repository_for_tests(reload_from_environment=True)
    queue = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T11:00:00Z"},
        headers=_review_queue_headers(),
    )

    assert resolved.status_code == 200
    assert resolved.json()["evaluation"]["outcome"] == "not_eligible"
    assert resolved.json()["persistence"] is None
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
    assert len(record.lifecycle_history) == 1
    assert record.audit_events[-1].attributes["reason_codes"] == (
        "opportunity_no_longer_eligible,below_materiality"
    )
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_lifecycle_history") == 1
    assert queue.status_code == 200
    assert queue.json()["items"] == []


@dataclass
class _CoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence

    def fetch_high_cash_evidence(
        self,
        request: CoreHighCashEvidenceRequest,
    ) -> CoreHighCashEvidence:
        return self.evidence


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _core_evidence(cash_weight: Decimal) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=_source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def _ingestion_command(idempotency_key: str) -> IngestHighCashSourceSignalCommand:
    return IngestHighCashSourceSignalCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
        correlation_id="corr-postgres-expiry",
        trace_id="trace-postgres-expiry",
    )


def test_postgres_runtime_serializes_concurrent_authoritative_expiry(
    postgres_database_url: str,
) -> None:
    created = ingest_high_cash_signal_from_core(
        _ingestion_command("postgres-high-cash-expiry-seed"),
        core_source=_CoreSource(_core_evidence(Decimal("0.18"))),
        repository=get_idea_repository(),
    )
    assert created.signal_result.persistence is not None
    assert created.signal_result.persistence.record is not None
    candidate_id = created.signal_result.persistence.record.candidate.candidate_id
    before = {
        table: _table_count(postgres_database_url, table)
        for table in ("idea_lifecycle_history", "idea_audit_event", "idea_outbox_event")
    }
    command = replace(
        _ingestion_command("placeholder"),
        evaluated_at_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
    )

    decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: _concurrent_expiry_decision(
            repository,
            replace(command, idempotency_key=key),
        ),
        ("postgres-high-cash-expiry-race-a", "postgres-high-cash-expiry-race-b"),
    )

    assert set(decisions) == {
        CandidateExpiryDecision.EXPIRED,
        CandidateExpiryDecision.ALREADY_EXPIRED,
    }
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        record = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(candidate_id)
    assert record is not None
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
    assert len(record.lifecycle_history) == 1
    for table, count in before.items():
        assert _table_count(postgres_database_url, table) == count + 1


def test_postgres_runtime_serializes_concurrent_due_applicability_expiry(
    postgres_database_url: str,
) -> None:
    expiry = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)
    candidate = candidate_fixture(
        "idea-candidate-due-expiry-001",
        family=OpportunityFamily.BOND_MATURITY,
        score=Decimal("80"),
        created_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    )
    candidate = replace(
        candidate,
        evidence_packet=replace(
            candidate.evidence_packet,
            applicability_expires_at_utc=expiry,
        ),
    )
    persisted = get_idea_repository().persist_candidate(
        candidate,
        idempotency_key="postgres-due-expiry-seed",
        payload={"candidate_id": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=candidate.created_at_utc,
    )
    assert persisted.record is not None
    before = {
        table: _table_count(postgres_database_url, table)
        for table in ("idea_lifecycle_history", "idea_audit_event", "idea_outbox_event")
    }

    decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, _: (
            expire_candidate_if_due(
                ExpireCandidateCommand(
                    candidate_id=candidate.candidate_id,
                    actor_subject="candidate-expiry-worker",
                    evaluated_at_utc=expiry,
                    reason_codes=(ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE,),
                ),
                repository=repository,
            ).decision
        ),
        ("postgres-due-expiry-race-a", "postgres-due-expiry-race-b"),
    )

    assert set(decisions) == {
        CandidateExpiryDecision.EXPIRED,
        CandidateExpiryDecision.ALREADY_EXPIRED,
    }
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        record = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(
            candidate.candidate_id
        )
    assert record is not None
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
    assert len(record.lifecycle_history) == 1
    assert record.audit_events[-1].attributes["reason_codes"] == (
        ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE.value
    )
    for table, count in before.items():
        assert _table_count(postgres_database_url, table) == count + 1


def _concurrent_expiry_decision(
    repository: PostgresIdeaRepository,
    command: IngestHighCashSourceSignalCommand,
) -> CandidateExpiryDecision:
    result = ingest_high_cash_signal_from_core(
        command,
        core_source=_CoreSource(_core_evidence(Decimal("0.10"))),
        repository=repository,
    )
    assert result.signal_result.expiry is not None
    return result.signal_result.expiry.decision
