from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.application.advise_realization_reconciliation import (
    AdviseRealizationAccessScopeDenied,
    AdviseRealizationReconciliationStatus,
    ReconcileAdviseRealizationCommand,
    reconcile_advise_realization_history,
)
from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeConversionIntentCommand,
    submit_conversion_intent_to_downstream,
)
from app.domain.advise_evidence_identity import (
    advise_source_evidence_fingerprint,
)
from app.domain import QueueAccessScopeFilter, SourceSystem
from app.infrastructure.downstream_client import DownstreamServiceError
from app.infrastructure.downstream_realization import (
    AdviseRealizationServiceContext,
    DownstreamRealizationAdapterConfig,
    HttpAdviseProposalRealizationClient,
)
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from tests.integration.postgres_runtime_support import (
    seed_governed_advise_conversion_resource,
    table_count,
)


_ROOT = Path(__file__).resolve().parents[2]
_OWNER_DSN_ENV = "LOTUS_ADVISE_POSTGRES_INTEGRATION_DSN"
_OWNER_ROOT_ENV = "LOTUS_ADVISE_ROOT"
_OWNER_PYTHON_ENV = "LOTUS_ADVISE_PYTHON"
_SUBMITTED_AT = datetime(2026, 9, 6, 8, 0, tzinfo=UTC)
_ACCEPTED_AT = datetime(2026, 9, 6, 8, 6, tzinfo=UTC)
_SCOPE = QueueAccessScopeFilter(
    tenant_id="tenant-sg",
    book_id="book-private-bank-sg",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-redacted",
)


