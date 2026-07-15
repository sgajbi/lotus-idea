from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

import pytest

from app.application.low_income_cashflow_runtime_evidence import (
    LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateLowIncomeCashflowReadiness,
    build_blocked_low_income_cashflow_runtime_execution,
    build_low_income_cashflow_runtime_execution,
    evaluate_low_income_cashflow_readiness,
    low_income_cashflow_runtime_execution_is_valid,
)
from app.application.runtime_evidence import sha256_json
from app.domain import EvidenceFreshness, LowIncomeSignalPolicy, SignalEvaluationOutcome
from app.ports.core_sources import CoreLowIncomeEvidence, CoreLowIncomeEvidenceRequest
from tests.support.low_income_cashflow_runtime_evidence import (
    AuthoritativeCoreLowIncomeSource,
    authoritative_low_income_evidence,
)

NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    ("minimum", "expected_outcome"),
    [
        (Decimal("-12500"), SignalEvaluationOutcome.CANDIDATE_CREATED),
        (Decimal("-10000"), SignalEvaluationOutcome.CANDIDATE_CREATED),
        (Decimal("-9999.99"), SignalEvaluationOutcome.NOT_ELIGIBLE),
        (Decimal("0"), SignalEvaluationOutcome.NOT_ELIGIBLE),
    ],
)
def test_runtime_execution_binds_domain_threshold_outcome(
    minimum: Decimal,
    expected_outcome: SignalEvaluationOutcome,
) -> None:
    result = evaluate_low_income_cashflow_readiness(
        _command(),
        core_source=AuthoritativeCoreLowIncomeSource(minimum_cashflow=minimum),
    )

    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=result)

    assert result.evaluation.outcome is expected_outcome
    assert low_income_cashflow_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED
    )
    serialized = str(payload)
    assert "tenant-a" not in serialized
    assert "portfolio-a" not in serialized
    assert "corr-a" not in serialized


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    [
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_product=replace(
                    evidence.cashflow_projection_product,
                    range_end_date=date(2026, 7, 20),
                ),
            ),
            "core_cashflow_projection_scope_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    cashflow_count=2,
                ),
            ),
            "core_cash_movement_counts_invalid",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_product=replace(
                    evidence.cashflow_projection_product,
                    runtime=replace(
                        evidence.cashflow_projection_product.runtime,
                        reconciliation_status="UNKNOWN",
                    ),
                ),
            ),
            "core_cashflow_projection_supportability_incomplete",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_product=replace(
                    evidence.cashflow_projection_product,
                    total_net_cashflow=Decimal("-1"),
                ),
            ),
            "core_cashflow_projection_series_invalid",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_ref=replace(
                    evidence.cashflow_projection_ref,
                    product_id="lotus-core:OtherProduct:v1",
                ),
            ),
            "core_cashflow_projection_source_ref_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    runtime=replace(
                        evidence.cash_movement_product.runtime,
                        generated_at_utc=NOW + timedelta(minutes=1),
                    ),
                ),
            ),
            "core_cash_movement_evidence_time_invalid",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_product=replace(
                    evidence.cashflow_projection_product,
                    runtime=replace(
                        evidence.cashflow_projection_product.runtime,
                        correlation_id="corr-other",
                    ),
                ),
            ),
            "core_cashflow_projection_correlation_binding_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    runtime=replace(
                        evidence.cash_movement_product.runtime,
                        degradation_status="PARTIAL",
                        degradation_reason_codes=("SOURCE_PARTIAL",),
                        degradation_detail_count=1,
                    ),
                ),
            ),
            "core_cash_movement_supportability_incomplete",
        ),
        (
            lambda evidence: replace(
                evidence,
                source_reported_min_projected_cumulative_cashflow=Decimal("-1"),
            ),
            "core_cashflow_minimum_mismatch",
        ),
    ],
)
def test_runtime_execution_fails_closed_on_source_trust_drift(
    mutation: Callable[[CoreLowIncomeEvidence], CoreLowIncomeEvidence],
    expected_blocker: str,
) -> None:
    command = _command()
    evidence = authoritative_low_income_evidence(
        request=_request(command),
        minimum_cashflow=Decimal("-12500"),
    )
    mutated = mutation(evidence)
    result = evaluate_low_income_cashflow_readiness(
        command,
        core_source=_FixedSource(mutated),
    )

    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=result)

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    [
        (
            lambda evidence: replace(evidence, cash_movement_product=None),
            "core_cash_movement_receipt_missing",
        ),
        (
            lambda evidence: replace(evidence, cashflow_projection_product=None),
            "core_cashflow_projection_receipt_missing",
        ),
        (
            lambda evidence: replace(evidence, entitlement_allowed=False),
            "core_cashflow_entitlement_denied",
        ),
        (
            lambda evidence: replace(evidence, cashflow_diagnostic="SOURCE_DEGRADED"),
            "core_cashflow_diagnostic_not_ready",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_ref=replace(
                    evidence.cashflow_projection_ref,
                    as_of_date=date(2026, 6, 20),
                ),
            ),
            "core_cashflow_projection_scope_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_ref=replace(
                    evidence.cashflow_projection_ref,
                    freshness=EvidenceFreshness.STALE,
                ),
            ),
            "core_cashflow_projection_evidence_not_current",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    end_date=date(2026, 6, 22),
                ),
            ),
            "core_cash_movement_window_mismatch",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    buckets=evidence.cash_movement_product.buckets * 2,
                    cashflow_count=2,
                ),
                cash_movement_count=2,
            ),
            "core_cash_movement_buckets_invalid",
        ),
        (
            lambda evidence: replace(
                evidence,
                cash_movement_product=replace(
                    evidence.cash_movement_product,
                    buckets=(
                        replace(
                            evidence.cash_movement_product.buckets[0],
                            movement_direction="INFLOW",
                        ),
                    ),
                ),
            ),
            "core_cash_movement_direction_mismatch",
        ),
        (
            lambda evidence: _replace_projection_runtime(evidence, portfolio_id="other"),
            "core_cashflow_projection_response_scope_mismatch",
        ),
        (
            lambda evidence: _replace_projection_runtime(
                evidence,
                source_digest="sha256:" + "e" * 64,
            ),
            "core_cashflow_projection_source_digest_mismatch",
        ),
        (
            lambda evidence: _replace_projection_runtime(evidence, snapshot_id=None),
            "core_cashflow_projection_governance_identity_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                cashflow_projection_product=replace(
                    evidence.cashflow_projection_product,
                    points=evidence.cashflow_projection_product.points[:-1],
                ),
            ),
            "core_cashflow_projection_series_invalid",
        ),
        (
            lambda evidence: _replace_projection_point(
                evidence,
                1,
                projection_date=date(2026, 6, 25),
            ),
            "core_cashflow_projection_series_invalid",
        ),
        (
            lambda evidence: _replace_projection_point(
                evidence,
                0,
                net_cashflow=Decimal("1"),
            ),
            "core_cashflow_projection_series_invalid",
        ),
        (
            lambda evidence: _replace_projection_point(
                evidence,
                0,
                projected_cumulative_cashflow=Decimal("-1"),
            ),
            "core_cashflow_projection_series_invalid",
        ),
    ],
)
def test_runtime_execution_rejects_incomplete_or_inconsistent_core_receipts(
    mutation: Callable[[CoreLowIncomeEvidence], CoreLowIncomeEvidence],
    expected_blocker: str,
) -> None:
    command = _command()
    evidence = authoritative_low_income_evidence(
        request=_request(command),
        minimum_cashflow=Decimal("-12500"),
    )

    result = evaluate_low_income_cashflow_readiness(
        command,
        core_source=_FixedSource(mutation(evidence)),
    )
    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=result)

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "changes",
    [
        {"tenant_id": " "},
        {"horizon_days": 0},
        {"correlation_id": " "},
    ],
)
def test_readiness_command_rejects_invalid_execution_scope(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(_command(), **changes)


def test_runtime_execution_rejects_unknown_and_tampered_claims() -> None:
    payload = _valid_payload()
    unknown = deepcopy(payload)
    unknown["execution"]["unexpected"] = True
    tampered = deepcopy(payload)
    tampered["execution"]["cashflowProjectionReceipt"]["totalNetCashflow"] = "0"

    assert low_income_cashflow_runtime_execution_is_valid(unknown) is False
    assert low_income_cashflow_runtime_execution_is_valid(tampered) is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"unexpected": True}),
        lambda payload: payload.update({"proofType": "caller_summary"}),
        lambda payload: payload["nonProofClaims"].update({"cashflowFactsOwned": "lotus-idea"}),
        lambda payload: payload["nonProofClaims"].update({"portfolioAccountingOwned": True}),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["cashMovementReceipt"],
            reconciliationStatus="UNKNOWN",
        ),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["evaluationReceipt"],
            outcome="not_eligible",
        ),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["requestReceipt"],
            asOfDate="not-a-date",
        ),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["requestReceipt"],
            horizonDays=0,
        ),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["cashMovementReceipt"],
            responseTenantIdHash="sha256:" + "f" * 64,
        ),
        lambda payload: _mutate_and_redigest(
            payload["execution"]["evaluationReceipt"],
            candidateScore="not-a-decimal",
        ),
    ],
)
def test_contract_rejects_closed_schema_and_semantic_tampering(
    mutation: Callable[[dict[str, Any]], object],
) -> None:
    payload = _valid_payload()

    mutation(payload)

    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


