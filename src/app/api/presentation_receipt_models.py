from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.temporal_validation import require_utc_datetime
from app.domain import (
    AcceptanceTimeSource,
    MAX_PRESENTED_CANDIDATE_COUNT,
    CandidatePresentationReceipt,
    PresentationReceiptResult,
)


_GOVERNED_REFERENCE = r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$"
_SHA256_DIGEST = r"^sha256:[0-9a-f]{64}$"


class PresentationReceiptRequest(CamelModel):
    tenant_id: str = Field(..., alias="tenantId", pattern=_GOVERNED_REFERENCE)
    presented_at_utc: datetime = Field(..., alias="presentedAtUtc")
    rank_at_presentation: int = Field(..., alias="rankAtPresentation", ge=1, strict=True)
    visible_candidate_count: int = Field(
        ...,
        alias="visibleCandidateCount",
        ge=1,
        le=MAX_PRESENTED_CANDIDATE_COUNT,
        strict=True,
    )
    queue_snapshot_digest: str = Field(..., alias="queueSnapshotDigest", pattern=_SHA256_DIGEST)
    queue_policy_version: str = Field(
        ...,
        alias="queuePolicyVersion",
        pattern=_GOVERNED_REFERENCE,
    )
    ranking_policy_version: str = Field(
        ...,
        alias="rankingPolicyVersion",
        pattern=_GOVERNED_REFERENCE,
    )
    candidate_material_version: int = Field(
        ...,
        alias="candidateMaterialVersion",
        ge=1,
        strict=True,
    )
    candidate_evidence_version: int = Field(
        ...,
        alias="candidateEvidenceVersion",
        ge=1,
        strict=True,
    )

    @field_validator("presented_at_utc")
    @classmethod
    def _presented_at_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc_datetime(value, field_name="presentedAtUtc")

    def to_domain(
        self,
        *,
        candidate_id: str,
        receipt_id: str,
        accepted_at_utc: datetime,
    ) -> CandidatePresentationReceipt:
        return CandidatePresentationReceipt(
            receipt_id=receipt_id,
            candidate_id=candidate_id,
            tenant_id=self.tenant_id,
            presented_at_utc=self.presented_at_utc,
            rank_at_presentation=self.rank_at_presentation,
            visible_candidate_count=self.visible_candidate_count,
            queue_snapshot_digest=self.queue_snapshot_digest,
            queue_policy_version=self.queue_policy_version,
            ranking_policy_version=self.ranking_policy_version,
            candidate_material_version=self.candidate_material_version,
            candidate_evidence_version=self.candidate_evidence_version,
            accepted_at_utc=accepted_at_utc,
        )


class PresentationReceiptEvidenceResponse(CamelModel):
    receipt_id: str = Field(..., alias="receiptId")
    candidate_id: str = Field(..., alias="candidateId")
    tenant_id: str = Field(..., alias="tenantId")
    presented_at_utc: datetime = Field(..., alias="presentedAtUtc")
    accepted_at_utc: datetime = Field(..., alias="acceptedAtUtc")
    acceptance_time_source: AcceptanceTimeSource = Field(..., alias="acceptanceTimeSource")
    rank_at_presentation: int = Field(..., alias="rankAtPresentation")
    visible_candidate_count: int = Field(..., alias="visibleCandidateCount")
    queue_snapshot_digest: str = Field(..., alias="queueSnapshotDigest")
    queue_policy_version: str = Field(..., alias="queuePolicyVersion")
    ranking_policy_version: str = Field(..., alias="rankingPolicyVersion")
    candidate_material_version: int = Field(..., alias="candidateMaterialVersion")
    candidate_evidence_version: int = Field(..., alias="candidateEvidenceVersion")
    schema_version: str = Field(..., alias="schemaVersion")
    surface: str
    producer: str

    @classmethod
    def from_domain(
        cls,
        receipt: CandidatePresentationReceipt,
    ) -> PresentationReceiptEvidenceResponse:
        return cls.model_validate(receipt, from_attributes=True)


class PresentationReceiptResponse(CamelModel):
    receipt: PresentationReceiptEvidenceResponse
    persistence_decision: str = Field(..., alias="persistenceDecision")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    effectiveness_measurement_status: str = Field(..., alias="effectivenessMeasurementStatus")
    certification_status: str = Field(..., alias="certificationStatus")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_result(
        cls,
        result: PresentationReceiptResult,
        *,
        durable_storage_backed: bool,
    ) -> PresentationReceiptResponse:
        if result.receipt is None:
            raise ValueError("presentation receipt result is missing receipt evidence")
        return cls(
            receipt=PresentationReceiptEvidenceResponse.from_domain(result.receipt),
            persistenceDecision=result.decision.value,
            durableStorageBacked=durable_storage_backed,
            effectivenessMeasurementStatus="stored_consumer_certification_pending",
            certificationStatus="not_certified",
            certificationBlockers=(
                "gateway_presentation_receipt_pass_through_not_certified",
                "workbench_visible_render_producer_not_certified",
            ),
            supportedFeaturePromoted=False,
        )


__all__ = [
    "PresentationReceiptEvidenceResponse",
    "PresentationReceiptRequest",
    "PresentationReceiptResponse",
]
