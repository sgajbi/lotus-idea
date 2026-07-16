from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_source_ref_request,
    serialize_signal_evaluation,
)
from app.api.idea_signal_models import (
    CandidatePersistenceSummaryResponse,
    EvaluateAndPersistHighCashSignalResponse,
    EvaluateHighCashSignalRequest,
    EvaluateHighCashSignalResponse,
    HighCashEvidenceRequest,
)
from app.api.signal_models import SourceRefRequest
from app.application.high_cash_signal import (
    EvaluateAndPersistHighCashSignalCommand,
    EvaluateHighCashFromCoreCommand,
    HighCashSignalPersistenceResult,
    evaluate_and_persist_high_cash_signal,
    evaluate_high_cash_signal_command,
    evaluate_high_cash_signal_from_core,
)
from app.domain import (
    EvidenceFreshness,
    InMemoryIdeaRepository,
    SignalEvaluationResult,
    SourceSystem,
)
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
)


HIGH_CASH_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/high-cash/evaluate"
HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/high-cash/evaluate-from-source"
)
HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION_PATH = (
    "/api/v1/idea-signals/high-cash/evaluate-and-persist"
)
HIGH_CASH_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "High-cash evidence creates a reviewable idea candidate",
    "blocked": "Incomplete or untrusted evidence blocks candidate creation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Cash weight below policy materiality creates no candidate",
}
HIGH_CASH_PERSISTENCE_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New high-cash candidate accepted and persisted",
    "replayed": "Matching idempotent request replayed without duplicate mutation",
    "duplicateCandidate": "New retry key resolves to the already persisted candidate",
    "blocked": "Blocked evaluation skips candidate persistence",
    "suppressed": "Suppressed duplicate evaluation skips candidate persistence",
    "notEligible": "Below-materiality evaluation skips candidate persistence",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_CORE.value
_TENANT_ID = "tenant-a"
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_high_cash_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(cash_weight=Decimal("0.18")),
        "blocked": _caller_evaluation_response(
            cash_weight=Decimal("0.18"),
            freshness=EvidenceFreshness.STALE,
        ),
        "suppressed": _caller_evaluation_response(
            cash_weight=Decimal("0.18"),
            duplicate_of_candidate_id="idea_high_cash_existing",
        ),
        "notEligible": _caller_evaluation_response(cash_weight=Decimal("0.05")),
    }


def build_source_backed_high_cash_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _source_evaluation_response(cash_weight=Decimal("0.18")),
        "blocked": _source_evaluation_response(
            cash_weight=Decimal("0.18"),
            freshness=EvidenceFreshness.STALE,
        ),
        "suppressed": _source_evaluation_response(
            cash_weight=Decimal("0.18"),
            duplicate_of_candidate_id="idea_high_cash_existing",
        ),
        "notEligible": _source_evaluation_response(cash_weight=Decimal("0.05")),
    }


def build_high_cash_persistence_response_examples() -> dict[str, dict[str, Any]]:
    repository = InMemoryIdeaRepository()
    accepted_command = _persistence_command(
        idempotency_key="high-cash-example-accepted",
        cash_weight=Decimal("0.18"),
    )
    accepted = evaluate_and_persist_high_cash_signal(
        accepted_command,
        repository=repository,
    )
    replayed = evaluate_and_persist_high_cash_signal(
        accepted_command,
        repository=repository,
    )
    duplicate = evaluate_and_persist_high_cash_signal(
        _persistence_command(
            idempotency_key="high-cash-example-duplicate-candidate",
            cash_weight=Decimal("0.18"),
        ),
        repository=repository,
    )

    return {
        "accepted": _persistence_response(accepted),
        "replayed": _persistence_response(replayed),
        "duplicateCandidate": _persistence_response(duplicate),
        "blocked": _persistence_response(
            evaluate_and_persist_high_cash_signal(
                _persistence_command(
                    idempotency_key="high-cash-example-blocked",
                    cash_weight=None,
                ),
                repository=repository,
            )
        ),
        "suppressed": _persistence_response(
            evaluate_and_persist_high_cash_signal(
                _persistence_command(
                    idempotency_key="high-cash-example-suppressed",
                    cash_weight=Decimal("0.18"),
                    duplicate_of_candidate_id="idea_high_cash_existing",
                ),
                repository=repository,
            )
        ),
        "notEligible": _persistence_response(
            evaluate_and_persist_high_cash_signal(
                _persistence_command(
                    idempotency_key="high-cash-example-not-eligible",
                    cash_weight=Decimal("0.05"),
                ),
                repository=repository,
            )
        ),
    }


