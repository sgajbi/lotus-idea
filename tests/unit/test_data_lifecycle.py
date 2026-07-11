from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.data_lifecycle import ExecuteDataLifecycle
from app.domain.data_lifecycle import (
    REGULATED_ADVISORY_POLICY_REF,
    REPORT_EVIDENCE_RETENTION_POLICY_REF,
    DataLifecycleAction,
    DataLifecycleBlocker,
    DataLifecycleCandidateContext,
    DataLifecycleCommand,
    DataLifecycleControl,
    DataLifecycleDecision,
    DataLifecycleOperationResult,
    DataLifecycleState,
    evaluate_data_lifecycle,
    resolve_external_retention_policy_ref,
)

NOW = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)


def test_report_retention_policy_resolves_only_governed_reference() -> None:
    assert (
        resolve_external_retention_policy_ref(REPORT_EVIDENCE_RETENTION_POLICY_REF)
        == REGULATED_ADVISORY_POLICY_REF
    )

    with pytest.raises(ValueError, match="not governed"):
        resolve_external_retention_policy_ref("caller:chosen:retention:v1")


@pytest.mark.parametrize("dry_run", [True, False])
def test_apply_hold_projects_or_applies_complete_hold_state(dry_run: bool) -> None:
    command = valid_command(DataLifecycleAction.APPLY_HOLD, dry_run=dry_run)

    evaluation = evaluate_data_lifecycle(command, valid_context(), evaluated_at_utc=NOW)

    assert evaluation.decision is (
        DataLifecycleDecision.PREVIEW if dry_run else DataLifecycleDecision.APPLIED
    )
    assert evaluation.blockers == ()
    assert evaluation.projected_control is not None
    assert evaluation.projected_control.state is DataLifecycleState.HELD
    assert evaluation.projected_control.held_from_state is DataLifecycleState.ACTIVE
    assert evaluation.projected_control.hold_authority_ref == command.authority_ref
    assert evaluation.projected_control.version == 2


def test_hold_and_release_enforce_state_authority_and_dual_approval() -> None:
    held = held_control()
    held_context = valid_context(control=held)

    duplicate_hold = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.APPLY_HOLD), held_context, evaluated_at_utc=NOW
    )
    missing_approval = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.RELEASE_HOLD, approver_subject=None),
        held_context,
        evaluated_at_utc=NOW,
    )
    wrong_authority = evaluate_data_lifecycle(
        replace(
            valid_command(DataLifecycleAction.RELEASE_HOLD),
            authority_ref="bank-privacy-governance:decision-001",
        ),
        held_context,
        evaluated_at_utc=NOW,
    )
    released = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.RELEASE_HOLD), held_context, evaluated_at_utc=NOW
    )

    assert duplicate_hold.blockers == (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,)
    assert missing_approval.blockers == (DataLifecycleBlocker.DUAL_AUTHORIZATION_REQUIRED,)
    assert wrong_authority.blockers == (DataLifecycleBlocker.AUTHORITY_INVALID,)
    assert released.decision is DataLifecycleDecision.APPLIED
    assert released.projected_control is not None
    assert released.projected_control.state is DataLifecycleState.ACTIVE
    assert released.projected_control.hold_authority_ref is None


@pytest.mark.parametrize(
    ("context_changes", "command_changes", "blocker"),
    [
        (
            {"candidate_tenant_id": None},
            {},
            DataLifecycleBlocker.TENANT_SCOPE_MISSING,
        ),
        (
            {"candidate_tenant_id": "tenant-other"},
            {},
            DataLifecycleBlocker.TENANT_SCOPE_MISMATCH,
        ),
        (
            {"control": None},
            {},
            DataLifecycleBlocker.LIFECYCLE_CONTROL_MISSING,
        ),
        (
            {"control": "unknown_policy"},
            {},
            DataLifecycleBlocker.RETENTION_POLICY_UNKNOWN,
        ),
        (
            {},
            {"authority_ref": "bank-legal-and-records-governance:decision-001"},
            DataLifecycleBlocker.AUTHORITY_INVALID,
        ),
    ],
)
def test_erasure_fails_closed_on_scope_policy_or_authority(
    context_changes: dict[str, Any],
    command_changes: dict[str, Any],
    blocker: DataLifecycleBlocker,
) -> None:
    if context_changes.get("control") == "unknown_policy":
        context_changes = {
            "control": replace(active_control(), policy_ref="lotus-idea:unknown:x:v1")
        }
    context = valid_context(**context_changes)
    command = replace(valid_command(DataLifecycleAction.ERASE), **command_changes)
    evaluation = evaluate_data_lifecycle(command, context, evaluated_at_utc=NOW)

    assert evaluation.decision is DataLifecycleDecision.BLOCKED
    assert blocker in evaluation.blockers