class _AdvisePostgresProcessClient:
    def __init__(self, *, advise_root: Path, advise_python: str, advise_dsn: str) -> None:
        self._advise_root = advise_root
        self._advise_python = advise_python
        self._env = _advise_environment(advise_root=advise_root, advise_dsn=advise_dsn)
        self.post_calls = 0
        self.get_calls = 0
        self.get_payloads: list[dict[str, Any]] = []
        self.last_get_payload: dict[str, Any] | None = None

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
        headers = _request_headers(
            additional_headers,
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        _ = self._request("POST", path, json_payload=json_payload, headers=headers)
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
        headers = _request_headers(
            additional_headers,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        payload = self._request(
            "GET",
            path,
            query_params=dict(query_params or {}),
            headers=headers,
        )
        self.get_payloads.append(payload)
        self.last_get_payload = payload
        return payload

    def close(self) -> None:
        return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        completed = subprocess.run(
            [
                self._advise_python,
                str(_ROOT / "scripts/downstream_realization/advise_postgres_owner_bridge.py"),
            ],
            cwd=self._advise_root,
            env=self._env,
            input=json.dumps(
                {
                    "method": method,
                    "path": path,
                    "json": json_payload,
                    "params": query_params,
                    "headers": headers,
                }
            ),
            check=True,
            capture_output=True,
            text=True,
        )
        response = json.loads(completed.stdout)
        if not isinstance(response, dict) or not isinstance(response.get("body"), dict):
            raise AssertionError("Advise owner process returned a malformed response")
        status_code = response.get("statusCode")
        if not isinstance(status_code, int):
            raise AssertionError("Advise owner process omitted statusCode")
        if status_code >= 400:
            raise DownstreamServiceError(
                code="upstream_rejected_request" if status_code < 500 else "upstream_unavailable",
                status_code=status_code,
            )
        return cast(dict[str, Any], response["body"])


def test_postgres_lost_response_reconciles_one_real_advise_intake_after_restart(
    postgres_database_url: str,
) -> None:
    advise_dsn, advise_root, advise_python = _owner_runtime()
    _prepare_advise_database(advise_dsn, advise_root=advise_root, advise_python=advise_python)
    conversion_intent_id = "conversion-advise-real-lost-response"
    candidate_id, evidence_fingerprint = seed_governed_advise_conversion_resource(
        postgres_database_url,
        conversion_intent_id,
    )
    transport = _AdvisePostgresProcessClient(
        advise_root=advise_root,
        advise_python=advise_python,
        advise_dsn=advise_dsn,
    )
    client = _advise_client(transport)
    command = RealizeConversionIntentCommand(
        conversion_intent_id=conversion_intent_id,
        idempotency_key="advise-real-lost-response-once",
        actor_subject="advisor-redacted",
        access_scope_filter=_SCOPE,
        correlation_id="corr-advise-real-lost-response",
        trace_id="trace-advise-real-lost-response",
        submitted_at_utc=_SUBMITTED_AT,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as first_connection:
        first_repository = PostgresIdeaRepository(cast(PostgresConnection, first_connection))
        uncertain = submit_conversion_intent_to_downstream(
            command,
            repository=first_repository,
            advise_client=client,
            manage_client=None,
        )
        uncertain_record = first_repository.downstream_submission_by_support_reference(
            uncertain.support_reference or ""
        )

    assert uncertain.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert uncertain_record is not None
    assert uncertain_record.status.value == "reconciliation_required"
    assert uncertain_record.attempt_count == 1
    assert uncertain_record.owner_receipt is None
    assert transport.post_calls == 1
    assert _advise_counts(advise_dsn) == (1, 1, 1)

    reconcile_command = ReconcileAdviseRealizationCommand(
        support_reference=uncertain.support_reference or "",
        actor_subject="platform-operator",
        access_scope_filter=_SCOPE,
        accepted_at_utc=_ACCEPTED_AT,
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as restart_connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, restart_connection))
        before_denial = _idea_counts(postgres_database_url)
        with pytest.raises(AdviseRealizationAccessScopeDenied):
            reconcile_advise_realization_history(
                ReconcileAdviseRealizationCommand(
                    support_reference=reconcile_command.support_reference,
                    actor_subject=reconcile_command.actor_subject,
                    access_scope_filter=QueueAccessScopeFilter(tenant_id="tenant-hk"),
                    accepted_at_utc=_ACCEPTED_AT,
                ),
                repository=restarted,
                advise_reader=client,
            )
        assert transport.get_calls == 0
        assert _idea_counts(postgres_database_url) == before_denial

        accepted = reconcile_advise_realization_history(
            reconcile_command,
            repository=restarted,
            advise_reader=client,
        )
        after_acceptance = _idea_counts(postgres_database_url)
        accepted_record = restarted.downstream_submission_by_support_reference(
            reconcile_command.support_reference
        )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as replay_connection:
        replay_runtime = PostgresIdeaRepository(cast(PostgresConnection, replay_connection))
        replayed = reconcile_advise_realization_history(
            reconcile_command,
            repository=replay_runtime,
            advise_reader=client,
        )
        replay_record = replay_runtime.downstream_submission_by_support_reference(
            reconcile_command.support_reference
        )

    assert accepted.status is AdviseRealizationReconciliationStatus.ACCEPTED, accepted.blocker
    assert accepted.appended_outcome_count == 1
    assert replayed.status is AdviseRealizationReconciliationStatus.REPLAYED
    assert replayed.appended_outcome_count == 0
    assert transport.post_calls == 1
    assert transport.get_calls == 2
    assert transport.get_payloads[0] == transport.get_payloads[1]
    assert _advise_counts(advise_dsn) == (1, 1, 1)
    assert _idea_counts(postgres_database_url) == after_acceptance
    assert accepted_record == replay_record
    assert replay_record is not None
    assert replay_record.attempt_count == 1
    assert replay_record.owner_receipt is not None
    assert replay_record.owner_receipt.source_evidence_fingerprint == (
        advise_source_evidence_fingerprint(
            candidate_id=candidate_id,
            evidence_content_hash=evidence_fingerprint,
        )
    )
    assert transport.last_get_payload is not None
    assert transport.last_get_payload["idea_candidate_id"] == candidate_id
    assert transport.last_get_payload["conversion_intent_id"] == conversion_intent_id
    assert transport.last_get_payload["intake_id"] == replay_record.owner_receipt.owner_request_id
    assert (
        transport.last_get_payload["realization_id"]
        == replay_record.owner_receipt.owner_realization_id
    )
    assert transport.last_get_payload["review_work_id"] == replay_record.owner_receipt.owner_work_id
    assert replay_record.audit_history[-1].occurred_at_utc == _ACCEPTED_AT
    assert transport.last_get_payload["outcomes"][0]["occurred_at"] != _ACCEPTED_AT.isoformat()


def _advise_client(transport: _AdvisePostgresProcessClient) -> HttpAdviseProposalRealizationClient:
    return HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="http://advise-process.invalid",
            submit_path="/advisory/proposals/idea-intake",
            history_path_template="/advisory/proposals/idea-intake/{intake_id}/realization",
            recovery_history_path="/advisory/proposals/idea-intake/realization",
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=AdviseRealizationServiceContext(
                actor_id="svc-lotus-idea",
                role="SERVICE",
                tenant_id="tenant-sg",
                legal_entity_code="SGPB",
                service_identity="lotus-idea",
                capabilities=(
                    "advisory.idea_proposal_intake.accept,advisory.idea_proposal_realization.read"
                ),
            ),
        ),
        client=cast(Any, transport),
    )


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