def test_contract_rejects_semantic_forgery_with_recomputed_digest() -> None:
    payload = _valid_payload()
    request = payload["execution"]["requestReceipt"]
    request["horizonDays"] = 29
    request["requestDigest"] = sha256_json(
        {key: value for key, value in request.items() if key != "requestDigest"}
    )

    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


def test_runtime_execution_rejects_policy_result_drift() -> None:
    result = evaluate_low_income_cashflow_readiness(
        _command(),
        core_source=AuthoritativeCoreLowIncomeSource(),
    )
    mismatched = replace(
        result,
        policy=LowIncomeSignalPolicy(
            policy_version="cashflow-liquidity-review-v2",
            projected_cumulative_cashflow_threshold=Decimal("-20000"),
            candidate_score=Decimal("68"),
        ),
    )

    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=mismatched)

    assert (
        "low_income_no_opportunity_outcome_mismatch"
        in payload["execution"]["qualificationBlockers"]
    )
    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


def test_runtime_execution_requires_candidate_identity_for_eligible_cashflow() -> None:
    result = evaluate_low_income_cashflow_readiness(
        _command(),
        core_source=AuthoritativeCoreLowIncomeSource(),
    )
    result = replace(result, evaluation=replace(result.evaluation, candidate=None))

    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=result)

    assert "low_income_candidate_identity_missing" in payload["execution"]["qualificationBlockers"]
    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