def test_erasure_blocks_holds_and_active_delivery_then_redacts_atomically() -> None:
    held = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.ERASE),
        valid_context(control=held_control()),
        evaluated_at_utc=NOW,
    )
    active_delivery = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.ERASE),
        valid_context(active_outbox_count=1, active_downstream_count=1),
        evaluated_at_utc=NOW,
    )
    erased = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.ERASE), valid_context(), evaluated_at_utc=NOW
    )

    assert held.blockers == (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,)
    assert active_delivery.blockers == (DataLifecycleBlocker.ACTIVE_DELIVERY_WORK,)
    assert erased.decision is DataLifecycleDecision.APPLIED
    assert erased.redaction_required is True
    assert erased.projected_control is not None
    assert erased.projected_control.state is DataLifecycleState.ERASED
    assert erased.projected_control.erased_at_utc == NOW

    replay = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.ERASE),
        valid_context(control=erased.projected_control),
        evaluated_at_utc=NOW + timedelta(minutes=1),
    )
    assert replay.decision is DataLifecycleDecision.REPLAYED


def test_lifecycle_evaluation_reports_missing_candidate_and_rejects_future_request() -> None:
    missing = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.ERASE),
        valid_context(candidate_exists=False),
        evaluated_at_utc=NOW,
    )

    assert missing.decision is DataLifecycleDecision.NOT_FOUND
    assert missing.blockers == (DataLifecycleBlocker.CANDIDATE_NOT_FOUND,)

    with pytest.raises(ValueError, match="must not be after evaluated_at_utc"):
        evaluate_data_lifecycle(
            replace(
                valid_command(DataLifecycleAction.ERASE),
                requested_at_utc=NOW + timedelta(seconds=1),
            ),
            valid_context(),
            evaluated_at_utc=NOW,
        )


def test_purge_requires_prior_erasure_expiry_and_no_delivery_work() -> None:
    active = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.PURGE), valid_context(), evaluated_at_utc=NOW
    )
    not_expired = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.PURGE),
        valid_context(control=erased_control(retention_expires_at_utc=NOW + timedelta(days=1))),
        evaluated_at_utc=NOW,
    )
    active_delivery = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.PURGE),
        valid_context(control=erased_control(), active_outbox_count=1),
        evaluated_at_utc=NOW,
    )

    assert DataLifecycleBlocker.INVALID_STATE in active.blockers
    assert not_expired.blockers == (DataLifecycleBlocker.RETENTION_NOT_EXPIRED,)
    assert active_delivery.blockers == (DataLifecycleBlocker.ACTIVE_DELIVERY_WORK,)


def test_purge_projects_bounded_payload_removal_and_replays_terminal_state() -> None:
    purged = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.PURGE),
        valid_context(control=erased_control()),
        evaluated_at_utc=NOW,
    )

    assert purged.decision is DataLifecycleDecision.APPLIED
    assert purged.purge_required is True
    assert purged.projected_control is not None
    assert purged.projected_control.state is DataLifecycleState.PURGED
    assert purged.projected_control.purged_at_utc == NOW

    replay = evaluate_data_lifecycle(
        valid_command(DataLifecycleAction.PURGE),
        valid_context(control=purged.projected_control),
        evaluated_at_utc=NOW + timedelta(minutes=1),
    )
    assert replay.decision is DataLifecycleDecision.REPLAYED