def _owner_runtime() -> tuple[str, Path, str]:
    dsn = os.getenv(_OWNER_DSN_ENV, "").strip()
    root = Path(os.getenv(_OWNER_ROOT_ENV, str(_ROOT.parent / "lotus-advise"))).resolve()
    python = os.getenv(_OWNER_PYTHON_ENV, "").strip() or sys.executable
    if not dsn:
        pytest.skip(f"{_OWNER_DSN_ENV} is required for cross-service PostgreSQL proof")
    if not root.joinpath("src/api/main.py").is_file():
        pytest.fail(f"{_OWNER_ROOT_ENV} does not identify a lotus-advise checkout")
    return dsn, root, python


def _prepare_advise_database(dsn: str, *, advise_root: Path, advise_python: str) -> None:
    env = _advise_environment(advise_root=advise_root, advise_dsn=dsn)
    subprocess.run(
        [
            advise_python,
            "scripts/postgres_migrate.py",
            "--target",
            "all",
            "--proposals-dsn",
            dsn,
        ],
        cwd=advise_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE TABLE proposal_memo_events, proposal_memo_idempotency, proposal_memos, "
            "proposal_approvals, proposal_workflow_events, proposal_versions, proposal_records, "
            "proposal_async_operations, proposal_idempotency, proposal_idea_intake_purge_events, "
            "proposal_idea_realization_outcomes, proposal_idea_review_realizations, "
            "proposal_idea_intakes CASCADE"
        )


def _advise_environment(*, advise_root: Path, advise_dsn: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(advise_root),
            "LOTUS_ADVISE_ROOT": str(advise_root),
            "ENVIRONMENT": "test",
            "IDEA_PROPOSAL_RECONCILIATION_ENABLED": "true",
            "PROPOSAL_STORE_BACKEND": "POSTGRES",
            "PROPOSAL_POSTGRES_DSN": advise_dsn,
            "POLICY_STORE_BACKEND": "POSTGRES",
            "POLICY_POSTGRES_DSN": advise_dsn,
            "WORKSPACE_STORE_BACKEND": "POSTGRES",
            "WORKSPACE_POSTGRES_DSN": advise_dsn,
            "ADVISORY_COPILOT_POSTGRES_DSN": advise_dsn,
        }
    )
    return env


def _advise_counts(dsn: str) -> tuple[int, int, int]:
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        counts = []
        for table in (
            "proposal_idea_intakes",
            "proposal_idea_review_realizations",
            "proposal_idea_realization_outcomes",
        ):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = cursor.fetchone()
            counts.append(int(row[0]) if row else -1)
    return cast(tuple[int, int, int], tuple(counts))


def _idea_counts(dsn: str) -> tuple[int, int, int, int]:
    tables = (
        "idea_downstream_submission",
        "idea_advise_realization_history",
        "idea_audit_event",
        "idea_outbox_event",
    )
    return cast(
        tuple[int, int, int, int],
        tuple(table_count(dsn, table, allowed_tables=tables) for table in tables),
    )
