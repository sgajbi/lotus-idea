from __future__ import annotations

from datetime import date, datetime

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.domain import EvidenceFreshness, IdeaCandidate, SourceRef, SourceSystem
from app.domain.access_scope import ReviewAccessScope


class ReviewAccessScopeRequest(CamelModel):
    tenant_id: str = Field(..., alias="tenantId")
    book_id: str = Field(..., alias="bookId")
    portfolio_id: str = Field(..., alias="portfolioId")
    client_id: str = Field(..., alias="clientId")

    @field_validator("tenant_id", "book_id", "portfolio_id", "client_id")
    @classmethod
    def _scope_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scope fields cannot be blank")
        return value

    def to_domain(self) -> ReviewAccessScope:
        return ReviewAccessScope(
            tenant_id=self.tenant_id,
            book_id=self.book_id,
            portfolio_id=self.portfolio_id,
            client_id=self.client_id,
        )


class SourceRefRequest(CamelModel):
    product_id: str = Field(
        ...,
        alias="productId",
        description="Governed source data-product identity.",
        examples=["lotus-core:PortfolioStateSnapshot:v1"],
    )
    source_system: SourceSystem = Field(
        ...,
        alias="sourceSystem",
        description="Source-owning Lotus service.",
        examples=[SourceSystem.LOTUS_CORE],
    )
    product_version: str = Field(
        ...,
        alias="productVersion",
        description="Source data-product version.",
        examples=["v1"],
    )
    route: str = Field(
        ...,
        description="Source-owned API or data-product route used to obtain the evidence.",
        examples=["/integration/portfolios/{portfolioRef}/core-snapshot"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date represented by the source evidence.",
        examples=["2026-06-21"],
    )
    generated_at_utc: datetime = Field(
        ...,
        alias="generatedAtUtc",
        description="UTC time when the source evidence was generated.",
        examples=["2026-06-21T10:00:00Z"],
    )
    content_hash: str = Field(
        ...,
        alias="contentHash",
        description="Source-owned content hash or lineage hash.",
        examples=["sha256:portfolio-state-snapshot-demo"],
    )
    data_quality_status: str = Field(
        ...,
        alias="dataQualityStatus",
        description="Source-owned data-quality posture.",
        examples=["complete"],
    )
    freshness: EvidenceFreshness = Field(
        ..., description="Freshness posture reported for the source evidence."
    )

    def to_domain(self) -> SourceRef:
        return SourceRef(
            product_id=self.product_id,
            source_system=self.source_system,
            product_version=self.product_version,
            route=self.route,
            as_of_date=self.as_of_date,
            generated_at_utc=self.generated_at_utc,
            content_hash=self.content_hash,
            data_quality_status=self.data_quality_status,
            freshness=self.freshness,
        )


class SourceRefResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: date = Field(..., alias="asOfDate")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    freshness: EvidenceFreshness

    @classmethod
    def from_domain(cls, source_ref: SourceRef) -> "SourceRefResponse":
        return cls(
            productId=source_ref.product_id,
            sourceSystem=source_ref.source_system,
            productVersion=source_ref.product_version,
            asOfDate=source_ref.as_of_date,
            generatedAtUtc=source_ref.generated_at_utc,
            dataQualityStatus=source_ref.data_quality_status,
            freshness=source_ref.freshness,
        )


class IdeaCandidateSummaryResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    supportability: str
    score: str | None = None
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    source_refs: tuple[SourceRefResponse, ...] = Field(..., alias="sourceRefs")

    @classmethod
    def from_domain(cls, candidate: IdeaCandidate) -> "IdeaCandidateSummaryResponse":
        return cls(
            candidateId=candidate.candidate_id,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            supportability=candidate.evidence_packet.supportability.value,
            score=str(candidate.score.score) if candidate.score is not None else None,
            scorePolicyVersion=candidate.score.policy_version
            if candidate.score is not None
            else None,
            sourceSignalIds=candidate.source_signal_ids,
            sourceRefs=tuple(
                SourceRefResponse.from_domain(source_ref)
                for source_ref in candidate.evidence_packet.source_refs
            ),
        )