def test_blocked_runtime_execution_never_qualifies() -> None:
    payload = build_blocked_low_income_cashflow_runtime_execution(
        generated_at_utc=NOW,
        command=_command(),
        error_code="core_source_entitlement_denied",
    )

    assert payload["aggregateBlockersSatisfied"] == []
    assert low_income_cashflow_runtime_execution_is_valid(payload) is False


def _valid_payload() -> dict[str, Any]:
    result = evaluate_low_income_cashflow_readiness(
        _command(),
        core_source=AuthoritativeCoreLowIncomeSource(),
    )
    return build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=result)


def _command() -> EvaluateLowIncomeCashflowReadiness:
    return EvaluateLowIncomeCashflowReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=NOW,
        horizon_days=30,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def _request(command: EvaluateLowIncomeCashflowReadiness) -> CoreLowIncomeEvidenceRequest:
    return CoreLowIncomeEvidenceRequest(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
        as_of_date=command.as_of_date,
        evaluated_at_utc=command.evaluated_at_utc,
        horizon_days=command.horizon_days,
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )


class _FixedSource:
    def __init__(self, evidence: CoreLowIncomeEvidence) -> None:
        self.evidence = evidence

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        return self.evidence


def _replace_projection_runtime(
    evidence: CoreLowIncomeEvidence,
    **changes: Any,
) -> CoreLowIncomeEvidence:
    projection = evidence.cashflow_projection_product
    assert projection is not None
    return replace(
        evidence,
        cashflow_projection_product=replace(
            projection,
            runtime=replace(projection.runtime, **changes),
        ),
    )


def _replace_projection_point(
    evidence: CoreLowIncomeEvidence,
    index: int,
    **changes: Any,
) -> CoreLowIncomeEvidence:
    projection = evidence.cashflow_projection_product
    assert projection is not None
    points = list(projection.points)
    points[index] = replace(points[index], **changes)
    return replace(
        evidence,
        cashflow_projection_product=replace(projection, points=tuple(points)),
    )


def _mutate_and_redigest(receipt: dict[str, Any], **changes: Any) -> None:
    receipt.update(changes)
    digest_field = next(
        key for key in ("requestDigest", "receiptDigest", "evaluationDigest") if key in receipt
    )
    receipt[digest_field] = sha256_json(
        {key: value for key, value in receipt.items() if key != digest_field}
    )
