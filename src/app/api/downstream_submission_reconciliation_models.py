from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.downstream_submission_reconciliation import (
    DownstreamSubmissionReconciliationResult,
    DownstreamSubmissionReconciliationSummary,
)
from app.domain import (
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    SourceSystem,
)


class DownstreamSubmissionReconciliationSummaryResponse(CamelModel):
    support_reference: str = Field(..., alias="supportReference")
    resource_type: DownstreamSubmissionResourceType = Field(..., alias="resourceType")
    target: ConversionTarget
    source_authority: SourceSystem = Field(..., alias="sourceAuthority")
    submission_posture: DownstreamSubmissionPosture = Field(..., alias="submissionPosture")
    attempt_count: int = Field(..., alias="attemptCount")
    submitted_at_utc: datetime = Field(..., alias="submittedAtUtc")
    updated_at_utc: datetime = Field(..., alias="updatedAtUtc")
    lease_expires_at_utc: datetime | None = Field(None, alias="leaseExpiresAtUtc")
    downstream_failure_reason: str | None = Field(None, alias="downstreamFailureReason")
    audit_entry_count: int = Field(..., alias="auditEntryCount")
    reconciliation_eligible: bool = Field(..., alias="reconciliationEligible")
    owner: str

    @classmethod
    def from_domain(
        cls,
        summary: DownstreamSubmissionReconciliationSummary,
    ) -> "DownstreamSubmissionReconciliationSummaryResponse":
        return cls.model_validate(summary, from_attributes=True)


class DownstreamSubmissionReconciliationListResponse(CamelModel):
    repository: str = "lotus-idea"
    items: tuple[DownstreamSubmissionReconciliationSummaryResponse, ...]
    returned_count: int = Field(..., alias="returnedCount")
    supportability_status: str = Field("not_certified", alias="supportabilityStatus")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class DownstreamSubmissionReconciliationRequest(CamelModel):
    resolution: DownstreamSubmissionResolution
    reason: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_]+$")
    change_reference: str = Field(
        ...,
        alias="changeReference",
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:/-]+$",
    )


class DownstreamSubmissionReconciliationResponse(CamelModel):
    repository: str = "lotus-idea"
    reconciliation_status: str = Field(..., alias="reconciliationStatus")
    submission: DownstreamSubmissionReconciliationSummaryResponse
    blocker: str | None = None
    supportability_status: str = Field("not_certified", alias="supportabilityStatus")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        result: DownstreamSubmissionReconciliationResult,
    ) -> "DownstreamSubmissionReconciliationResponse":
        assert result.summary is not None
        return cls(
            reconciliationStatus=result.status.value,
            submission=DownstreamSubmissionReconciliationSummaryResponse.from_domain(
                result.summary
            ),
            blocker=result.blocker,
            supportabilityStatus="not_certified",
            supportedFeaturePromoted=False,
        )
