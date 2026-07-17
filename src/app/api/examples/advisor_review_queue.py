from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.review_queue_models import BusinessReviewQueueResponse
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashSignalCommand,
    evaluate_and_persist_high_cash_signal,
)
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    build_review_queue_from_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    SourceRef,
    SourceSystem,
)
from app.domain.access_scope import ReviewAccessScope


ADVISOR_REVIEW_QUEUE_OPERATION_PATH = "/api/v1/review-queues/advisor"
ADVISOR_REVIEW_QUEUE_SUCCESS_EXAMPLE_SUMMARIES = {
    "itemsAvailable": "Eligible Idea candidates are returned in deterministic advisor rank order",
    "noItemsAvailable": "No eligible Idea candidates are available for the bounded advisor scope",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_ACCESS_SCOPE = ReviewAccessScope(
    tenant_id="tenant-private-bank-sg",
    book_id="book-advisor-001",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-001",
)


def build_advisor_review_queue_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "itemsAvailable": _queue_response(include_eligible_candidate=True),
        "noItemsAvailable": _queue_response(include_eligible_candidate=False),
    }


def apply_advisor_review_queue_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    examples = build_advisor_review_queue_response_examples()
    apply_named_response_examples(
        openapi_schema,
        operation_path=ADVISOR_REVIEW_QUEUE_OPERATION_PATH,
        operation_method="get",
        examples=build_named_openapi_examples(
            examples,
            ADVISOR_REVIEW_QUEUE_SUCCESS_EXAMPLE_SUMMARIES,
        ),
    )
    return openapi_schema


def _queue_response(*, include_eligible_candidate: bool) -> dict[str, Any]:
    repository = InMemoryIdeaRepository()
    if include_eligible_candidate:
        _persist_eligible_high_cash_candidate(repository)

    queue = build_review_queue_from_repository(
        BuildReviewQueueFromRepositoryCommand(
            evaluated_at_utc=_EVALUATED_AT,
        ),
        repository=repository,
    )
    return BusinessReviewQueueResponse.from_domain(queue).model_dump(
        mode="json",
        by_alias=True,
    )


def _persist_eligible_high_cash_candidate(repository: InMemoryIdeaRepository) -> None:
    result = evaluate_and_persist_high_cash_signal(
        EvaluateAndPersistHighCashSignalCommand(
            evaluation=EvaluateHighCashSignalCommand(
                as_of_date=_AS_OF_DATE,
                source_reported_cash_weight=Decimal("0.18"),
                portfolio_state_ref=_source_ref("PortfolioStateSnapshot"),
                holdings_ref=_source_ref("HoldingsAsOf"),
                cash_movement_ref=_source_ref("PortfolioCashMovementSummary"),
                cashflow_projection_ref=_source_ref("PortfolioCashflowProjection"),
                evaluated_at_utc=_EVALUATED_AT,
                access_scope=_ACCESS_SCOPE,
            ),
            idempotency_key="openapi-example:advisor-review-queue:items-available",
            actor_subject="openapi-example-generator",
        ),
        repository=repository,
    )
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED


def _source_ref(name: str) -> SourceRef:
    return SourceRef(
        product_id=f"lotus-core:{name}:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{name}",
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        content_hash=f"sha256:advisor-review-queue-{name.lower()}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


__all__ = [
    "ADVISOR_REVIEW_QUEUE_OPERATION_PATH",
    "ADVISOR_REVIEW_QUEUE_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_advisor_review_queue_openapi_examples",
    "build_advisor_review_queue_response_examples",
]
