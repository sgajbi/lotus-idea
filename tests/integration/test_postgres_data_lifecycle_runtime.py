from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import Any, cast

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.application.data_lifecycle import ExecuteDataLifecycle, ReviewScheduledDataLifecycle
from app.domain import DownstreamSubmissionClaimDecision
from app.domain.data_lifecycle import (
    DataLifecycleBlocker,
    DataLifecycleAction,
    DataLifecycleCommand,
    DataLifecycleDecision,
)
from app.domain.data_lifecycle.authority import (
    LifecycleAuthorityDomain,
    VerifiedLifecycleAuthorityReceipt,
)
from app.infrastructure.postgres_data_lifecycle import DataLifecycleWriteBlockedError
from app.infrastructure.postgres_data_lifecycle_schedule import (
    PostgresScheduledDataLifecycleRepository,
)
from app.infrastructure.postgres_disaster_recovery import REFERENTIAL_CHECKS
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    seed_active_conversion_resource,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim


TENANT_ID = "tenant-private-bank-sg"


def test_postgres_data_lifecycle_survives_restart_and_redacts_atomically(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("lifecycle-runtime-candidate-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    _complete_outbox_delivery(postgres_database_url, candidate_id)
    requested_at = datetime.now(UTC) - timedelta(seconds=1)

    preview_payload = _action_payload("erase", requested_at=requested_at, dry_run=True)
    preview = _action(client, candidate_id, "lifecycle-preview-001", preview_payload)
    assert preview.status_code == 200
    assert preview.json()["decision"] == "preview"

    reset_idea_repository_for_tests(reload_from_environment=True)
    replay = _action(client, candidate_id, "lifecycle-preview-001", preview_payload)
    conflict = _action(
        client,
        candidate_id,
        "lifecycle-preview-001",
        {**preview_payload, "reason": "changed_approved_request"},
    )
    assert replay.status_code == 200
    assert replay.json()["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "data_lifecycle_idempotency_conflict"

    hold = _action(
        client,
        candidate_id,
        "lifecycle-hold-001",
        _action_payload(
            "apply_hold",
            requested_at=requested_at,
            authority_ref="bank-legal-and-records-governance:hold-001",
        ),
    )
    blocked = _action(
        client,
        candidate_id,
        "lifecycle-erase-held-001",
        _action_payload("erase", requested_at=requested_at, approver=True),
    )
    assert hold.status_code == 200
    assert hold.json()["state"] == "held"
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "data_lifecycle_action_blocked"

    release = _action(
        client,
        candidate_id,
        "lifecycle-release-001",
        _action_payload(
            "release_hold",
            requested_at=requested_at,
            authority_ref="bank-legal-and-records-governance:hold-001",
            approver=True,
        ),
    )
    erased = _action(
        client,
        candidate_id,
        "lifecycle-erase-001",
        _action_payload("erase", requested_at=requested_at, approver=True),
    )
    assert release.status_code == 200
    assert release.json()["state"] == "active"
    assert erased.status_code == 200
    assert erased.json()["state"] == "erased"

    _assert_erased_graph(postgres_database_url, candidate_id)
    reset_idea_repository_for_tests(reload_from_environment=True)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        assert repository.candidate_record_by_id(candidate_id) is None
        erased_telemetry = repository.runtime_trust_telemetry_summary()
        assert erased_telemetry.candidate_snapshot_count == 0
        assert erased_telemetry.data_lifecycle_state_counts == {"erased": 1}
        assert erased_telemetry.lifecycle_control_missing_count == 0

    _expire_retention(postgres_database_url, candidate_id)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        scheduled_review = ReviewScheduledDataLifecycle(
            PostgresScheduledDataLifecycleRepository(connection),
            now=lambda: datetime.now(UTC),
        ).execute(limit=10)
    assert scheduled_review.truncated is False
    assert scheduled_review.ready_count == 1
    assert [item.snapshot.candidate_id for item in scheduled_review.items] == [candidate_id]

    purged = _action(
        client,
        candidate_id,
        "lifecycle-purge-001",
        _action_payload("purge", requested_at=requested_at, approver=True),
    )
    assert purged.status_code == 200, _operation_blockers(
        postgres_database_url, "lifecycle-purge-001"
    )
    assert purged.json()["state"] == "purged"
    _assert_purged_graph(postgres_database_url, candidate_id)
    _assert_no_orphaned_references(postgres_database_url)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        purged_telemetry = repository.runtime_trust_telemetry_summary()
        assert purged_telemetry.candidate_snapshot_count == 0
        assert purged_telemetry.data_lifecycle_state_counts == {"purged": 1}


def test_postgres_erasure_and_delivery_claim_are_serialized(
    postgres_database_url: str,
) -> None:
    conversion_id = "conversion-lifecycle-race"
    candidate_id = seed_active_conversion_resource(postgres_database_url, conversion_id)
    barrier = Barrier(2)
    evaluated_at = datetime.now(UTC)

    def erase() -> DataLifecycleDecision:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
            command = DataLifecycleCommand(
                candidate_id=candidate_id,
                tenant_id=TENANT_ID,
                action=DataLifecycleAction.ERASE,
                actor_subject="privacy-operator-race",
                approver_subject="privacy-approver-race",
                authority_ref="bank-privacy-governance:race-001",
                reason="approved_lifecycle_request",
                change_reference="privacy-case-race-001",
                idempotency_key="lifecycle-race-erase-001",
                request_fingerprint="a" * 64,
                correlation_id="corr-lifecycle-race-001",
                trace_id="trace-lifecycle-race-001",
                requested_at_utc=evaluated_at - timedelta(seconds=1),
                dry_run=False,
            )
            barrier.wait(timeout=5)
            return (
                ExecuteDataLifecycle(repository, now=lambda: evaluated_at).execute(command).decision
            )

    def claim() -> str:
        with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
            repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
            record = build_downstream_submission_claim(
                idempotency_key="lifecycle-race-claim-001",
                request_fingerprint="sha256:lifecycle-race-claim",
                resource_id=conversion_id,
                submitted_at_utc=evaluated_at,
            )
            barrier.wait(timeout=5)
            try:
                return repository.claim_downstream_submission(record).decision.value
            except DataLifecycleWriteBlockedError as error:
                return error.blocker

    with ThreadPoolExecutor(max_workers=2) as executor:
        erase_future = executor.submit(erase)
        claim_future = executor.submit(claim)
        erase_decision = erase_future.result(timeout=10)
        claim_decision = claim_future.result(timeout=10)

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM idea_data_lifecycle_control WHERE candidate_id = %s",
                (candidate_id,),
            )
            control = cursor.fetchone()
            cursor.execute(
                """SELECT COUNT(*) AS submission_count FROM idea_downstream_submission
                   WHERE resource_id = %s""",
                (conversion_id,),
            )
            submission_count = cursor.fetchone()
    assert control is not None
    assert submission_count is not None
    observed = (erase_decision.value, claim_decision)
    assert observed in {
        (DataLifecycleDecision.APPLIED.value, "candidate_erased"),
        (
            DataLifecycleDecision.BLOCKED.value,
            DownstreamSubmissionClaimDecision.ACCEPTED.value,
        ),
    }
    assert not (control["state"] == "erased" and submission_count["submission_count"] != 0)


def test_postgres_lifecycle_authority_receipt_is_restart_safe_and_single_use(
    postgres_database_url: str,
) -> None:
    persisted = TestClient(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("lifecycle-authority-runtime-candidate-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    _complete_outbox_delivery(postgres_database_url, candidate_id)
    evaluated_at = datetime.now(UTC)
    receipt = VerifiedLifecycleAuthorityReceipt(
        decision_id="privacy-decision-runtime-001",
        replay_nonce="f" * 64,
        tenant_id=TENANT_ID,
        candidate_id=candidate_id,
        action=DataLifecycleAction.ERASE,
        authority_domain=LifecycleAuthorityDomain.PRIVACY,
        authority_ref="bank-privacy-governance:decision-runtime-001",
        change_reference="privacy-case-runtime-authority-001",
        key_id="lifecycle-key-runtime-001",
        rotation_epoch=4,
        issued_at_utc=evaluated_at - timedelta(minutes=3),
        effective_at_utc=evaluated_at - timedelta(minutes=2),
        expires_at_utc=evaluated_at + timedelta(minutes=5),
        verified_at_utc=evaluated_at,
    )
    command = DataLifecycleCommand(
        candidate_id=candidate_id,
        tenant_id=TENANT_ID,
        action=DataLifecycleAction.ERASE,
        actor_subject="privacy-operator-authority-runtime",
        approver_subject="privacy-approver-authority-runtime",
        authority_ref=receipt.authority_ref,
        reason="approved_lifecycle_request",
        change_reference=receipt.change_reference,
        idempotency_key="lifecycle-authority-runtime-apply-001",
        request_fingerprint="f" * 64,
        correlation_id="corr-lifecycle-authority-runtime-001",
        trace_id="trace-lifecycle-authority-runtime-001",
        requested_at_utc=evaluated_at - timedelta(seconds=1),
        dry_run=False,
        authority_verification_required=True,
        authority_receipt=receipt,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        first = ExecuteDataLifecycle(
            PostgresIdeaRepository(cast(PostgresConnection, connection)),
            now=lambda: evaluated_at,
        ).execute(command)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        replay = ExecuteDataLifecycle(repository, now=lambda: evaluated_at).execute(command)
        reused = ExecuteDataLifecycle(repository, now=lambda: evaluated_at).execute(
            replace(command, idempotency_key="lifecycle-authority-runtime-reuse-001")
        )

    assert first.decision is DataLifecycleDecision.APPLIED
    assert replay.decision is DataLifecycleDecision.REPLAYED
    assert reused.decision is DataLifecycleDecision.CONFLICT
    assert reused.blockers == (DataLifecycleBlocker.AUTHORITY_ATTESTATION_REPLAY,)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT authority_decision_id, authority_replay_nonce,
                          authority_key_id, authority_rotation_epoch,
                          authority_verified_at_utc
                   FROM idea_data_lifecycle_operation
                   WHERE candidate_id = %s AND authority_decision_id IS NOT NULL""",
                (candidate_id,),
            )
            rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["authority_decision_id"] == receipt.decision_id
    assert rows[0]["authority_replay_nonce"] == receipt.replay_nonce
    assert rows[0]["authority_key_id"] == receipt.key_id
    assert rows[0]["authority_rotation_epoch"] == receipt.rotation_epoch
    assert rows[0]["authority_verified_at_utc"] == receipt.verified_at_utc


def _action(
    client: TestClient,
    candidate_id: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> Any:
    return client.post(
        f"/api/v1/data-lifecycle/candidates/{candidate_id}/actions",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
            "X-Caller-Subject": "privacy-operator-001",
            "X-Caller-Roles": "privacy_officer",
            "X-Caller-Capabilities": "idea.data-lifecycle.manage",
            "X-Caller-Tenant-Ids": TENANT_ID,
            "X-Correlation-Id": "corr-lifecycle-runtime-001",
            "X-Trace-Id": "trace-lifecycle-runtime-001",
        },
    )


def _action_payload(
    action: str,
    *,
    requested_at: datetime,
    dry_run: bool = False,
    authority_ref: str = "bank-privacy-governance:decision-001",
    approver: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tenantId": TENANT_ID,
        "action": action,
        "authorityRef": authority_ref,
        "reason": "approved_lifecycle_request",
        "changeReference": "privacy-case-runtime-001",
        "requestedAtUtc": requested_at.isoformat(),
        "dryRun": dry_run,
    }
    if approver:
        payload["approverSubject"] = "privacy-approver-001"
    return payload


def _complete_outbox_delivery(database_url: str, candidate_id: str) -> None:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """UPDATE idea_outbox_event
               SET status = 'published', published_at_utc = CURRENT_TIMESTAMP,
                   failure_reason = NULL, lease_owner = NULL,
                   lease_attempt_id = NULL, lease_expires_at_utc = NULL
               WHERE aggregate_type = 'idea_candidate' AND aggregate_id = %s""",
            (candidate_id,),
        )


def _assert_erased_graph(database_url: str, candidate_id: str) -> None:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT candidate_json FROM idea_candidate_record WHERE candidate_id = %s",
                (candidate_id,),
            )
            candidate = cursor.fetchone()
            assert candidate is not None
            assert candidate["candidate_json"]["data_lifecycle_state"] == "erased"
            assert "access_scope" not in candidate["candidate_json"]
            cursor.execute(
                """SELECT state, actor_subject, approver_subject,
                          correlation_id, trace_id
                   FROM idea_data_lifecycle_control control
                   JOIN idea_data_lifecycle_operation operation USING (candidate_id)
                   WHERE candidate_id = %s""",
                (candidate_id,),
            )
            operations = cursor.fetchall()
    assert operations
    assert {row["state"] for row in operations} == {"erased"}
    assert all(str(row["actor_subject"]).startswith("redacted-") for row in operations)
    assert all(
        row["approver_subject"] is None or str(row["approver_subject"]).startswith("redacted-")
        for row in operations
    )
    assert {row["correlation_id"] for row in operations} == {"corr-lifecycle-runtime-001"}
    assert {row["trace_id"] for row in operations} == {"trace-lifecycle-runtime-001"}


def _expire_retention(database_url: str, candidate_id: str) -> None:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """UPDATE idea_data_lifecycle_control
               SET retention_expires_at_utc = CURRENT_TIMESTAMP - INTERVAL '1 day'
               WHERE candidate_id = %s AND state = 'erased'""",
            (candidate_id,),
        )
        assert cursor.rowcount == 1


def _assert_purged_graph(database_url: str, candidate_id: str) -> None:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT state, purged_at_utc
                   FROM idea_data_lifecycle_control WHERE candidate_id = %s""",
                (candidate_id,),
            )
            control = cursor.fetchone()
            assert control is not None
            assert control["state"] == "purged"
            assert control["purged_at_utc"] is not None
            cursor.execute(
                """SELECT COUNT(*) AS payload_count FROM idea_outbox_event
                   WHERE aggregate_type = 'idea_candidate' AND aggregate_id = %s""",
                (candidate_id,),
            )
            payload_count = cursor.fetchone()
            assert payload_count is not None
            assert payload_count["payload_count"] == 0
            cursor.execute(
                """SELECT COUNT(*) AS operation_count
                   FROM idea_data_lifecycle_operation WHERE candidate_id = %s""",
                (candidate_id,),
            )
            operation_count = cursor.fetchone()
            assert operation_count is not None
            assert operation_count["operation_count"] >= 6


def _operation_blockers(database_url: str, idempotency_key: str) -> object:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT blockers_json FROM idea_data_lifecycle_operation
                   WHERE idempotency_key = %s""",
                (idempotency_key,),
            )
            row = cursor.fetchone()
    return row["blockers_json"] if row is not None else "operation_not_persisted"


def _assert_no_orphaned_references(database_url: str) -> None:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            for relationship, (_, query) in REFERENTIAL_CHECKS.items():
                cursor.execute(query)
                row = cursor.fetchone()
                assert row is not None
                assert next(iter(row.values())) == 0, relationship
