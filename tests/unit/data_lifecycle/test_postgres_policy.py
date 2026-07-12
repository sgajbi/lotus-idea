from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Sequence

import pytest

from app.domain.data_lifecycle import (
    REGULATED_ADVISORY_POLICY_REF,
    DataLifecycleAction,
    DataLifecycleBlocker,
    DataLifecycleCommand,
    DataLifecycleDecision,
    DataLifecycleOperationResult,
    DataLifecycleState,
    evaluate_data_lifecycle,
)
from app.domain.data_lifecycle.authority import (
    LifecycleAuthorityDomain,
    VerifiedLifecycleAuthorityReceipt,
)
from app.domain.data_lifecycle.archive_posture import (
    ArchiveLegalHoldStatus,
    ArchiveLifecycleAction,
    ArchivePurgeStatus,
    VerifiedArchiveLifecycleReceipt,
)
from app.infrastructure.data_lifecycle import postgres_policy as module
from app.infrastructure.data_lifecycle.postgres_policy import (
    DataLifecycleWriteBlockedError,
    PostgresDataLifecycleRepository,
    assert_data_lifecycle_allows_candidate_writes,
)
from app.infrastructure.data_lifecycle.postgres_redaction import (
    purge_expired_candidate_payloads,
    redact_candidate_graph,
)
from tests.unit.postgres_repository_fake import FakePostgresConnection

NOW = datetime(2026, 7, 11, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("control", "expected_blocker"),
    [
        (None, "lifecycle_control_missing"),
        ({"state": "erased", "held_from_state": None}, "candidate_erased"),
        ({"state": "held", "held_from_state": "purged"}, "candidate_erased"),
    ],
)
def test_postgres_write_fence_rejects_missing_or_terminal_lifecycle_control(
    control: dict[str, object] | None,
    expected_blocker: str,
) -> None:
    connection = FakePostgresConnection()
    connection.rows["idea_candidate_record"].append({"candidate_id": "candidate-fenced"})
    if control is not None:
        connection.rows["idea_data_lifecycle_control"].append(
            {"candidate_id": "candidate-fenced", **control}
        )

    with connection.cursor() as cursor, pytest.raises(DataLifecycleWriteBlockedError) as error:
        assert_data_lifecycle_allows_candidate_writes(cursor, {"candidate-fenced"})

    assert error.value.blocker == expected_blocker


