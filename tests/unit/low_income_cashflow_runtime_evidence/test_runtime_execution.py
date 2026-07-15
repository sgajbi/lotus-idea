from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
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
from app.domain import SignalEvaluationOutcome
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


def test_runtime_execution_rejects_unknown_and_tampered_claims() -> None:
    payload = _valid_payload()
    unknown = deepcopy(payload)
    unknown["execution"]["unexpected"] = True
    tampered = deepcopy(payload)
    tampered["execution"]["cashflowProjectionReceipt"]["totalNetCashflow"] = "0"

    assert low_income_cashflow_runtime_execution_is_valid(unknown) is False
    assert low_income_cashflow_runtime_execution_is_valid(tampered) is False


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
