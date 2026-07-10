from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.outbox_recovery import OutboxRecoveryRunSummary
from app.domain import OutboxDeadLetterSummary


class OutboxDeadLetterSummaryResponse(CamelModel):
    support_reference: str = Field(..., alias="supportReference")
    event_family: str = Field(..., alias="eventFamily")
    schema_version: str = Field(..., alias="schemaVersion")
    retry_count: int = Field(..., alias="retryCount")
    first_failed_at_utc: datetime = Field(..., alias="firstFailedAtUtc")
    last_failed_at_utc: datetime = Field(..., alias="lastFailedAtUtc")
    failure_reason: str = Field(..., alias="failureReason")
    recovery_eligible: bool = Field(..., alias="recoveryEligible")
    recovery_blocker: str | None = Field(None, alias="recoveryBlocker")
    disposition: str
    owner: str

    @classmethod
    def from_domain(cls, summary: OutboxDeadLetterSummary) -> OutboxDeadLetterSummaryResponse:
        return cls(
            supportReference=summary.support_reference,
            eventFamily=summary.event_family,
            schemaVersion=summary.schema_version,
            retryCount=summary.retry_count,
            firstFailedAtUtc=summary.first_failed_at_utc,
            lastFailedAtUtc=summary.last_failed_at_utc,
            failureReason=summary.failure_reason,
            recoveryEligible=summary.recovery_eligible,
            recoveryBlocker=summary.recovery_blocker,
            disposition=summary.disposition,
            owner=summary.owner,
        )


class OutboxDeadLetterListResponse(CamelModel):
    repository: str = "lotus-idea"
    supportability_status: str = Field("not_certified", alias="supportabilityStatus")
    items: tuple[OutboxDeadLetterSummaryResponse, ...]
    returned_count: int = Field(..., alias="returnedCount")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class OutboxRecoveryRequest(CamelModel):
    reason: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_]+$")
    change_reference: str = Field(
        ...,
        alias="changeReference",
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:/-]+$",
    )


class OutboxRecoveryResponse(CamelModel):
    repository: str = "lotus-idea"
    support_reference: str = Field(..., alias="supportReference")
    run_status: str = Field(..., alias="runStatus")
    recovery_reference: str | None = Field(None, alias="recoveryReference")
    blocker: str | None = None
    publication_attempted: bool = Field(..., alias="publicationAttempted")
    original_retry_count: int | None = Field(None, alias="originalRetryCount")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(cls, summary: OutboxRecoveryRunSummary) -> OutboxRecoveryResponse:
        return cls(
            supportReference=summary.support_reference,
            runStatus=summary.run_status.value,
            recoveryReference=summary.recovery_reference,
            blocker=summary.blocker,
            publicationAttempted=summary.publication_attempted,
            originalRetryCount=summary.original_retry_count,
            supportabilityStatus=summary.supportability_status,
            supportedFeaturePromoted=summary.supported_feature_promoted,
        )


__all__ = [
    "OutboxDeadLetterListResponse",
    "OutboxDeadLetterSummaryResponse",
    "OutboxRecoveryRequest",
    "OutboxRecoveryResponse",
]