class LifecycleCursor:
    def __init__(self, connection: LifecycleConnection) -> None:
        self.connection = connection
        self.rows: list[dict[str, Any]] = []
        self.rowcount = 0
        self.executed: list[str] = []

    def __enter__(self) -> LifecycleCursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        normalized = " ".join(query.lower().split())
        self.executed.append(normalized)
        self.rows = []
        self.rowcount = 0
        if "pg_advisory_xact_lock" in normalized:
            return
        if "from idea_data_lifecycle_operation" in normalized:
            assert params is not None
            if "archive_decision_id" in normalized:
                operation = next(
                    (
                        row
                        for row in self.connection.operations.values()
                        if row.get("decision") == "applied"
                        and (
                            row.get("archive_decision_id") == params[0]
                            or row.get("archive_payload_digest") == params[1]
                        )
                    ),
                    None,
                )
            elif "where authority_decision_id" in normalized:
                operation = next(
                    (
                        row
                        for row in self.connection.operations.values()
                        if row.get("authority_decision_id") == params[0]
                        or row.get("authority_replay_nonce") == params[1]
                    ),
                    None,
                )
            else:
                operation = self.connection.operations.get(str(params[0]))
            self.rows = [operation] if operation is not None else []
            return
        if "select candidate_json" in normalized:
            assert params is not None
            if self.connection.candidate_exists:
                self.rows = [
                    {
                        "candidate_json": {
                            "access_scope": {"tenant_id": self.connection.candidate_tenant_id}
                        }
                    }
                ]
            return
        if "from idea_data_lifecycle_control" in normalized:
            self.rows = [dict(self.connection.control)] if self.connection.control else []
            return
        if "from idea_outbox_event" in normalized:
            self.rows = [{"active_count": self.connection.active_outbox_count}]
            return
        if "from idea_downstream_submission" in normalized:
            self.rows = [{"active_count": self.connection.active_downstream_count}]
            return
        if "from idea_report_evidence_pack_request" in normalized:
            self.rows = [
                {"report_evidence_pack_id": evidence_pack_id}
                for evidence_pack_id in sorted(self.connection.linked_report_evidence_pack_ids)
            ]
            return
        if normalized.startswith("update idea_data_lifecycle_control"):
            assert params is not None
            self.rowcount = self.connection.control_update_rowcount
            if self.rowcount == 1:
                keys = (
                    "state",
                    "version",
                    "updated_at_utc",
                    "held_from_state",
                    "hold_authority_ref",
                    "hold_change_reference",
                    "held_at_utc",
                    "erased_at_utc",
                    "purged_at_utc",
                    "tombstone_sha256",
                )
                self.connection.control.update(dict(zip(keys, params[:10], strict=True)))
            return
        if normalized.startswith("insert into idea_data_lifecycle_operation"):
            assert params is not None
            values = [_unwrap(value) for value in params]
            row = dict(
                zip(
                    (
                        "operation_id",
                        "idempotency_key",
                        "request_fingerprint",
                        "candidate_id",
                        "correlation_id",
                        "trace_id",
                        "tenant_id",
                        "action",
                        "decision",
                        "dry_run",
                        "actor_subject",
                        "approver_subject",
                        "authority_ref",
                        "reason",
                        "change_reference",
                        "blockers_json",
                        "affected_row_counts_json",
                        "audit_sha256",
                        "requested_at_utc",
                        "evaluated_at_utc",
                        "control_version",
                        "authority_decision_id",
                        "authority_replay_nonce",
                        "authority_key_id",
                        "authority_rotation_epoch",
                        "authority_verified_at_utc",
                        "archive_decision_id",
                        "archive_document_id",
                        "archive_evidence_pack_id",
                        "archive_payload_digest",
                        "archive_key_id",
                        "archive_verified_at_utc",
                    ),
                    values,
                    strict=True,
                )
            )
            self.connection.operations[str(row["idempotency_key"])] = row
            self.rowcount = 1
            return
        raise AssertionError(f"unexpected SQL: {normalized}")

    def fetchone(self) -> Mapping[str, Any] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class LifecycleConnection:
    def __init__(self) -> None:
        self.candidate_exists = True
        self.candidate_tenant_id: str | None = "tenant-001"
        self.control = active_control_row()
        self.operations: dict[str, dict[str, Any]] = {}
        self.active_outbox_count = 0
        self.active_downstream_count = 0
        self.linked_report_evidence_pack_ids: list[str] = []
        self.control_update_rowcount = 1
        self.commits = 0
        self.rollbacks = 0
        self.cursor_instance = LifecycleCursor(self)

    def cursor(self) -> LifecycleCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class RecordingMutationCursor:
    def __init__(self) -> None:
        self.rowcount = 1
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, query: str, params: tuple[Any, ...]) -> None:
        self.calls.append((" ".join(query.split()), params))


def test_postgres_lifecycle_erasure_redacts_and_audits_in_one_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = LifecycleConnection()
    redactions: list[tuple[str, str, str]] = []
    observations: list[dict[str, object]] = []

    def redact(
        _cursor: Any, *, candidate_id: str, tenant_id: str, tombstone_sha256: str
    ) -> dict[str, int]:
        redactions.append((candidate_id, tenant_id, tombstone_sha256))
        return {"idea_candidate_record": 1, "idea_audit_event": 2}

    monkeypatch.setattr(module, "redact_candidate_graph", redact)
    monkeypatch.setattr(
        module,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )

    result = execute(connection, valid_command(DataLifecycleAction.ERASE))

    assert result.decision is DataLifecycleDecision.APPLIED
    assert result.control is not None
    assert result.control.state is DataLifecycleState.ERASED
    assert len(observations) == 1
    assert observations[0]["operation"] == "lifecycle_action"
    assert observations[0]["outcome"] == "accepted"
    assert len(result.control.tombstone_sha256 or "") == 64
    assert result.affected_row_counts == {
        "idea_candidate_record": 1,
        "idea_audit_event": 2,
        "idea_data_lifecycle_control": 1,
    }
    assert len(redactions) == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert len(connection.operations) == 1
    operation = next(iter(connection.operations.values()))
    assert operation["actor_subject"].startswith("redacted-")
    assert operation["approver_subject"] == operation["actor_subject"]
    assert operation["correlation_id"] == "corr-data-lifecycle-001"
    assert operation["trace_id"] == "trace-data-lifecycle-001"


def test_postgres_lifecycle_loads_exact_linked_report_evidence_pack_ids() -> None:
    connection = LifecycleConnection()
    connection.linked_report_evidence_pack_ids = ["report-pack-002", "report-pack-001"]

    result = execute(connection, valid_command(DataLifecycleAction.ERASE))

    assert result.decision is DataLifecycleDecision.BLOCKED
    assert result.blockers == (DataLifecycleBlocker.ARCHIVE_POSTURE_REQUIRED,)


