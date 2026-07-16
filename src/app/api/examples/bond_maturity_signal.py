from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.api.bond_maturity_signals import (
    EvaluateBondMaturitySignalRequest,
    EvaluateBondMaturitySignalResponse,
)
from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_source_ref_request,
    serialize_signal_evaluation,
)
from app.api.signal_models import SourceRefRequest
from app.application.bond_maturity_signal import (
    EvaluateBondMaturityFromCoreCommand,
    evaluate_bond_maturity_signal_command,
    evaluate_bond_maturity_signal_from_core,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
    CoreSourceUnavailable,
)


BOND_MATURITY_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/bond-maturity/evaluate"
BOND_MATURITY_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/bond-maturity/evaluate-from-source"
)
BOND_MATURITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "An upcoming bond maturity creates an advisor-review candidate",
    "blocked": "Stale, denied, incomplete, or unavailable Core evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "No maturity inside the review window creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_CORE
_TENANT_ID = "tenant-a"
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
_QUALIFYING_MATURITY_DATE = date(2026, 7, 10)
_NON_QUALIFYING_MATURITY_DATE = date(2026, 8, 15)


def build_bond_maturity_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(
            next_maturity_date=_QUALIFYING_MATURITY_DATE,
        ),
        "blocked": _caller_evaluation_response(
            next_maturity_date=_QUALIFYING_MATURITY_DATE,
            freshness=EvidenceFreshness.STALE,
        ),
        "suppressed": _caller_evaluation_response(
            next_maturity_date=_QUALIFYING_MATURITY_DATE,
            duplicate_of_candidate_id="idea_bond_maturity_existing",
        ),
        "notEligible": _caller_evaluation_response(
            next_maturity_date=_NON_QUALIFYING_MATURITY_DATE,
        ),
    }


def build_source_backed_bond_maturity_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _source_evaluation_response(
            next_maturity_date=_QUALIFYING_MATURITY_DATE,
        ),
        "blocked": _source_evaluation_response(source_error=CoreSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            next_maturity_date=_QUALIFYING_MATURITY_DATE,
            duplicate_of_candidate_id="idea_bond_maturity_existing",
        ),
        "notEligible": _source_evaluation_response(
            next_maturity_date=_NON_QUALIFYING_MATURITY_DATE,
        ),
    }


def apply_bond_maturity_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            BOND_MATURITY_EVALUATE_OPERATION_PATH,
            build_bond_maturity_evaluation_response_examples(),
        ),
        (
            BOND_MATURITY_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_bond_maturity_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                BOND_MATURITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    next_maturity_date: date,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateBondMaturitySignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedNextMaturityDate=next_maturity_date,
        sourceReportedMaturingPositionCount=2,
        holdingsRef=_source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        maturityFactRef=_source_ref(
            "lotus-core:PortfolioMaturitySummary:v1",
            freshness=freshness,
        ),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_bond_maturity_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    next_maturity_date: date = _QUALIFYING_MATURITY_DATE,
    duplicate_of_candidate_id: str | None = None,
    source_error: CoreSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_bond_maturity_signal_from_core(
        EvaluateBondMaturityFromCoreCommand(
            portfolio_id=_PORTFOLIO_ID,
            tenant_id=_TENANT_ID,
            as_of_date=_AS_OF_DATE,
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        core_source=_ExampleCoreBondMaturitySource(
            evidence=_core_evidence(next_maturity_date),
            error=source_error,
        ),
    )
    return _serialized(result)


def _core_evidence(next_maturity_date: date) -> CoreBondMaturityEvidence:
    return CoreBondMaturityEvidence(
        source_reported_next_maturity_date=next_maturity_date,
        source_reported_maturing_position_count=2,
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1").to_domain(),
        maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1").to_domain(),
        maturity_diagnostic="example_not_exposed",
    )


def _source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRefRequest:
    return build_source_ref_request(
        product_id,
        source_system=_SOURCE_AUTHORITY,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateBondMaturitySignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleCoreBondMaturitySource(CoreBondMaturitySourcePort):
    evidence: CoreBondMaturityEvidence
    error: CoreSourceUnavailable | None = None

    def fetch_bond_maturity_evidence(
        self,
        request: CoreBondMaturityEvidenceRequest,
    ) -> CoreBondMaturityEvidence:
        del request
        if self.error is not None:
            raise self.error
        return self.evidence


__all__ = [
    "BOND_MATURITY_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "BOND_MATURITY_EVALUATE_OPERATION_PATH",
    "BOND_MATURITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_bond_maturity_signal_openapi_examples",
    "build_bond_maturity_evaluation_response_examples",
    "build_source_backed_bond_maturity_evaluation_response_examples",
]
