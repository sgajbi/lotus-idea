from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier, Lock
from typing import Any, cast

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
    ReportMaterializationReconciliationResult,
    ReportMaterializationReconciliationStatus,
    reconcile_report_materialization_receipt,
)
from app.domain import (
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    SourceSystem,
)
from app.infrastructure.downstream_client import DownstreamServiceError
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    HttpReportEvidencePackMaterializationClient,
    ReportRealizationServiceContext,
)
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    ReportEvidencePackMaterializationReader,
)
from tests.integration.postgres_runtime_support import table_count
from tests.unit.test_downstream_realization_application import (
    AUTHORIZED_SCOPE_FILTER,
    repository_with_report_pack,
)


_ROOT = Path(__file__).resolve().parents[2]
_OWNER_DSN_ENV = "LOTUS_REPORT_POSTGRES_INTEGRATION_DSN"
_OWNER_ROOT_ENV = "LOTUS_REPORT_ROOT"
_OWNER_PYTHON_ENV = "LOTUS_REPORT_PYTHON"
_SUBMITTED_AT = datetime(2026, 9, 7, 7, 0, tzinfo=UTC)
_RECOVERED_AT = _SUBMITTED_AT + timedelta(minutes=6)


class _ReportPostgresProcessClient:
    def __init__(self, *, report_root: Path, report_python: str, report_dsn: str) -> None:
        self._report_root = report_root
        self._report_python = report_python
        self._env = _report_environment(report_root=report_root, report_dsn=report_dsn)
        self.post_calls = 0
        self.get_calls = 0
        self.get_payloads: list[dict[str, Any]] = []
        self.next_get_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
        self._process_lock = Lock()

    def post_json(
        self,
        path: str,
        *,
        json_payload: dict[str, Any],
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        self.post_calls += 1
        self._request(
            "POST",
            path,
            json_payload=json_payload,
            headers=_request_headers(
                additional_headers,
                correlation_id=correlation_id,
                trace_id=trace_id,
                idempotency_key=idempotency_key,
            ),
        )
        raise DownstreamServiceError(code="upstream_timeout", attempt_count=1)

    def get_json(
        self,
        path: str,
        *,
        query_params: Mapping[str, str] | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        self.get_calls += 1
        payload = self._request(
            "GET",
            path,
            query_params=dict(query_params or {}),
            headers=_request_headers(
                additional_headers,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ),
        )
        if self.next_get_transform is not None:
            transform = self.next_get_transform
            self.next_get_transform = None
            payload = transform(payload)
        self.get_payloads.append(payload)
        return payload

    def advance_to_collecting(self, job_id: str) -> None:
        self._request("ADVANCE_COLLECTING", "", job_id=job_id, headers={})

    def close(self) -> None:
        return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        query_params: dict[str, str] | None = None,
        job_id: str | None = None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        with self._process_lock:
            completed = subprocess.run(
                [
                    self._report_python,
                    str(_ROOT / "scripts/downstream_realization/report_postgres_owner_bridge.py"),
                ],
                cwd=self._report_root,
                env=self._env,
                input=json.dumps(
                    {
                        "method": method,
                        "path": path,
                        "json": json_payload,
                        "params": query_params,
                        "jobId": job_id,
                        "headers": headers,
                    }
                ),
                check=True,
                capture_output=True,
                text=True,
            )
        response = json.loads(completed.stdout)
        if not isinstance(response, dict) or not isinstance(response.get("body"), dict):
            raise AssertionError("Report owner process returned a malformed response")
        status_code = response.get("statusCode")
        if not isinstance(status_code, int):
            raise AssertionError("Report owner process omitted statusCode")
        if status_code >= 400:
            raise DownstreamServiceError(
                code="upstream_rejected_request" if status_code < 500 else "upstream_unavailable",
                status_code=status_code,
            )
        return cast(dict[str, Any], response["body"])


class _ConcurrentReader:
    def __init__(
        self,
        delegate: HttpReportEvidencePackMaterializationClient,
        barrier: Barrier,
    ) -> None:
        self._delegate = delegate
        self._barrier = barrier

    def recover_report_evidence_pack_receipt(
        self, *args: Any, **kwargs: Any
    ) -> DownstreamOwnerReceipt:
        receipt = self._delegate.recover_report_evidence_pack_receipt(*args, **kwargs)
        self._barrier.wait(timeout=15)
        return receipt


def test_report_retained_receipt_matrix_uses_real_postgres_state_without_duplicate_post(
    postgres_database_url: str,
) -> None:
    report_dsn, report_root, report_python = _owner_runtime()
    _prepare_report_database(report_dsn, report_root=report_root, report_python=report_python)
    source_repository = repository_with_report_pack()
    evidence_pack = source_repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    candidate_record = source_repository.candidate_record_for_report_evidence_pack(
        evidence_pack.report_evidence_pack_id
    )
    assert candidate_record is not None
    assert candidate_record.candidate.access_scope is not None
    access_scope = candidate_record.candidate.access_scope
    transport = _ReportPostgresProcessClient(
        report_root=report_root,
        report_python=report_python,
        report_dsn=report_dsn,
    )
    client = _report_client(transport)
    idempotency_key = "report-real-lost-response-once"

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.replace_snapshot(source_repository.snapshot())
        uncertain = submit_report_evidence_pack_to_downstream(
            RealizeReportEvidencePackCommand(
                report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
                idempotency_key=idempotency_key,
                actor_subject="advisor-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                submitted_at_utc=_SUBMITTED_AT,
            ),
            repository=repository,
            report_client=client,
        )
        assert uncertain.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
        assert uncertain.support_reference is not None
        support_reference = uncertain.support_reference

    assert transport.post_calls == 1
    assert _report_counts(report_dsn) == (1, 1, 1, 1)

    owner_receipt = client.recover_report_evidence_pack_receipt(
        evidence_pack,
        access_scope=access_scope,
        idempotency_key=idempotency_key,
    )
    legacy_receipt = _durable_receipt(owner_receipt, source_event_version=None)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        seeded = repository.reconcile_downstream_submission(
            support_reference=support_reference,
            resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
            actor_subject="legacy-migration",
            reason="retained_pre_version_report_receipt",
            change_reference="retained-report-receipt",
            reconciled_at_utc=_SUBMITTED_AT + timedelta(minutes=1),
            owner_receipt=legacy_receipt,
        )
        assert seeded.decision is DownstreamSubmissionMutationDecision.ACCEPTED
        assert seeded.record is not None
        legacy_audit_count = len(seeded.record.audit_history)

    command = ReconcileReportMaterializationCommand(
        support_reference=support_reference,
        actor_subject="platform-operator",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        accepted_at_utc=_RECOVERED_AT,
    )
    accepted = _reconcile_from_restart(postgres_database_url, command, client)
    after_legacy = _idea_submission(postgres_database_url, support_reference)
    replayed = _reconcile_from_restart(postgres_database_url, command, client)
    after_exact_replay = _idea_submission(postgres_database_url, support_reference)

    assert accepted.status is ReportMaterializationReconciliationStatus.ACCEPTED
    assert accepted.owner_receipt is not None
    assert accepted.owner_receipt.source_event_version == 1
    assert replayed.status is ReportMaterializationReconciliationStatus.REPLAYED
    assert after_exact_replay == after_legacy
    assert after_legacy.owner_receipt is not None
    assert len(after_legacy.audit_history) == legacy_audit_count + 1
    assert _report_counts(report_dsn) == (1, 1, 1, 1)

    report_job_id = accepted.owner_receipt.owner_realization_id
    transport.advance_to_collecting(report_job_id)
    assert _report_counts(report_dsn) == (1, 1, 1, 2)

    concurrent_command = replace(command, accepted_at_utc=_RECOVERED_AT + timedelta(seconds=1))
    concurrent_reader = _ConcurrentReader(client, Barrier(2))
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = tuple(
            executor.map(
                lambda _: (
                    _reconcile_from_restart(
                        postgres_database_url, concurrent_command, concurrent_reader
                    ).status
                ),
                range(2),
            )
        )
    assert sorted(statuses) == sorted(
        (
            ReportMaterializationReconciliationStatus.ACCEPTED,
            ReportMaterializationReconciliationStatus.REPLAYED,
        )
    )
    advanced = _idea_submission(postgres_database_url, support_reference)
    assert advanced.owner_receipt is not None
    assert advanced.owner_receipt.source_event_version == 2
    assert advanced.owner_receipt.owner_request_id == after_legacy.owner_receipt.owner_request_id
    assert advanced.owner_receipt.owner_realization_id == report_job_id
    assert len(advanced.audit_history) == len(after_legacy.audit_history) + 1

    def conflict(payload: dict[str, Any]) -> dict[str, Any]:
        return {**payload, "status": "data_ready", "materialization_status": "data_ready"}

    transport.next_get_transform = conflict
    before_conflict = _idea_submission(postgres_database_url, support_reference)
    refused = _reconcile_from_restart(
        postgres_database_url,
        replace(command, accepted_at_utc=_RECOVERED_AT + timedelta(seconds=2)),
        client,
    )
    assert refused.status is ReportMaterializationReconciliationStatus.CONFLICT
    assert refused.blocker == "report_materialization_owner_version_conflict"
    assert _idea_submission(postgres_database_url, support_reference) == before_conflict

    final_counts = _idea_counts(postgres_database_url)
    final_replay = _reconcile_from_restart(
        postgres_database_url,
        replace(command, accepted_at_utc=_RECOVERED_AT + timedelta(seconds=3)),
        client,
    )
    assert final_replay.status is ReportMaterializationReconciliationStatus.REPLAYED
    assert _idea_submission(postgres_database_url, support_reference) == advanced
    assert _idea_counts(postgres_database_url) == final_counts
    assert _report_counts(report_dsn) == (1, 1, 1, 2)
    assert transport.post_calls == 1
    assert transport.get_calls == 7


def _report_client(
    transport: _ReportPostgresProcessClient,
) -> HttpReportEvidencePackMaterializationClient:
    return HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="http://report-process.invalid",
            submit_path="/reports/idea-evidence-packs/materializations",
            report_recovery_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=ReportRealizationServiceContext(
                actor_id="svc-lotus-idea",
                caller_application="lotus-idea",
                tenant_id="tenant-sg",
                region="APAC",
                requested_output_formats=("json",),
            ),
        ),
        client=cast(Any, transport),
    )


