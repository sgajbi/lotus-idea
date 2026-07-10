from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Mapping

REGULATED_ADVISORY_POLICY_REF = "lotus-idea:regulated-advisory-evidence:seven-year:v1"
OPERATIONAL_DELIVERY_POLICY_REF = "lotus-idea:operational-delivery:four-hundred-day:v1"
QUARANTINE_POLICY_REF = "lotus-idea:quarantine:ninety-day:v1"
REPORT_EVIDENCE_RETENTION_POLICY_REF = "lotus-report:idea-evidence-retention:v1"
KNOWN_LOCAL_POLICY_REFS = frozenset(
    {
        REGULATED_ADVISORY_POLICY_REF,
        OPERATIONAL_DELIVERY_POLICY_REF,
        QUARANTINE_POLICY_REF,
    }
)
EXTERNAL_POLICY_MAPPINGS = {
    REPORT_EVIDENCE_RETENTION_POLICY_REF: REGULATED_ADVISORY_POLICY_REF,
}
REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")


class DataLifecycleState(StrEnum):
    ACTIVE = "active"
    HELD = "held"
    ERASED = "erased"
    PURGED = "purged"


class DataLifecycleAction(StrEnum):
    APPLY_HOLD = "apply_hold"
    RELEASE_HOLD = "release_hold"
    ERASE = "erase"
    PURGE = "purge"


class DataLifecycleDecision(StrEnum):
    PREVIEW = "preview"
    APPLIED = "applied"
    REPLAYED = "replayed"
    BLOCKED = "blocked"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


class DataLifecycleBlocker(StrEnum):
    CANDIDATE_NOT_FOUND = "candidate_not_found"
    TENANT_SCOPE_MISSING = "tenant_scope_missing"
    TENANT_SCOPE_MISMATCH = "tenant_scope_mismatch"
    LIFECYCLE_CONTROL_MISSING = "lifecycle_control_missing"
    RETENTION_POLICY_UNKNOWN = "retention_policy_unknown"
    AUTHORITY_INVALID = "authority_invalid"
    DUAL_AUTHORIZATION_REQUIRED = "dual_authorization_required"
    LEGAL_HOLD_ACTIVE = "legal_hold_active"
    LEGAL_HOLD_NOT_ACTIVE = "legal_hold_not_active"
    ACTIVE_DELIVERY_WORK = "active_delivery_work"
    RETENTION_NOT_EXPIRED = "retention_not_expired"
    INVALID_STATE = "invalid_state"


@dataclass(frozen=True)
class DataLifecycleControl:
    candidate_id: str
    tenant_id: str
    policy_ref: str
    state: DataLifecycleState
    retention_expires_at_utc: datetime
    version: int
    updated_at_utc: datetime
    held_from_state: DataLifecycleState | None = None
    hold_authority_ref: str | None = None
    hold_change_reference: str | None = None
    held_at_utc: datetime | None = None
    erased_at_utc: datetime | None = None
    purged_at_utc: datetime | None = None
    tombstone_sha256: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "tenant_id", "policy_ref"):
            _require_reference(str(getattr(self, field_name)), field_name)
        _require_utc(self.retention_expires_at_utc, "retention_expires_at_utc")
        _require_utc(self.updated_at_utc, "updated_at_utc")
        if self.version <= 0:
            raise ValueError("version must be positive")
        _validate_hold_state(self)
        _validate_terminal_state(self)


@dataclass(frozen=True)
class DataLifecycleCandidateContext:
    candidate_exists: bool
    candidate_tenant_id: str | None
    control: DataLifecycleControl | None
    active_outbox_count: int
    active_downstream_count: int

    def __post_init__(self) -> None:
        if self.candidate_tenant_id is not None:
            _require_reference(self.candidate_tenant_id, "candidate_tenant_id")
        for field_name in ("active_outbox_count", "active_downstream_count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")


