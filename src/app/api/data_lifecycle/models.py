from __future__ import annotations

from datetime import datetime
import hashlib
import json

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.temporal_validation import require_timezone_aware
from app.domain.data_lifecycle import (
    DataLifecycleAction,
    DataLifecycleBlocker,
    DataLifecycleCommand,
    DataLifecycleDecision,
    DataLifecycleOperationResult,
    DataLifecycleState,
)
from app.security.caller_context import CallerContext
from app.domain.outbox.events import EventLineageContext
from app.domain.data_lifecycle.authority import VerifiedLifecycleAuthorityReceipt
from app.domain.data_lifecycle.archive_posture import VerifiedArchiveLifecycleReceipt
from app.integration.data_lifecycle.authority_contract import LifecycleAuthorityProducerDecision
from app.integration.data_lifecycle.archive_posture_contract import (
    ArchiveLifecycleProducerDecision,
)

SOURCE_SAFE_REFERENCE = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$"


class DataLifecycleActionRequest(CamelModel):
    tenant_id: str = Field(..., alias="tenantId", pattern=SOURCE_SAFE_REFERENCE)
    action: DataLifecycleAction
    authority_ref: str = Field(..., alias="authorityRef", pattern=SOURCE_SAFE_REFERENCE)
    reason: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9_]+$")
    change_reference: str = Field(
        ...,
        alias="changeReference",
        pattern=SOURCE_SAFE_REFERENCE,
    )
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    dry_run: bool = Field(..., alias="dryRun")
    approver_subject: str | None = Field(
        default=None,
        alias="approverSubject",
        pattern=SOURCE_SAFE_REFERENCE,
    )
    authority_decision: LifecycleAuthorityProducerDecision | None = Field(
        default=None,
        alias="authorityDecision",
    )
    archive_lifecycle_decision: ArchiveLifecycleProducerDecision | None = Field(
        default=None,
        alias="archiveLifecycleDecision",
    )

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="requestedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        idempotency_key: str,
        event_lineage: EventLineageContext,
        authority_verification_required: bool = False,
        authority_receipt: VerifiedLifecycleAuthorityReceipt | None = None,
        archive_lifecycle_receipt: VerifiedArchiveLifecycleReceipt | None = None,
    ) -> DataLifecycleCommand:
        payload = {
            "action": self.action.value,
            "approver_subject": self.approver_subject,
            "authority_ref": self.authority_ref,
            "candidate_id": candidate_id,
            "change_reference": self.change_reference,
            "dry_run": self.dry_run,
            "reason": self.reason,
            "requested_at_utc": self.requested_at_utc.isoformat(),
            "tenant_id": self.tenant_id,
            "authority_decision_sha256": _producer_decision_sha256(self.authority_decision),
            "archive_lifecycle_decision_sha256": _producer_decision_sha256(
                self.archive_lifecycle_decision
            ),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return DataLifecycleCommand(
            candidate_id=candidate_id,
            tenant_id=self.tenant_id,
            action=self.action,
            actor_subject=caller.subject,
            approver_subject=self.approver_subject,
            authority_ref=self.authority_ref,
            reason=self.reason,
            change_reference=self.change_reference,
            idempotency_key=idempotency_key,
            request_fingerprint=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            correlation_id=event_lineage.correlation_id,
            trace_id=event_lineage.trace_id,
            requested_at_utc=self.requested_at_utc,
            dry_run=self.dry_run,
            authority_verification_required=authority_verification_required,
            authority_receipt=authority_receipt,
            archive_lifecycle_receipt=archive_lifecycle_receipt,
        )


def _producer_decision_sha256(
    decision: LifecycleAuthorityProducerDecision | ArchiveLifecycleProducerDecision | None,
) -> str | None:
    if decision is None:
        return None
    canonical = json.dumps(
        decision.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


class DataLifecycleActionResponse(CamelModel):
    repository: str = "lotus-idea"
    operation_id: str = Field(..., alias="operationId")
    decision: DataLifecycleDecision
    action: DataLifecycleAction
    state: DataLifecycleState | None
    retention_expires_at_utc: datetime | None = Field(None, alias="retentionExpiresAtUtc")
    control_version: int | None = Field(None, alias="controlVersion")
    blockers: tuple[DataLifecycleBlocker, ...]
    dry_run: bool = Field(..., alias="dryRun")
    audit_sha256: str = Field(..., alias="auditSha256")
    affected_row_counts: dict[str, int] = Field(..., alias="affectedRowCounts")
    certification_status: str = Field("not_certified", alias="certificationStatus")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        result: DataLifecycleOperationResult,
        *,
        action: DataLifecycleAction,
    ) -> DataLifecycleActionResponse:
        control = result.control
        return cls(
            operationId=result.operation_id,
            decision=result.decision,
            action=action,
            state=control.state if control is not None else None,
            retentionExpiresAtUtc=(
                control.retention_expires_at_utc if control is not None else None
            ),
            controlVersion=control.version if control is not None else None,
            blockers=result.blockers,
            dryRun=result.dry_run,
            auditSha256=result.audit_sha256,
            affectedRowCounts=dict(result.affected_row_counts),
            certificationStatus="not_certified",
            supportedFeaturePromoted=False,
        )