def test_lifecycle_models_reject_incoherent_or_sensitive_evidence_shapes() -> None:
    with pytest.raises(ValueError, match="complete hold metadata"):
        replace(active_control(), state=DataLifecycleState.HELD)
    with pytest.raises(ValueError, match="forbids hold metadata"):
        replace(active_control(), hold_authority_ref="bank-legal:hold-001")
    with pytest.raises(ValueError, match="require erased_at_utc"):
        replace(active_control(), state=DataLifecycleState.ERASED)
    with pytest.raises(ValueError, match="non-negative integer"):
        replace(valid_context(), active_outbox_count=-1)
    with pytest.raises(ValueError, match="source-safe reference"):
        replace(valid_command(DataLifecycleAction.ERASE), actor_subject="raw user name")
    with pytest.raises(ValueError, match="must be distinct"):
        replace(
            valid_command(DataLifecycleAction.ERASE),
            trace_id="corr-data-lifecycle-001",
        )
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        valid_result(audit_sha256="bad")
    with pytest.raises(ValueError, match="Idea-owned table"):
        valid_result(affected_row_counts={"foreign_table": 1})


def test_application_keeps_evaluation_inside_repository_execution_boundary() -> None:
    repository = StubLifecycleRepository(valid_result())
    command = valid_command(DataLifecycleAction.ERASE)

    result = ExecuteDataLifecycle(repository, now=lambda: NOW).execute(command)

    assert result is repository.result
    assert repository.command is command
    assert repository.evaluated_at_utc == NOW
    assert repository.evaluator is evaluate_data_lifecycle


class StubLifecycleRepository:
    def __init__(self, result: DataLifecycleOperationResult) -> None:
        self.result = result
        self.command: DataLifecycleCommand | None = None
        self.evaluated_at_utc: datetime | None = None
        self.evaluator: Any = None

    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: Any,
    ) -> DataLifecycleOperationResult:
        self.command = command
        self.evaluated_at_utc = evaluated_at_utc
        self.evaluator = evaluator
        return self.result


def active_control() -> DataLifecycleControl:
    return DataLifecycleControl(
        candidate_id="candidate-001",
        tenant_id="tenant-001",
        policy_ref=REGULATED_ADVISORY_POLICY_REF,
        state=DataLifecycleState.ACTIVE,
        retention_expires_at_utc=NOW - timedelta(days=1),
        version=1,
        updated_at_utc=NOW - timedelta(days=2),
    )


def held_control() -> DataLifecycleControl:
    return replace(
        active_control(),
        state=DataLifecycleState.HELD,
        held_from_state=DataLifecycleState.ACTIVE,
        hold_authority_ref="bank-legal-and-records-governance:hold-001",
        hold_change_reference="legal-case-001",
        held_at_utc=NOW - timedelta(hours=1),
    )


def erased_control(*, retention_expires_at_utc: datetime | None = None) -> DataLifecycleControl:
    return replace(
        active_control(),
        state=DataLifecycleState.ERASED,
        retention_expires_at_utc=retention_expires_at_utc or NOW - timedelta(days=1),
        erased_at_utc=NOW - timedelta(days=2),
    )


def valid_context(**changes: Any) -> DataLifecycleCandidateContext:
    values: dict[str, Any] = {
        "candidate_exists": True,
        "candidate_tenant_id": "tenant-001",
        "control": active_control(),
        "active_outbox_count": 0,
        "active_downstream_count": 0,
    }
    values.update(changes)
    return DataLifecycleCandidateContext(**values)


def valid_command(
    action: DataLifecycleAction,
    *,
    dry_run: bool = False,
    approver_subject: str | None = "privacy-approver-001",
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
        approver_subject=approver_subject,
        authority_ref=authority_ref,
        reason="approved_lifecycle_request",
        change_reference="privacy-case-001",
        idempotency_key="lifecycle-idempotency-001",
        request_fingerprint="a" * 64,
        correlation_id="corr-data-lifecycle-001",
        trace_id="trace-data-lifecycle-001",
        requested_at_utc=NOW - timedelta(minutes=1),
        dry_run=dry_run,
    )


def valid_result(**changes: Any) -> DataLifecycleOperationResult:
    values: dict[str, Any] = {
        "operation_id": "lifecycle-operation-001",
        "decision": DataLifecycleDecision.APPLIED,
        "control": erased_control(),
        "blockers": (),
        "dry_run": False,
        "audit_sha256": "b" * 64,
        "affected_row_counts": {"idea_candidate_record": 1},
    }
    values.update(changes)
    return DataLifecycleOperationResult(**values)