@dataclass(frozen=True)
class DataLifecycleCommand:
    candidate_id: str
    tenant_id: str
    action: DataLifecycleAction
    actor_subject: str
    authority_ref: str
    reason: str
    change_reference: str
    idempotency_key: str
    request_fingerprint: str
    requested_at_utc: datetime
    dry_run: bool
    approver_subject: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "tenant_id",
            "actor_subject",
            "authority_ref",
            "reason",
            "change_reference",
            "idempotency_key",
            "request_fingerprint",
        ):
            _require_reference(str(getattr(self, field_name)), field_name)
        if self.approver_subject is not None:
            _require_reference(self.approver_subject, "approver_subject")
        _require_utc(self.requested_at_utc, "requested_at_utc")


@dataclass(frozen=True)
class DataLifecycleEvaluation:
    decision: DataLifecycleDecision
    current_control: DataLifecycleControl | None
    projected_control: DataLifecycleControl | None
    blockers: tuple[DataLifecycleBlocker, ...]
    redaction_required: bool = False
    purge_required: bool = False


@dataclass(frozen=True)
class DataLifecycleOperationResult:
    operation_id: str
    decision: DataLifecycleDecision
    control: DataLifecycleControl | None
    blockers: tuple[DataLifecycleBlocker, ...]
    dry_run: bool
    audit_sha256: str
    affected_row_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        _require_reference(self.operation_id, "operation_id")
        if not re.fullmatch(r"[a-f0-9]{64}", self.audit_sha256):
            raise ValueError("audit_sha256 must be a lowercase SHA-256 digest")
        for table, count in self.affected_row_counts.items():
            if not re.fullmatch(r"idea_[a-z0-9_]+", table):
                raise ValueError("affected_row_counts must use Idea-owned table names")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("affected_row_counts values must be non-negative integers")


def resolve_external_retention_policy_ref(policy_ref: str) -> str:
    try:
        return EXTERNAL_POLICY_MAPPINGS[policy_ref]
    except KeyError as exc:
        raise ValueError("retention policy reference is not governed") from exc


def evaluate_data_lifecycle(
    command: DataLifecycleCommand,
    context: DataLifecycleCandidateContext,
    *,
    evaluated_at_utc: datetime,
) -> DataLifecycleEvaluation:
    _require_utc(evaluated_at_utc, "evaluated_at_utc")
    if not context.candidate_exists:
        return DataLifecycleEvaluation(
            decision=DataLifecycleDecision.NOT_FOUND,
            current_control=context.control,
            projected_control=context.control,
            blockers=(DataLifecycleBlocker.CANDIDATE_NOT_FOUND,),
        )
    if command.requested_at_utc > evaluated_at_utc:
        raise ValueError("requested_at_utc must not be after evaluated_at_utc")
    blockers = _common_blockers(command, context)
    control = context.control
    if blockers or control is None:
        return _blocked(control, blockers)

    if command.action is DataLifecycleAction.APPLY_HOLD:
        return _evaluate_hold(command, control, evaluated_at_utc)
    if command.action is DataLifecycleAction.RELEASE_HOLD:
        return _evaluate_release(command, control, evaluated_at_utc)
    if command.action is DataLifecycleAction.ERASE:
        return _evaluate_erase(command, context, control, evaluated_at_utc)
    return _evaluate_purge(command, context, control, evaluated_at_utc)


def _common_blockers(
    command: DataLifecycleCommand,
    context: DataLifecycleCandidateContext,
) -> tuple[DataLifecycleBlocker, ...]:
    blockers: list[DataLifecycleBlocker] = []
    if context.candidate_tenant_id is None:
        blockers.append(DataLifecycleBlocker.TENANT_SCOPE_MISSING)
    elif context.candidate_tenant_id != command.tenant_id:
        blockers.append(DataLifecycleBlocker.TENANT_SCOPE_MISMATCH)
    if context.control is None:
        blockers.append(DataLifecycleBlocker.LIFECYCLE_CONTROL_MISSING)
    elif context.control.policy_ref not in KNOWN_LOCAL_POLICY_REFS:
        blockers.append(DataLifecycleBlocker.RETENTION_POLICY_UNKNOWN)
    if not _authority_matches(command):
        blockers.append(DataLifecycleBlocker.AUTHORITY_INVALID)
    if not command.dry_run and _requires_dual_authorization(command.action):
        if command.approver_subject is None or command.approver_subject == command.actor_subject:
            blockers.append(DataLifecycleBlocker.DUAL_AUTHORIZATION_REQUIRED)
    return tuple(blockers)


