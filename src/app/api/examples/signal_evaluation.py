from __future__ import annotations

from datetime import date, datetime
from typing import Any, TypeVar

from app.api.signal_models import SignalEvaluationResponse, SourceRefRequest
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem


ResponseT = TypeVar("ResponseT", bound=SignalEvaluationResponse)


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
) -> SourceRefRequest:
    return SourceRefRequest(
        productId=product_id,
        sourceSystem=source_system,
        productVersion="v1",
        route=f"/source/{product_id}",
        asOfDate=as_of_date,
        generatedAtUtc=generated_at_utc,
        contentHash=f"sha256:{product_id}",
        dataQualityStatus="complete",
        freshness=freshness,
    )


__all__ = [
    "build_source_ref_request",
    "serialize_signal_evaluation",
]
