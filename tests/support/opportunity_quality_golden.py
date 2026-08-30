from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from app.domain import (
    ConcentrationRiskSignalInput,
    ConcentrationRiskSignalPolicy,
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    MandateHealthSignalInput,
    MandateHealthSignalPolicy,
    ReviewQueueAudience,
    SourceRef,
    SourceSystem,
    UnderperformanceSignalInput,
    UnderperformanceSignalPolicy,
    build_review_queue,
    evaluate_concentration_risk_signal,
    evaluate_high_cash_signal,
    evaluate_mandate_health_signal,
    evaluate_underperformance_signal,
)
from app.domain.signal_evaluation_models import SignalEvaluationResult


GOLDEN_SET_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "opportunity_quality"
    / "opportunity-quality-golden-set.v1.json"
)
EXPECTED_SCHEMA_VERSION = "lotus-idea-opportunity-quality-golden-set.v1"
REQUIRED_FAMILIES = {"high_cash", "concentration", "underperformance", "allocation_drift"}


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> dict[str, Any]:
    parsed: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("golden set must be a JSON object")
    return cast(dict[str, Any], parsed)


def evaluate_golden_set(golden_set: dict[str, Any]) -> tuple[str, ...]:
    errors = list(_validate_contract(golden_set))
    if errors:
        return tuple(errors)

    context = golden_set["evaluationContext"]
    as_of_date = date.fromisoformat(context["asOfDate"])
    evaluated_at = datetime.fromisoformat(context["evaluatedAtUtc"].replace("Z", "+00:00"))
    results: dict[str, SignalEvaluationResult] = {}
    cases_by_portfolio: dict[str, list[tuple[str, SignalEvaluationResult]]] = {}

    for case in golden_set["cases"]:
        result = _evaluate_case(case, as_of_date=as_of_date, evaluated_at=evaluated_at)
        results[case["caseId"]] = result
        cases_by_portfolio.setdefault(case["portfolio"], []).append((case["caseId"], result))
        errors.extend(_compare_case(case, result))

    for expectation in golden_set["queueExpectations"]:
        candidates = tuple(
            result.candidate
            for _, result in cases_by_portfolio.get(expectation["portfolio"], [])
            if result.candidate is not None
        )
        queue = build_review_queue(
            candidates,
            audience=ReviewQueueAudience(expectation["audience"]),
            evaluated_at_utc=evaluated_at,
        )
        case_id_by_candidate_id = {
            result.candidate.candidate_id: case_id
            for case_id, result in cases_by_portfolio.get(expectation["portfolio"], [])
            if result.candidate is not None
        }
        actual_case_ids = [case_id_by_candidate_id[item.candidate.candidate_id] for item in queue.items]
        actual_buckets = [item.priority_bucket.value for item in queue.items]
        queue_name = f"{expectation['portfolio']}:{expectation['audience']}"
        if actual_case_ids != expectation["orderedCaseIds"]:
            errors.append(
                f"{queue_name} orderedCaseIds expected {expectation['orderedCaseIds']!r}, "
                f"got {actual_case_ids!r}"
            )
        if actual_buckets != expectation["priorityBuckets"]:
            errors.append(
                f"{queue_name} priorityBuckets expected {expectation['priorityBuckets']!r}, "
                f"got {actual_buckets!r}"
            )

    return tuple(errors)