def _evaluate_hold(
    command: DataLifecycleCommand,
    control: DataLifecycleControl,
    evaluated_at_utc: datetime,
) -> DataLifecycleEvaluation:
    if control.state is DataLifecycleState.HELD:
        return _blocked(control, (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,))
    projected = replace(
        control,
        state=DataLifecycleState.HELD,
        version=control.version + 1,
        updated_at_utc=evaluated_at_utc,
        held_from_state=control.state,
        hold_authority_ref=command.authority_ref,
        hold_change_reference=command.change_reference,
        held_at_utc=evaluated_at_utc,
    )
    return _approved(command, control, projected)


def _evaluate_release(
    command: DataLifecycleCommand,
    control: DataLifecycleControl,
    evaluated_at_utc: datetime,
) -> DataLifecycleEvaluation:
    if control.state is not DataLifecycleState.HELD or control.held_from_state is None:
        return _blocked(control, (DataLifecycleBlocker.LEGAL_HOLD_NOT_ACTIVE,))
    projected = replace(
        control,
        state=control.held_from_state,
        version=control.version + 1,
        updated_at_utc=evaluated_at_utc,
        held_from_state=None,
        hold_authority_ref=None,
        hold_change_reference=None,
        held_at_utc=None,
    )
    return _approved(command, control, projected)


def _evaluate_erase(
    command: DataLifecycleCommand,
    context: DataLifecycleCandidateContext,
    control: DataLifecycleControl,
    evaluated_at_utc: datetime,
) -> DataLifecycleEvaluation:
    if control.state is DataLifecycleState.HELD:
        return _blocked(control, (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,))
    if control.state in {DataLifecycleState.ERASED, DataLifecycleState.PURGED}:
        return _replayed(control)
    if _has_active_delivery(context):
        return _blocked(control, (DataLifecycleBlocker.ACTIVE_DELIVERY_WORK,))
    projected = replace(
        control,
        state=DataLifecycleState.ERASED,
        version=control.version + 1,
        updated_at_utc=evaluated_at_utc,
        erased_at_utc=evaluated_at_utc,
    )
    return _approved(command, control, projected, redaction_required=True)


def _evaluate_purge(
    command: DataLifecycleCommand,
    context: DataLifecycleCandidateContext,
    control: DataLifecycleControl,
    evaluated_at_utc: datetime,
) -> DataLifecycleEvaluation:
    if control.state is DataLifecycleState.HELD:
        return _blocked(control, (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,))
    if control.state is DataLifecycleState.PURGED:
        return _replayed(control)
    blockers: list[DataLifecycleBlocker] = []
    if control.state is not DataLifecycleState.ERASED:
        blockers.append(DataLifecycleBlocker.INVALID_STATE)
    if evaluated_at_utc < control.retention_expires_at_utc:
        blockers.append(DataLifecycleBlocker.RETENTION_NOT_EXPIRED)
    if _has_active_delivery(context):
        blockers.append(DataLifecycleBlocker.ACTIVE_DELIVERY_WORK)
    if blockers:
        return _blocked(control, tuple(blockers))
    projected = replace(
        control,
        state=DataLifecycleState.PURGED,
        version=control.version + 1,
        updated_at_utc=evaluated_at_utc,
        purged_at_utc=evaluated_at_utc,
    )
    return _approved(command, control, projected, purge_required=True)