def _reconcile_from_restart(
    dsn: str,
    command: ReconcileReportMaterializationCommand,
    client: ReportEvidencePackMaterializationReader,
) -> ReportMaterializationReconciliationResult:
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        return reconcile_report_materialization_receipt(
            command,
            repository=repository,
            report_reader=client,
        )


def _durable_receipt(
    receipt: DownstreamOwnerReceipt,
    *,
    source_event_version: int | None,
) -> DownstreamSubmissionOwnerReceipt:
    assert receipt.report_materialization is not None
    return DownstreamSubmissionOwnerReceipt(
        owner_authority=receipt.owner_authority,
        owner_request_id=receipt.owner_request_id,
        owner_realization_id=receipt.owner_realization_id,
        owner_work_id=receipt.owner_work_id,
        source_event_version=source_event_version,
        source_evidence_fingerprint=receipt.source_evidence_fingerprint,
        report_materialization=receipt.report_materialization,
    )


def _idea_submission(dsn: str, support_reference: str) -> DownstreamSubmissionRecord:
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        submission = PostgresIdeaRepository(
            cast(PostgresConnection, connection)
        ).downstream_submission_by_support_reference(support_reference)
    assert submission is not None
    return submission


def _owner_runtime() -> tuple[str, Path, str]:
    dsn = os.getenv(_OWNER_DSN_ENV, "").strip()
    root = Path(os.getenv(_OWNER_ROOT_ENV, str(_ROOT.parent / "lotus-report"))).resolve()
    python = os.getenv(_OWNER_PYTHON_ENV, "").strip() or sys.executable
    if not dsn:
        pytest.skip(f"{_OWNER_DSN_ENV} is required for cross-service PostgreSQL proof")
    if not root.joinpath("src/app/main.py").is_file():
        pytest.fail(f"{_OWNER_ROOT_ENV} does not identify a lotus-report checkout")
    return dsn, root, python