@pytest.mark.parametrize(
    ("dry_run", "active_outbox_count", "decision", "blocker"),
    [
        (True, 0, DataLifecycleDecision.PREVIEW, None),
        (False, 1, DataLifecycleDecision.BLOCKED, DataLifecycleBlocker.ACTIVE_DELIVERY_WORK),
    ],
)
def test_postgres_lifecycle_records_preview_and_blocked_decisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    dry_run: bool,
    active_outbox_count: int,
    decision: DataLifecycleDecision,
    blocker: DataLifecycleBlocker | None,
) -> None:
    connection = LifecycleConnection()
    connection.active_outbox_count = active_outbox_count
    monkeypatch.setattr(
        module,
        "redact_candidate_graph",
        lambda *_args, **_kwargs: pytest.fail("redaction must not run"),
    )

    result = execute(
        connection,
        valid_command(DataLifecycleAction.ERASE, dry_run=dry_run),
    )

    assert result.decision is decision
    assert result.blockers == (() if blocker is None else (blocker,))
    assert result.affected_row_counts == {}
    assert connection.control["state"] == "active"
    assert len(connection.operations) == 1


def test_postgres_lifecycle_replays_matching_key_and_conflicts_changed_request() -> None:
    connection = LifecycleConnection()
    command = valid_command(DataLifecycleAction.APPLY_HOLD)
    first = execute(connection, command)

    replay = execute(connection, command)
    conflict = execute(connection, replace(command, request_fingerprint="f" * 64))

    assert first.decision is DataLifecycleDecision.APPLIED
    assert replay.decision is DataLifecycleDecision.REPLAYED
    assert replay.operation_id == first.operation_id
    assert conflict.decision is DataLifecycleDecision.CONFLICT
    assert conflict.blockers == (DataLifecycleBlocker.IDEMPOTENCY_CONFLICT,)
    assert len(connection.operations) == 1


def test_postgres_lifecycle_reserves_applied_authority_but_not_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = LifecycleConnection()
    monkeypatch.setattr(
        module,
        "redact_candidate_graph",
        lambda *_args, **_kwargs: {"idea_candidate_record": 1},
    )
    receipt = valid_authority_receipt(DataLifecycleAction.ERASE)
    preview_command = replace(
        valid_command(DataLifecycleAction.ERASE, dry_run=True),
        authority_verification_required=True,
        authority_receipt=receipt,
    )
    apply_command = replace(
        valid_command(DataLifecycleAction.ERASE),
        idempotency_key="lifecycle-erase-authorized-apply-001",
        authority_verification_required=True,
        authority_receipt=receipt,
    )

    preview = execute(connection, preview_command)
    applied = execute(connection, apply_command)
    replayed = execute(connection, apply_command)
    reused = execute(
        connection,
        replace(apply_command, idempotency_key="lifecycle-erase-authority-reuse-001"),
    )

    assert preview.decision is DataLifecycleDecision.PREVIEW
    assert applied.decision is DataLifecycleDecision.APPLIED
    assert replayed.decision is DataLifecycleDecision.REPLAYED
    assert reused.decision is DataLifecycleDecision.CONFLICT
    assert reused.blockers == (DataLifecycleBlocker.AUTHORITY_ATTESTATION_REPLAY,)
    assert len(connection.operations) == 2
    preview_row = connection.operations[preview_command.idempotency_key]
    applied_row = connection.operations[apply_command.idempotency_key]
    assert preview_row["authority_decision_id"] is None
    assert applied_row["authority_decision_id"] == receipt.decision_id
    assert applied_row["authority_replay_nonce"] == receipt.replay_nonce
    assert applied_row["authority_key_id"] == receipt.key_id


