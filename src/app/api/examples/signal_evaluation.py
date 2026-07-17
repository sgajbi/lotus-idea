from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, TypeVar

from app.api.signal_models import SignalEvaluationResponse, SourceRefRequest
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceUnavailable,
)


ResponseT = TypeVar("ResponseT", bound=SignalEvaluationResponse)
EvidenceT = TypeVar("EvidenceT")


def serialize_signal_evaluation(
    result: SignalEvaluationResult,
    *,
    response_model: type[ResponseT],
    source_authority: SourceSystem,
) -> dict[str, Any]:
    return response_model.from_domain(
        result,
        source_authority=source_authority.value,
    ).model_dump(mode="json", by_alias=True)


def build_source_ref_request(
    product_id: str,
    *,
    source_system: SourceSystem,
    as_of_date: date,
    generated_at_utc: datetime,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    data_quality_status: str = "complete",
) -> SourceRefRequest:
    return SourceRefRequest(
        productId=product_id,
        sourceSystem=source_system,
        productVersion="v1",
        route=f"/source/{product_id}",
        asOfDate=as_of_date,
        generatedAtUtc=generated_at_utc,
        contentHash=f"sha256:{product_id}",
        dataQualityStatus=data_quality_status,
        freshness=freshness,
    )


def build_core_source_ref_request(
    product_id: str,
    *,
    as_of_date: date,
    generated_at_utc: datetime,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRefRequest:
    return build_source_ref_request(
        product_id,
        source_system=SourceSystem.LOTUS_CORE,
        as_of_date=as_of_date,
        generated_at_utc=generated_at_utc,
        freshness=freshness,
    )


def return_or_raise_example_evidence(
    evidence: EvidenceT,
    error: Exception | None,
) -> EvidenceT:
    if error is not None:
        raise error
    return evidence


@dataclass(frozen=True)
class ExampleAdvisePolicyEvaluationSource(AdviseOpportunitySourcePort):
    """Deterministic Advise-port fake for source-backed OpenAPI examples."""

    evidence: AdvisePolicyEvaluationEvidence
    error: AdviseSourceUnavailable | None = None

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "build_core_source_ref_request",
    "build_source_ref_request",
    "ExampleAdvisePolicyEvaluationSource",
    "return_or_raise_example_evidence",
    "serialize_signal_evaluation",
]