def _prepare_report_database(dsn: str, *, report_root: Path, report_python: str) -> None:
    subprocess.run(
        [
            report_python,
            "-c",
            (
                "import os; "
                "from app.reporting_jobs.postgres_ledger import PostgresReportJobLedger; "
                "ledger=PostgresReportJobLedger("
                "database_url=os.environ['REPORT_JOB_LEDGER_DATABASE_URL']); ledger.close()"
            ),
        ],
        cwd=report_root,
        env=_report_environment(report_root=report_root, report_dsn=dsn),
        check=True,
        capture_output=True,
        text=True,
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE TABLE idea_evidence_intake, report_status_event, report_job, "
            "report_request CASCADE"
        )


def _report_environment(*, report_root: Path, report_dsn: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(report_root / "src"),
            "LOTUS_REPORT_ROOT": str(report_root),
            "ENVIRONMENT": "test",
            "REPORT_JOB_LEDGER_DATABASE_URL": report_dsn,
            "REPORT_IDEA_EVIDENCE_INTAKE_LEDGER_BACKEND": "postgresql",
            "REPORT_POSTGRES_POOL_MIN_SIZE": "0",
        }
    )
    return env


def _request_headers(
    additional_headers: Mapping[str, str] | None,
    *,
    correlation_id: str | None,
    trace_id: str | None,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    headers = dict(additional_headers or {})
    if correlation_id:
        headers["X-Correlation-Id"] = correlation_id
    if trace_id:
        headers["X-Trace-Id"] = trace_id
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _report_counts(dsn: str) -> tuple[int, int, int, int]:
    tables = ("idea_evidence_intake", "report_request", "report_job", "report_status_event")
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        counts: list[int] = []
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = cursor.fetchone()
            counts.append(int(row[0]) if row else -1)
    return cast(tuple[int, int, int, int], tuple(counts))


def _idea_counts(dsn: str) -> tuple[int, int, int]:
    tables = ("idea_downstream_submission", "idea_audit_event", "idea_outbox_event")
    return cast(
        tuple[int, int, int],
        tuple(table_count(dsn, table, allowed_tables=tables) for table in tables),
    )