def test_postgres_lifecycle_reserves_applied_archive_posture_but_not_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = LifecycleConnection()
    connection.linked_report_evidence_pack_ids = ["report-pack-001"]
    monkeypatch.setattr(
        module,
        "redact_candidate_graph",
        lambda *_args, **_kwargs: {"idea_candidate_record": 1},
    )
    receipt = valid_archive_receipt()
    preview_command = replace(
        valid_command(DataLifecycleAction.ERASE, dry_run=True),
        archive_lifecycle_receipt=receipt,
    )
    apply_command = replace(
        valid_command(DataLifecycleAction.ERASE),
        idempotency_key="lifecycle-erase-archive-apply-001",
        archive_lifecycle_receipt=receipt,
    )

    preview = execute(connection, preview_command)
    applied = execute(connection, apply_command)
    replayed = execute(connection, apply_command)
    reused = execute(
        connection,
        replace(apply_command, idempotency_key="lifecycle-erase-archive-reuse-001"),
    )

    assert preview.decision is DataLifecycleDecision.PREVIEW
    assert applied.decision is DataLifecycleDecision.APPLIED
    assert replayed.decision is DataLifecycleDecision.REPLAYED
    assert reused.decision is DataLifecycleDecision.CONFLICT
    assert reused.blockers == (DataLifecycleBlocker.ARCHIVE_POSTURE_REPLAY,)
    preview_row = connection.operations[preview_command.idempotency_key]
    applied_row = connection.operations[apply_command.idempotency_key]
    assert preview_row["archive_decision_id"] is None
    assert applied_row["archive_decision_id"] == receipt.decision_id
    assert applied_row["archive_document_id"] == receipt.document_id
    assert applied_row["archive_evidence_pack_id"] == receipt.evidence_pack_id
    assert applied_row["archive_payload_digest"] == receipt.payload_digest


def test_postgres_lifecycle_purge_removes_only_governed_payload_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = LifecycleConnection()
    connection.control = erased_control_row()
    purged: list[str] = []

    def purge(_cursor: Any, *, candidate_id: str) -> dict[str, int]:
        purged.append(candidate_id)
        return {"idea_feedback_event": 1, "idea_ai_explanation_lineage": 1}

    monkeypatch.setattr(module, "purge_expired_candidate_payloads", purge)

    result = execute(connection, valid_command(DataLifecycleAction.PURGE))

    assert result.decision is DataLifecycleDecision.APPLIED
    assert result.control is not None
    assert result.control.state is DataLifecycleState.PURGED
    assert purged == ["candidate-001"]
    assert result.affected_row_counts["idea_data_lifecycle_control"] == 1


def test_postgres_lifecycle_rolls_back_when_control_lock_is_lost() -> None:
    connection = LifecycleConnection()
    connection.control_update_rowcount = 0

    with pytest.raises(RuntimeError, match="lost tenant-scoped aggregate lock"):
        execute(connection, valid_command(DataLifecycleAction.APPLY_HOLD))

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.operations == {}


def test_postgres_purge_uses_terminal_control_after_access_scope_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = LifecycleConnection()
    connection.candidate_tenant_id = None
    connection.control = erased_control_row()
    monkeypatch.setattr(module, "purge_expired_candidate_payloads", lambda *_args, **_kwargs: {})

    result = execute(connection, valid_command(DataLifecycleAction.PURGE))

    assert result.decision is DataLifecycleDecision.APPLIED
    assert result.control is not None
    assert result.control.state is DataLifecycleState.PURGED


def test_postgres_lifecycle_not_found_is_source_safe_and_not_persisted() -> None:
    connection = LifecycleConnection()
    connection.candidate_exists = False
    connection.control = {}

    result = execute(connection, valid_command(DataLifecycleAction.ERASE))

    assert result.decision is DataLifecycleDecision.NOT_FOUND
    assert result.blockers == (DataLifecycleBlocker.CANDIDATE_NOT_FOUND,)
    assert len(result.audit_sha256) == 64
    assert connection.operations == {}
    assert connection.commits == 1


def test_redaction_and_purge_cover_the_declared_candidate_graph_without_raw_identity() -> None:
    cursor = RecordingMutationCursor()

    redacted = redact_candidate_graph(
        cursor,
        candidate_id="candidate-001",
        tenant_id="tenant-001",
        tombstone_sha256="d" * 64,
    )
    purged = purge_expired_candidate_payloads(cursor, candidate_id="candidate-001")

    assert set(redacted) == {
        "idea_candidate_record",
        "idea_candidate_state_quarantine",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_conversion_outcome",
        "idea_conversion_outcome_quarantine",
        "idea_report_evidence_pack_request",
        "idea_ai_explanation_lineage",
        "idea_data_lifecycle_operation",
        "idea_outbox_event",
        "idea_outbox_recovery_audit",
        "idea_downstream_submission",
    }
    assert set(purged) == {
        "idea_candidate_state_quarantine",
        "idea_conversion_outcome_quarantine",
        "idea_ai_explanation_lineage",
        "idea_feedback_event",
        "idea_downstream_submission",
        "idea_outbox_recovery_audit",
        "idea_outbox_event",
        "idea_idempotency_record",
    }
    serialized_params = repr([params for _, params in cursor.calls])
    assert "privacy-operator" not in serialized_params
    assert "privacy-approver" not in serialized_params
    assert "redacted-" in serialized_params


