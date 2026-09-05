from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import psycopg
from psycopg.rows import dict_row

from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeReportEvidencePackCommand,
    submit_report_evidence_pack_to_downstream,
)
from app.application.report_materialization_reconciliation import (
    ReconcileReportMaterializationCommand,
    ReportMaterializationReconciliationStatus,
    reconcile_report_materialization_receipt,
)
from app.domain import GovernedReportEvidencePack, ReviewAccessScope
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.ports.downstream_realization import DownstreamOwnerReceipt, DownstreamRealizationOutcome
from tests.support.report_materialization import authoritative_report_outcome
from tests.unit.test_downstream_realization_application import (
    AUTHORIZED_SCOPE_FILTER,
    repository_with_report_pack,
)


RECORDED_AT = datetime(2026, 9, 5, 15, 30, tzinfo=UTC)


@dataclass
class _LostResponseClient:
    call_count: int = 0

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.call_count += 1
        raise TimeoutError("Report committed before the response was lost")


@dataclass
class _CountingReader:
    receipt: DownstreamOwnerReceipt
    call_count: int = 0

    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        self.call_count += 1
        assert evidence_pack.report_evidence_pack_id == "report-evidence-pack-001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        assert idempotency_key == "postgres-report-recovery-001"
        return self.receipt


def test_postgres_report_receipt_recovery_survives_restart_and_exactly_replays(
    postgres_database_url: str,
) -> None:
    source_repository = repository_with_report_pack()
    evidence_pack = source_repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    submit_client = _LostResponseClient()

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.replace_snapshot(source_repository.snapshot())
        submission = submit_report_evidence_pack_to_downstream(
            RealizeReportEvidencePackCommand(
                report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
                idempotency_key="postgres-report-recovery-001",
                actor_subject="advisor-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                submitted_at_utc=RECORDED_AT,
            ),
            repository=repository,
            report_client=submit_client,
        )
        assert submission.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
        assert submission.support_reference is not None
        support_reference = submission.support_reference

    owner_outcome = authoritative_report_outcome(evidence_pack)
    assert owner_outcome.owner_receipt is not None
    reader = _CountingReader(owner_outcome.owner_receipt)
    command = ReconcileReportMaterializationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        accepted_at_utc=RECORDED_AT,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        accepted = reconcile_report_materialization_receipt(
            command,
            repository=restarted,
            report_reader=reader,
        )
        assert accepted.status is ReportMaterializationReconciliationStatus.ACCEPTED
        assert accepted.owner_receipt is not None
        assert (
            accepted.owner_receipt.owner_request_id == owner_outcome.owner_receipt.owner_request_id
        )
        assert (
            accepted.owner_receipt.owner_realization_id
            == owner_outcome.owner_receipt.owner_realization_id
        )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted_again = PostgresIdeaRepository(cast(PostgresConnection, connection))
        replayed = reconcile_report_materialization_receipt(
            command,
            repository=restarted_again,
            report_reader=reader,
        )
        persisted = restarted_again.downstream_submission_by_support_reference(support_reference)
        assert replayed.status is ReportMaterializationReconciliationStatus.REPLAYED
        assert replayed.owner_receipt == accepted.owner_receipt
        assert persisted is not None
        assert persisted.owner_receipt == accepted.owner_receipt
        assert persisted.updated_at_utc == RECORDED_AT
        assert persisted.audit_history[-1].occurred_at_utc == RECORDED_AT

    assert submit_client.call_count == 1
    assert reader.call_count == 1