def _validate_contract(golden_set: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if golden_set.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {EXPECTED_SCHEMA_VERSION!r}")
    authorship = golden_set.get("authorship", {})
    if authorship.get("method") != "independently_authored":
        errors.append("authorship.method must be 'independently_authored'")
    if authorship.get("expectedResultsDerivedFromProductionCode") is not False:
        errors.append("expected results must not be derived from production code")
    if authorship.get("classification") != "synthetic_non_client_data":
        errors.append("golden-set data must be classified as synthetic_non_client_data")

    cases = golden_set.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return tuple(errors)
    case_ids = [case.get("caseId") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("caseId values must be unique")
    families = {case.get("family") for case in cases}
    if families != REQUIRED_FAMILIES:
        errors.append(f"families must be exactly {sorted(REQUIRED_FAMILIES)!r}")
    return tuple(errors)


def _evaluate_case(
    case: dict[str, Any],
    *,
    as_of_date: date,
    evaluated_at: datetime,
) -> SignalEvaluationResult:
    facts = case["facts"]
    family = case["family"]
    freshness = EvidenceFreshness(facts["freshness"])
    if family == "high_cash":
        refs = _high_cash_refs(as_of_date, evaluated_at, freshness)
        return evaluate_high_cash_signal(
            HighCashSignalInput(
                as_of_date=as_of_date,
                source_reported_cash_weight=Decimal(facts["cashWeight"]),
                portfolio_state_ref=refs[0],
                holdings_ref=refs[1],
                cash_movement_ref=refs[2],
                cashflow_projection_ref=refs[3],
                evaluated_at_utc=evaluated_at,
            ),
            HighCashSignalPolicy("idle-liquidity-v1", Decimal("0.12"), Decimal("82")),
        )
    if family == "concentration":
        return evaluate_concentration_risk_signal(
            ConcentrationRiskSignalInput(
                as_of_date=as_of_date,
                top_position_weight_current=Decimal(facts["topPositionWeight"]),
                top_issuer_weight_current=Decimal(facts["topIssuerWeight"]),
                issuer_coverage_status=facts["issuerCoverageStatus"],
                concentration_ref=_source_ref(
                    product_id="lotus-risk:ConcentrationRiskReport:v1",
                    source_system=SourceSystem.LOTUS_RISK,
                    route="/analytics/risk/concentration",
                    as_of_date=as_of_date,
                    evaluated_at=evaluated_at,
                    freshness=freshness,
                ),
                evaluated_at_utc=evaluated_at,
            ),
            ConcentrationRiskSignalPolicy(
                "concentration-attention-v1", Decimal("0.15"), Decimal("0.20"), Decimal("78")
            ),
        )
    if family == "underperformance":
        return evaluate_underperformance_signal(
            UnderperformanceSignalInput(
                as_of_date=as_of_date,
                source_reported_active_return=Decimal(facts["activeReturn"]),
                benchmark_context_available=facts["benchmarkContextAvailable"],
                performance_ref=_source_ref(
                    product_id="lotus-performance:ReturnsSeriesBundle:v1",
                    source_system=SourceSystem.LOTUS_PERFORMANCE,
                    route="/integration/returns/series",
                    as_of_date=as_of_date,
                    evaluated_at=evaluated_at,
                    freshness=freshness,
                ),
                evaluated_at_utc=evaluated_at,
            ),
            UnderperformanceSignalPolicy(
                "underperformance-review-v1", Decimal("-0.005"), Decimal("74")
            ),
        )
    if family == "allocation_drift":
        return evaluate_mandate_health_signal(
            MandateHealthSignalInput(
                as_of_date=as_of_date,
                workflow_decision_count=facts["workflowDecisionCount"],
                lineage_edge_count=facts["lineageEdgeCount"],
                manage_supportability_state=facts["supportabilityState"],
                portfolio_scope_confirmed=facts["portfolioScopeConfirmed"],
                action_register_ref=_source_ref(
                    product_id="lotus-manage:PortfolioActionRegister:v1",
                    source_system=SourceSystem.LOTUS_MANAGE,
                    route="/api/v1/rebalance/supportability/summary",
                    as_of_date=as_of_date,
                    evaluated_at=evaluated_at,
                    freshness=freshness,
                ),
                evaluated_at_utc=evaluated_at,
            ),
            MandateHealthSignalPolicy(
                "allocation-drift-mandate-review-v1", 1, 1, Decimal("70")
            ),
        )
    raise AssertionError(f"unsupported golden-set family: {family}")


def _compare_case(case: dict[str, Any], result: SignalEvaluationResult) -> tuple[str, ...]:
    expected = case["expected"]
    case_id = case["caseId"]
    errors: list[str] = []
    comparisons = {
        "outcome": result.outcome.value,
        "reasonCodes": [reason.value for reason in result.reason_codes],
        "unsupportedReasons": [reason.value for reason in result.unsupported_reasons],
    }
    for field_name, actual_result_value in comparisons.items():
        if actual_result_value != expected[field_name]:
            errors.append(
                f"{case_id} {field_name} expected {expected[field_name]!r}, "
                f"got {actual_result_value!r}"
            )

    if result.candidate is None:
        if expected["outcome"] == "candidate_created":
            errors.append(f"{case_id} expected a candidate")
        return tuple(errors)
    if expected["outcome"] != "candidate_created":
        errors.append(f"{case_id} unexpectedly created a candidate")
        return tuple(errors)
    actual_products = [ref.product_id for ref in result.candidate.evidence_packet.source_refs]
    candidate_comparisons: dict[str, object] = {
        "score": str(result.candidate.score.score) if result.candidate.score else None,
        "reviewPosture": result.candidate.review_posture.value,
        "sourceProducts": actual_products,
    }
    for field_name, actual_candidate_value in candidate_comparisons.items():
        if actual_candidate_value != expected[field_name]:
            errors.append(
                f"{case_id} {field_name} expected {expected[field_name]!r}, "
                f"got {actual_candidate_value!r}"
            )
    return tuple(errors)


def _high_cash_refs(
    as_of_date: date,
    evaluated_at: datetime,
    freshness: EvidenceFreshness,
) -> tuple[SourceRef, SourceRef, SourceRef, SourceRef]:
    products_and_routes = (
        ("lotus-core:PortfolioStateSnapshot:v1", "/integration/portfolios/{portfolio_id}/core-snapshot"),
        ("lotus-core:HoldingsAsOf:v1", "/portfolios/{portfolio_id}/cash-balances"),
        (
            "lotus-core:PortfolioCashMovementSummary:v1",
            "/portfolios/{portfolio_id}/cash-movement-summary",
        ),
        (
            "lotus-core:PortfolioCashflowProjection:v1",
            "/portfolios/{portfolio_id}/cashflow-projection",
        ),
    )
    refs = tuple(
        _source_ref(
            product_id=product_id,
            source_system=SourceSystem.LOTUS_CORE,
            route=route,
            as_of_date=as_of_date,
            evaluated_at=evaluated_at,
            freshness=freshness,
        )
        for product_id, route in products_and_routes
    )
    return refs[0], refs[1], refs[2], refs[3]


def _source_ref(
    *,
    product_id: str,
    source_system: SourceSystem,
    route: str,
    as_of_date: date,
    evaluated_at: datetime,
    freshness: EvidenceFreshness,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version="v1",
        route=route,
        as_of_date=as_of_date,
        generated_at_utc=evaluated_at.astimezone(UTC),
        content_hash=f"sha256:golden:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


__all__ = ["GOLDEN_SET_PATH", "evaluate_golden_set", "load_golden_set"]