def _approved(
    command: DataLifecycleCommand,
    current: DataLifecycleControl,
    projected: DataLifecycleControl,
    *,
    redaction_required: bool = False,
    purge_required: bool = False,
) -> DataLifecycleEvaluation:
    return DataLifecycleEvaluation(
        decision=(
            DataLifecycleDecision.PREVIEW if command.dry_run else DataLifecycleDecision.APPLIED
        ),
        current_control=current,
        projected_control=projected,
        blockers=(),
        redaction_required=redaction_required,
        purge_required=purge_required,
    )


def _blocked(
    control: DataLifecycleControl | None,
    blockers: tuple[DataLifecycleBlocker, ...],
) -> DataLifecycleEvaluation:
    return DataLifecycleEvaluation(
        decision=DataLifecycleDecision.BLOCKED,
        current_control=control,
        projected_control=control,
        blockers=blockers,
    )


def _replayed(control: DataLifecycleControl) -> DataLifecycleEvaluation:
    return DataLifecycleEvaluation(
        decision=DataLifecycleDecision.REPLAYED,
        current_control=control,
        projected_control=control,
        blockers=(),
    )


def _authority_matches(command: DataLifecycleCommand) -> bool:
    prefix = (
        "bank-legal-and-records-governance:"
        if command.action in {DataLifecycleAction.APPLY_HOLD, DataLifecycleAction.RELEASE_HOLD}
        else "bank-privacy-governance:"
    )
    return command.authority_ref.startswith(prefix)


def _requires_dual_authorization(action: DataLifecycleAction) -> bool:
    return action in {
        DataLifecycleAction.RELEASE_HOLD,
        DataLifecycleAction.ERASE,
        DataLifecycleAction.PURGE,
    }


def _has_active_delivery(context: DataLifecycleCandidateContext) -> bool:
    return context.active_outbox_count > 0 or context.active_downstream_count > 0


def _validate_hold_state(control: DataLifecycleControl) -> None:
    hold_values = (
        control.held_from_state,
        control.hold_authority_ref,
        control.hold_change_reference,
        control.held_at_utc,
    )
    if control.state is DataLifecycleState.HELD:
        if any(value is None for value in hold_values):
            raise ValueError("held lifecycle control requires complete hold metadata")
        if control.held_from_state is DataLifecycleState.HELD:
            raise ValueError("held_from_state cannot be held")
        assert control.held_at_utc is not None
        _require_reference(str(control.hold_authority_ref), "hold_authority_ref")
        _require_reference(str(control.hold_change_reference), "hold_change_reference")
        _require_utc(control.held_at_utc, "held_at_utc")
    elif any(value is not None for value in hold_values):
        raise ValueError("non-held lifecycle control forbids hold metadata")


def _validate_terminal_state(control: DataLifecycleControl) -> None:
    if control.erased_at_utc is not None:
        _require_utc(control.erased_at_utc, "erased_at_utc")
    if control.purged_at_utc is not None:
        _require_utc(control.purged_at_utc, "purged_at_utc")
    effective_state = (
        control.held_from_state if control.state is DataLifecycleState.HELD else control.state
    )
    if effective_state in {DataLifecycleState.ERASED, DataLifecycleState.PURGED}:
        if control.erased_at_utc is None:
            raise ValueError("erased and purged lifecycle controls require erased_at_utc")
    elif control.erased_at_utc is not None or control.purged_at_utc is not None:
        raise ValueError("active lifecycle control forbids erasure or purge timestamps")
    if effective_state is DataLifecycleState.PURGED and control.purged_at_utc is None:
        raise ValueError("purged lifecycle control requires purged_at_utc")
    if effective_state is not DataLifecycleState.PURGED and control.purged_at_utc is not None:
        raise ValueError("non-purged lifecycle control forbids purged_at_utc")
    if control.tombstone_sha256 is not None and not re.fullmatch(
        r"[a-f0-9]{64}", control.tombstone_sha256
    ):
        raise ValueError("tombstone_sha256 must be a lowercase SHA-256 digest")


def _require_reference(value: str, field_name: str) -> None:
    if not REFERENCE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a source-safe reference")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