def apply_high_cash_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples, summaries in (
        (
            HIGH_CASH_EVALUATE_OPERATION_PATH,
            build_high_cash_evaluation_response_examples(),
            HIGH_CASH_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
        ),
        (
            HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_high_cash_evaluation_response_examples(),
            HIGH_CASH_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
        ),
        (
            HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION_PATH,
            build_high_cash_persistence_response_examples(),
            HIGH_CASH_PERSISTENCE_SUCCESS_EXAMPLE_SUMMARIES,
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(examples, summaries),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    cash_weight: Decimal | None,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = _evaluation_request(
        cash_weight=cash_weight,
        freshness=freshness,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )
    result = evaluate_high_cash_signal_command(request.to_command())
    return _serialized_evaluation(result)


def _source_evaluation_response(
    *,
    cash_weight: Decimal,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    result = evaluate_high_cash_signal_from_core(
        EvaluateHighCashFromCoreCommand(
            portfolio_id=_PORTFOLIO_ID,
            tenant_id=_TENANT_ID,
            as_of_date=_AS_OF_DATE,
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        core_source=_ExampleCoreSource(
            evidence=_core_evidence(cash_weight=cash_weight, freshness=freshness)
        ),
    )
    return _serialized_evaluation(result)


def _persistence_command(
    *,
    idempotency_key: str,
    cash_weight: Decimal | None,
    duplicate_of_candidate_id: str | None = None,
) -> EvaluateAndPersistHighCashSignalCommand:
    return EvaluateAndPersistHighCashSignalCommand(
        evaluation=_evaluation_request(
            cash_weight=cash_weight,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ).to_command(),
        idempotency_key=idempotency_key,
        actor_subject="signal-ingestion-worker",
    )


def _persistence_response(result: HighCashSignalPersistenceResult) -> dict[str, Any]:
    response = EvaluateAndPersistHighCashSignalResponse(
        evaluation=EvaluateHighCashSignalResponse.from_domain(
            result.evaluation,
            source_authority=_SOURCE_AUTHORITY,
        ),
        persistence=(
            CandidatePersistenceSummaryResponse.from_record(
                decision=result.persistence.decision,
                record=result.persistence.record,
            )
            if result.persistence is not None
            else None
        ),
        durableStorageBacked=False,
        supportedFeaturePromoted=False,
    )
    return response.model_dump(mode="json", by_alias=True)


def _serialized_evaluation(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateHighCashSignalResponse,
        source_authority=SourceSystem.LOTUS_CORE,
    )


def _evaluation_request(
    *,
    cash_weight: Decimal | None,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> EvaluateHighCashSignalRequest:
    return EvaluateHighCashSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedCashWeight=cash_weight,
        sourceEvidence=HighCashEvidenceRequest(
            portfolioStateRef=_source_ref_request(
                "lotus-core:PortfolioStateSnapshot:v1",
                freshness=freshness,
            ),
            holdingsRef=_source_ref_request(
                "lotus-core:HoldingsAsOf:v1",
                freshness=freshness,
            ),
            cashMovementRef=_source_ref_request(
                "lotus-core:PortfolioCashMovementSummary:v1",
                freshness=freshness,
            ),
            cashflowProjectionRef=_source_ref_request(
                "lotus-core:PortfolioCashflowProjection:v1",
                freshness=freshness,
            ),
        ),
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )


def _core_evidence(
    *,
    cash_weight: Decimal,
    freshness: EvidenceFreshness,
) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=_source_ref_request(
            "lotus-core:PortfolioStateSnapshot:v1",
            freshness=freshness,
        ).to_domain(),
        holdings_ref=_source_ref_request(
            "lotus-core:HoldingsAsOf:v1",
            freshness=freshness,
        ).to_domain(),
        cash_movement_ref=_source_ref_request(
            "lotus-core:PortfolioCashMovementSummary:v1",
            freshness=freshness,
        ).to_domain(),
        cashflow_projection_ref=_source_ref_request(
            "lotus-core:PortfolioCashflowProjection:v1",
            freshness=freshness,
        ).to_domain(),
    )


def _source_ref_request(
    product_id: str,
    *,
    freshness: EvidenceFreshness,
) -> SourceRefRequest:
    return build_source_ref_request(
        product_id,
        source_system=SourceSystem.LOTUS_CORE,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
    )


@dataclass(frozen=True)
class _ExampleCoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence

    def fetch_high_cash_evidence(
        self,
        request: CoreHighCashEvidenceRequest,
    ) -> CoreHighCashEvidence:
        del request
        return self.evidence


__all__ = [
    "HIGH_CASH_EVALUATE_AND_PERSIST_OPERATION_PATH",
    "HIGH_CASH_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "HIGH_CASH_EVALUATE_OPERATION_PATH",
    "HIGH_CASH_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "HIGH_CASH_PERSISTENCE_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_high_cash_signal_openapi_examples",
    "build_high_cash_evaluation_response_examples",
    "build_high_cash_persistence_response_examples",
    "build_source_backed_high_cash_evaluation_response_examples",
]
