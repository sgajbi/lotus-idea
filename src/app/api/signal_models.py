from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import Field

from app.api.access_scope_models import ReviewAccessScopeRequest as ReviewAccessScopeRequest
from app.api.base_model import CamelModel
from app.api.score_models import ScoreContributionResponse
from app.domain import (
    CausalInputRevision,
    CandidateIdentity,
    EvidenceFreshness,
    IdeaCandidate,
    SignalEvaluationResult,
    SourceReconciliationPosture,
    SourceRef,
    SourceRevisionClaims,
    SourceSystem,
)


class CausalInputRevisionModel(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_revision: str = Field(..., alias="sourceRevision")
    restatement_version: str | None = Field(default=None, alias="restatementVersion")

    def to_domain(self) -> CausalInputRevision:
        return CausalInputRevision(
            product_id=self.product_id,
            source_revision=self.source_revision,
            restatement_version=self.restatement_version,
        )

    @classmethod
    def from_domain(cls, revision: CausalInputRevision) -> Self:
        return cls(
            productId=revision.product_id,
            sourceRevision=revision.source_revision,
            restatementVersion=revision.restatement_version,
        )


class SourceRevisionClaimsModel(CamelModel):
    snapshot_id: str | None = Field(default=None, alias="snapshotId")
    source_revision: str | None = Field(default=None, alias="sourceRevision")
    restatement_version: str | None = Field(default=None, alias="restatementVersion")
    source_batch_id: str | None = Field(default=None, alias="sourceBatchId")
    source_cut_id: str | None = Field(default=None, alias="sourceCutId")
    calculation_run_id: str | None = Field(default=None, alias="calculationRunId")
    methodology_version: str | None = Field(default=None, alias="methodologyVersion")
    policy_version: str | None = Field(default=None, alias="policyVersion")
    causal_input_revisions: tuple[CausalInputRevisionModel, ...] = Field(
        default=(), alias="causalInputRevisions"
    )
    reconciliation_posture: SourceReconciliationPosture = Field(
        SourceReconciliationPosture.UNKNOWN,
        alias="reconciliationPosture",
    )

    def to_domain(self) -> SourceRevisionClaims:
        return SourceRevisionClaims(
            snapshot_id=self.snapshot_id,
            source_revision=self.source_revision,
            restatement_version=self.restatement_version,
            source_batch_id=self.source_batch_id,
            source_cut_id=self.source_cut_id,
            calculation_run_id=self.calculation_run_id,
            methodology_version=self.methodology_version,
            policy_version=self.policy_version,
            causal_input_revisions=tuple(
                revision.to_domain() for revision in self.causal_input_revisions
            ),
            reconciliation_posture=self.reconciliation_posture,
        )

    @classmethod
    def from_domain(cls, claims: SourceRevisionClaims) -> Self:
        return cls(
            snapshotId=claims.snapshot_id,
            sourceRevision=claims.source_revision,
            restatementVersion=claims.restatement_version,
            sourceBatchId=claims.source_batch_id,
            sourceCutId=claims.source_cut_id,
            calculationRunId=claims.calculation_run_id,
            methodologyVersion=claims.methodology_version,
            policyVersion=claims.policy_version,
            causalInputRevisions=tuple(
                CausalInputRevisionModel.from_domain(revision)
                for revision in claims.causal_input_revisions
            ),
            reconciliationPosture=claims.reconciliation_posture,
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
    revision_claims: SourceRevisionClaimsModel | None = Field(
        default=None,
        alias="revisionClaims",
        description=(
            "Source-owner-issued revision, restatement, calculation, methodology and "
            "reconciliation identity. Absence is retained as unknown, never inferred."
        ),
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
            revision_claims=(
                self.revision_claims.to_domain() if self.revision_claims is not None else None
            ),
        )


class SourceRefResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: date = Field(..., alias="asOfDate")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    freshness: EvidenceFreshness
    revision_claims: SourceRevisionClaimsModel | None = Field(
        default=None,
        alias="revisionClaims",
    )

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
            revisionClaims=(
                SourceRevisionClaimsModel.from_domain(source_ref.revision_claims)
                if source_ref.revision_claims is not None
                else None
            ),
        )


class CandidateIdentityResponse(CamelModel):
    business_identity_id: str = Field(..., alias="businessIdentityId")
    policy_version: str = Field(..., alias="policyVersion")
    material_fingerprint: str = Field(..., alias="materialFingerprint")
    material_version: int = Field(..., alias="materialVersion")
    evidence_version: int = Field(..., alias="evidenceVersion")
    change_reason: str = Field(..., alias="changeReason")
    supersedes_material_version: int | None = Field(
        default=None,
        alias="supersedesMaterialVersion",
    )

    @classmethod
    def from_domain(cls, identity: CandidateIdentity) -> "CandidateIdentityResponse":
        return cls(
            businessIdentityId=identity.business_identity_id,
            policyVersion=identity.policy_version,
            materialFingerprint=identity.material_fingerprint,
            materialVersion=identity.material_version,
            evidenceVersion=identity.evidence_version,
            changeReason=identity.change_reason.value,
            supersedesMaterialVersion=identity.supersedes_material_version,
        )


class IdeaCandidateSummaryResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    identity: CandidateIdentityResponse
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    supportability: str
    score: str | None = None
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    score_reason_codes: tuple[str, ...] = Field(..., alias="scoreReasonCodes")
    score_components: tuple[ScoreContributionResponse, ...] = Field(..., alias="scoreComponents")
    score_conflict_penalty_applied: str | None = Field(
        default=None,
        alias="scoreConflictPenaltyApplied",
    )
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    source_refs: tuple[SourceRefResponse, ...] = Field(..., alias="sourceRefs")
    applicability_expires_at_utc: datetime | None = Field(
        default=None,
        alias="applicabilityExpiresAtUtc",
        description=(
            "Authoritative UTC boundary after which this material opportunity is no longer "
            "reviewable; equality is expired."
        ),
    )

    @classmethod
    def from_domain(cls, candidate: IdeaCandidate) -> "IdeaCandidateSummaryResponse":
        return cls(
            candidateId=candidate.candidate_id,
            identity=CandidateIdentityResponse.from_domain(candidate.identity),
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            supportability=candidate.evidence_packet.supportability.value,
            score=str(candidate.score.score) if candidate.score is not None else None,
            scorePolicyVersion=candidate.score.policy_version
            if candidate.score is not None
            else None,
            scoreReasonCodes=(
                tuple(reason.value for reason in candidate.score.reason_codes)
                if candidate.score is not None
                else ()
            ),
            scoreComponents=(
                tuple(
                    ScoreContributionResponse.from_domain(item)
                    for item in candidate.score.contributions
                )
                if candidate.score is not None
                else ()
            ),
            scoreConflictPenaltyApplied=(
                str(candidate.score.conflict_penalty_applied)
                if candidate.score is not None
                else None
            ),
            sourceSignalIds=candidate.source_signal_ids,
            sourceRefs=tuple(
                SourceRefResponse.from_domain(source_ref)
                for source_ref in candidate.evidence_packet.source_refs
            ),
            applicabilityExpiresAtUtc=(candidate.evidence_packet.applicability_expires_at_utc),
        )


class SignalEvaluationResponse(CamelModel):
    outcome: str
    family: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    candidate: IdeaCandidateSummaryResponse | None
    source_authority: str = Field(..., alias="sourceAuthority")
    supported_feature_promoted: bool = Field(
        False,
        alias="supportedFeaturePromoted",
        description=(
            "False until live source, Gateway/Workbench, data-mesh, and "
            "supported-feature proof exists."
        ),
    )

    @classmethod
    def from_domain(
        cls,
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> Self:
        return cls(
            outcome=result.outcome.value,
            family=result.family.value,
            reasonCodes=tuple(reason.value for reason in result.reason_codes),
            unsupportedReasons=tuple(reason.value for reason in result.unsupported_reasons),
            candidate=(
                IdeaCandidateSummaryResponse.from_domain(result.candidate)
                if result.candidate is not None
                else None
            ),
            sourceAuthority=source_authority,
            supportedFeaturePromoted=False,
        )