def execute(
    connection: LifecycleConnection,
    command: DataLifecycleCommand,
) -> DataLifecycleOperationResult:
    return PostgresDataLifecycleRepository(connection).execute_data_lifecycle(
        command,
        evaluated_at_utc=NOW,
        evaluator=evaluate_data_lifecycle,
    )


def valid_command(
    action: DataLifecycleAction,
    *,
    dry_run: bool = False,
) -> DataLifecycleCommand:
    authority_ref = (
        "bank-legal-and-records-governance:decision-001"
        if action in {DataLifecycleAction.APPLY_HOLD, DataLifecycleAction.RELEASE_HOLD}
        else "bank-privacy-governance:decision-001"
    )
    return DataLifecycleCommand(
        candidate_id="candidate-001",
        tenant_id="tenant-001",
        action=action,
        actor_subject="privacy-operator-001",
        approver_subject="privacy-approver-001",
        authority_ref=authority_ref,
        reason="approved_lifecycle_request",
        change_reference="privacy-case-001",
        idempotency_key=f"lifecycle-{action.value}-001",
        request_fingerprint="a" * 64,
        correlation_id="corr-data-lifecycle-001",
        trace_id="trace-data-lifecycle-001",
        requested_at_utc=NOW - timedelta(minutes=1),
        dry_run=dry_run,
    )


def valid_authority_receipt(
    action: DataLifecycleAction,
) -> VerifiedLifecycleAuthorityReceipt:
    authority_domain = (
        LifecycleAuthorityDomain.LEGAL_AND_RECORDS
        if action in {DataLifecycleAction.APPLY_HOLD, DataLifecycleAction.RELEASE_HOLD}
        else LifecycleAuthorityDomain.PRIVACY
    )
    authority_ref = (
        "bank-legal-and-records-governance:decision-001"
        if authority_domain is LifecycleAuthorityDomain.LEGAL_AND_RECORDS
        else "bank-privacy-governance:decision-001"
    )
    return VerifiedLifecycleAuthorityReceipt(
        decision_id=f"lifecycle-decision-{action.value}-001",
        replay_nonce="e" * 64,
        tenant_id="tenant-001",
        candidate_id="candidate-001",
        action=action,
        authority_domain=authority_domain,
        authority_ref=authority_ref,
        change_reference="privacy-case-001",
        key_id="lifecycle-key-001",
        rotation_epoch=3,
        issued_at_utc=NOW - timedelta(minutes=3),
        effective_at_utc=NOW - timedelta(minutes=2),
        expires_at_utc=NOW + timedelta(minutes=5),
        verified_at_utc=NOW - timedelta(minutes=1),
    )


def valid_archive_receipt() -> VerifiedArchiveLifecycleReceipt:
    return VerifiedArchiveLifecycleReceipt(
        decision_id="archive-decision-001",
        document_id="document-001",
        evidence_pack_id="report-pack-001",
        candidate_id="candidate-001",
        tenant_id="tenant-001",
        retention_policy_id="generated-report-standard",
        legal_hold_status=ArchiveLegalHoldStatus.CLEAR,
        purge_status=ArchivePurgeStatus.NOT_ELIGIBLE,
        lifecycle_action=ArchiveLifecycleAction.RETAIN,
        payload_digest="sha256:" + "f" * 64,
        key_id="archive-key-001",
        issued_at_utc=NOW - timedelta(minutes=2),
        expires_at_utc=NOW + timedelta(minutes=3),
        verified_at_utc=NOW - timedelta(minutes=1),
    )


def active_control_row() -> dict[str, Any]:
    return {
        "candidate_id": "candidate-001",
        "tenant_id": "tenant-001",
        "policy_ref": REGULATED_ADVISORY_POLICY_REF,
        "state": "active",
        "retention_expires_at_utc": NOW - timedelta(days=1),
        "version": 1,
        "updated_at_utc": NOW - timedelta(days=2),
        "held_from_state": None,
        "hold_authority_ref": None,
        "hold_change_reference": None,
        "held_at_utc": None,
        "erased_at_utc": None,
        "purged_at_utc": None,
        "tombstone_sha256": None,
    }


def erased_control_row() -> dict[str, Any]:
    return {
        **active_control_row(),
        "state": "erased",
        "erased_at_utc": NOW - timedelta(days=2),
        "tombstone_sha256": "c" * 64,
    }


def _unwrap(value: Any) -> Any:
    return value.obj if hasattr(value, "obj") else value
