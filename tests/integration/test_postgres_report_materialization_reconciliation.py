from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import cast

import psycopg
from psycopg.rows import dict_row
import pytest

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
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationNotObserved,
    DownstreamRealizationOutcome,
)
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
class _AcceptedResponseClient:
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
        return authoritative_report_outcome(evidence_pack)


@dataclass
class _CountingReader:
    receipt: DownstreamOwnerReceipt
    expected_idempotency_key: str
    call_count: int = 0
    acceptance_observed: bool = True
    _call_count_lock: Lock = field(default_factory=Lock, repr=False)

    def recover_report_evidence_pack_receipt(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str,
    ) -> DownstreamOwnerReceipt:
        with self._call_count_lock:
            self.call_count += 1
        assert evidence_pack.report_evidence_pack_id == "report-evidence-pack-001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        assert idempotency_key == self.expected_idempotency_key
        if not self.acceptance_observed:
            raise DownstreamRealizationNotObserved(
                "Report has no materialization for this evidence pack"
            )
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
    reader = _CountingReader(
        owner_outcome.owner_receipt,
        expected_idempotency_key="postgres-report-recovery-001",
        acceptance_observed=False,
    )
    command = ReconcileReportMaterializationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        accepted_at_utc=RECORDED_AT,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        before = restarted.downstream_submission_by_support_reference(support_reference)
        not_observed = reconcile_report_materialization_receipt(
            command,
            repository=restarted,
            report_reader=reader,
        )
        unchanged = restarted.downstream_submission_by_support_reference(support_reference)
        assert (
            not_observed.status
            is ReportMaterializationReconciliationStatus.OWNER_ACCEPTANCE_NOT_OBSERVED
        )
        assert unchanged == before

    reader.acceptance_observed = True
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
    assert reader.call_count == 3


def test_postgres_recovers_owner_acceptance_after_local_finalize_failure_and_restart(
    postgres_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_repository = repository_with_report_pack()
    evidence_pack = source_repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    submit_client = _AcceptedResponseClient()

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.replace_snapshot(source_repository.snapshot())

        def fail_finalize(**_: object) -> None:
            raise RuntimeError("simulated Idea commit failure after Report acceptance")

        monkeypatch.setattr(repository, "finalize_downstream_submission", fail_finalize)
        submission = submit_report_evidence_pack_to_downstream(
            RealizeReportEvidencePackCommand(
                report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
                idempotency_key="postgres-report-finalize-failure-001",
                actor_subject="advisor-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                submitted_at_utc=RECORDED_AT,
            ),
            repository=repository,
            report_client=submit_client,
        )
        assert submission.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
        assert submission.downstream_failure_reason == "downstream_submission_finalization_failed"
        assert submission.support_reference is not None
        support_reference = submission.support_reference
        pending = repository.downstream_submission_by_support_reference(support_reference)
        assert pending is not None
        assert pending.status.value == "in_flight"
        assert pending.owner_receipt is None
        assert pending.attempt_count == 1
        assert [entry.action.value for entry in pending.audit_history] == ["claimed"]

    owner_outcome = authoritative_report_outcome(evidence_pack)
    assert owner_outcome.owner_receipt is not None
    reader = _CountingReader(
        owner_outcome.owner_receipt,
        expected_idempotency_key="postgres-report-finalize-failure-001",
    )
    command = ReconcileReportMaterializationCommand(
        support_reference=support_reference,
        actor_subject="operator-redacted",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        accepted_at_utc=RECORDED_AT + timedelta(minutes=6),
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        recovered = reconcile_report_materialization_receipt(
            command,
            repository=restarted,
            report_reader=reader,
        )
        persisted = restarted.downstream_submission_by_support_reference(support_reference)
        assert recovered.status is ReportMaterializationReconciliationStatus.ACCEPTED
        assert persisted is not None
        assert persisted.status.value == "accepted_by_downstream"
        assert persisted.owner_receipt == recovered.owner_receipt
        assert persisted.attempt_count == 1
        assert [entry.action.value for entry in persisted.audit_history] == [
            "claimed",
            "reconciled",
        ]

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted_again = PostgresIdeaRepository(cast(PostgresConnection, connection))
        replayed = reconcile_report_materialization_receipt(
            command,
            repository=restarted_again,
            report_reader=reader,
        )
        assert replayed.status is ReportMaterializationReconciliationStatus.REPLAYED
        assert replayed.owner_receipt == recovered.owner_receipt

    assert submit_client.call_count == 1
    assert reader.call_count == 2


def test_postgres_concurrent_report_owner_advancement_converges_without_duplicate_state(
    postgres_database_url: str,
) -> None:
    source_repository = repository_with_report_pack()
    evidence_pack = source_repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    owner_outcome = authoritative_report_outcome(evidence_pack)
    assert owner_outcome.owner_receipt is not None
    first_reader = _CountingReader(
        owner_outcome.owner_receipt,
        expected_idempotency_key="postgres-report-owner-advance-001",
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.replace_snapshot(source_repository.snapshot())
        submission = submit_report_evidence_pack_to_downstream(
            RealizeReportEvidencePackCommand(
                report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
                idempotency_key="postgres-report-owner-advance-001",
                actor_subject="advisor-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                submitted_at_utc=RECORDED_AT,
            ),
            repository=repository,
            report_client=_LostResponseClient(),
        )
        assert submission.support_reference is not None
        command = ReconcileReportMaterializationCommand(
            support_reference=submission.support_reference,
            actor_subject="operator-redacted",
            access_scope_filter=AUTHORIZED_SCOPE_FILTER,
            accepted_at_utc=RECORDED_AT + timedelta(seconds=1),
        )
        first = reconcile_report_materialization_receipt(
            command,
            repository=repository,
            report_reader=first_reader,
        )
        assert first.status is ReportMaterializationReconciliationStatus.ACCEPTED
        assert first.owner_receipt is not None
        assert first.owner_receipt.report_materialization is not None
        advanced_receipt = replace(
            owner_outcome.owner_receipt,
            source_event_version=2,
            report_materialization=replace(
                first.owner_receipt.report_materialization,
                status="collecting_data",
                materialization_status="collecting_data",
            ),
        )

    reader = _CountingReader(
        advanced_receipt,
        expected_idempotency_key="postgres-report-owner-advance-001",
    )

    def reconcile_from_new_runtime() -> ReportMaterializationReconciliationStatus:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
            result = reconcile_report_materialization_receipt(
                replace(command, accepted_at_utc=RECORDED_AT + timedelta(seconds=2)),
                repository=repository,
                report_reader=reader,
            )
            return result.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = tuple(executor.map(lambda _index: reconcile_from_new_runtime(), range(2)))

    assert sorted(statuses) == sorted(
        (
            ReportMaterializationReconciliationStatus.ACCEPTED,
            ReportMaterializationReconciliationStatus.REPLAYED,
        )
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        persisted = repository.downstream_submission_by_support_reference(command.support_reference)
        assert persisted is not None
        assert persisted.owner_receipt is not None
        assert persisted.owner_receipt.source_event_version == 2
        assert [entry.action.value for entry in persisted.audit_history].count("reconciled") == 2
    assert reader.call_count == 2
