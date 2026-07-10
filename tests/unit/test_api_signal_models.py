from __future__ import annotations

import importlib.util
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.api.signal_models import (
    ReviewAccessScopeRequest,
    SignalEvaluationResponse,
    SourceRefRequest,
)
from app.api.allocation_drift_signals import EvaluateAllocationDriftFromSourceRequest
from app.api.bond_maturity_signals import EvaluateBondMaturityFromSourceRequest
from app.api.concentration_risk_signals import EvaluateConcentrationRiskFromSourceRequest
from app.api.drawdown_review_signals import EvaluateDrawdownReviewFromSourceRequest
from app.api.high_volatility_signals import EvaluateHighVolatilityFromSourceRequest
from app.api.idea_signal_models import (
    EvaluateHighCashFromSourceRequest,
    EvaluateMandateRestrictionFromSourceRequest,
)
from app.api.low_income_signals import EvaluateLowIncomeFromSourceRequest
from app.api.missing_benchmark_signals import EvaluateMissingBenchmarkFromSourceRequest
from app.api.missing_risk_profile_signals import EvaluateMissingRiskProfileFromSourceRequest
from app.api.missing_suitability_signals import EvaluateMissingSuitabilityFromSourceRequest
from app.api.underperformance_signals import EvaluateUnderperformanceFromSourceRequest
from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_api_signal_model_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_signal_model_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("api_signal_model_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_access_scope_request_validates_and_maps_to_domain() -> None:
    request = ReviewAccessScopeRequest(
        tenantId="tenant-1",
        bookId="book-1",
        portfolioId="portfolio-1",
        clientId="client-1",
    )

    domain_scope = request.to_domain()

    assert domain_scope.tenant_id == "tenant-1"
    assert domain_scope.book_id == "book-1"
    assert domain_scope.portfolio_id == "portfolio-1"
    assert domain_scope.client_id == "client-1"


def test_review_access_scope_request_rejects_blank_scope_fields() -> None:
    with pytest.raises(ValidationError, match="scope fields cannot be blank"):
        ReviewAccessScopeRequest(
            tenantId="tenant-1",
            bookId=" ",
            portfolioId="portfolio-1",
            clientId="client-1",
        )


def test_source_ref_request_preserves_source_authority_metadata() -> None:
    request = SourceRefRequest(
        productId="lotus-core:PortfolioStateSnapshot:v1",
        sourceSystem=SourceSystem.LOTUS_CORE,
        productVersion="v1",
        route="/integration/portfolios/{portfolioRef}/core-snapshot",
        asOfDate=date(2026, 6, 21),
        generatedAtUtc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        contentHash="sha256:portfolio-state-snapshot-demo",
        dataQualityStatus="complete",
        freshness=EvidenceFreshness.CURRENT,
    )

    source_ref = request.to_domain()

    assert source_ref.product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert source_ref.source_system is SourceSystem.LOTUS_CORE
    assert source_ref.product_version == "v1"
    assert source_ref.route == "/integration/portfolios/{portfolioRef}/core-snapshot"
    assert source_ref.content_hash == "sha256:portfolio-state-snapshot-demo"
    assert source_ref.data_quality_status == "complete"
    assert source_ref.freshness is EvidenceFreshness.CURRENT


def test_signal_evaluation_response_maps_domain_result_source_safely() -> None:
    source_refs = (
        _source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        _source_ref("lotus-core:HoldingsAsOf:v1"),
        _source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        _source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=date(2026, 6, 21),
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=source_refs[0],
            holdings_ref=source_refs[1],
            cash_movement_ref=source_refs[2],
            cashflow_projection_ref=source_refs[3],
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )

    response = SignalEvaluationResponse.from_domain(result, source_authority="lotus-core")

    payload = response.model_dump(by_alias=True)
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "high_cash"
    assert payload["reasonCodes"] == (
        "high_cash_ratio",
        "cash_source_ready",
        "review_required",
    )
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-core:PortfolioStateSnapshot:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_api_signal_model_boundary_gate_passes_current_repository() -> None:
    module = _load_api_signal_model_boundary_gate()

    assert module.validate_api_signal_model_boundary() == []


def _portfolio_source_request_payload() -> dict[str, object]:
    return {
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "asOfDate": date(2026, 6, 21),
        "evaluatedAtUtc": datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    }


def _evaluation_source_request_payload() -> dict[str, object]:
    return {
        "evaluationId": "pev_001",
        "asOfDate": date(2026, 6, 21),
        "evaluatedAtUtc": datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
    }


@pytest.mark.parametrize(
    ("request_model", "payload", "field", "message"),
    [
        (
            EvaluateAllocationDriftFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateBondMaturityFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateConcentrationRiskFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateDrawdownReviewFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateHighVolatilityFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateLowIncomeFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateHighCashFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateMissingBenchmarkFromSourceRequest,
            _portfolio_source_request_payload(),
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateUnderperformanceFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "portfolioId",
            "portfolioId is required",
        ),
        (
            EvaluateDrawdownReviewFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "periodName",
            "periodName is required",
        ),
        (
            EvaluateHighVolatilityFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "periodName",
            "periodName is required",
        ),
        (
            EvaluateUnderperformanceFromSourceRequest,
            {**_portfolio_source_request_payload(), "periodName": "YTD"},
            "periodName",
            "periodName is required",
        ),
        (
            EvaluateMissingRiskProfileFromSourceRequest,
            _evaluation_source_request_payload(),
            "evaluationId",
            "evaluationId is required",
        ),
        (
            EvaluateMissingSuitabilityFromSourceRequest,
            _evaluation_source_request_payload(),
            "evaluationId",
            "evaluationId is required",
        ),
        (
            EvaluateMandateRestrictionFromSourceRequest,
            _evaluation_source_request_payload(),
            "evaluationId",
            "evaluationId is required",
        ),
    ],
)
def test_source_request_rejects_blank_identity_fields(
    request_model: type[Any],
    payload: dict[str, object],
    field: str,
    message: str,
) -> None:
    invalid_payload = {**payload, field: " "}

    with pytest.raises(ValidationError, match=message):
        request_model(**invalid_payload)


def test_missing_benchmark_request_preserves_explicitly_omitted_currency() -> None:
    request = EvaluateMissingBenchmarkFromSourceRequest(
        **cast(Any, _portfolio_source_request_payload()),
        reportingCurrency=None,
    )

    assert request.reporting_currency is None


def test_missing_benchmark_request_rejects_blank_currency() -> None:
    with pytest.raises(ValidationError, match="reportingCurrency must not be blank"):
        EvaluateMissingBenchmarkFromSourceRequest(
            **cast(Any, _portfolio_source_request_payload()),
            reportingCurrency=" ",
        )


def test_underperformance_request_preserves_optional_currency_and_normalizes_it() -> None:
    request = EvaluateUnderperformanceFromSourceRequest(
        **cast(Any, _portfolio_source_request_payload()),
        periodName="YTD",
        reportingCurrency=None,
    )
    normalized = EvaluateUnderperformanceFromSourceRequest(
        **cast(Any, _portfolio_source_request_payload()),
        periodName="YTD",
        reportingCurrency="usd",
    )

    assert request.reporting_currency is None
    assert normalized.reporting_currency == "USD"


def test_underperformance_request_rejects_non_iso_currency() -> None:
    with pytest.raises(ValidationError, match="3-letter ISO currency code"):
        EvaluateUnderperformanceFromSourceRequest(
            **cast(Any, _portfolio_source_request_payload()),
            periodName="YTD",
            reportingCurrency="US1",
        )


def test_api_signal_model_boundary_gate_blocks_route_module_dto_import(tmp_path: Path) -> None:
    module = _load_api_signal_model_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "unsafe_signal.py").write_text(
        "from app.api.idea_signals import SourceRefRequest, router\n",
        encoding="utf-8",
    )

    errors = module.validate_api_signal_model_boundary(tmp_path)

    assert errors == [
        "src/app/api/unsafe_signal.py:1: shared signal API DTOs (SourceRefRequest) must "
        "be imported from `app.api.signal_models`, not from the `idea_signals` route module"
    ]


def _source_ref(product_id: str) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolioRef}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolioRef}/cash-balances",
        "lotus-core:PortfolioCashMovementSummary:v1": "/portfolios/{portfolioRef}/cash-movement-summary",
        "lotus-core:PortfolioCashflowProjection:v1": "/portfolios/{portfolioRef}/cashflow-projection",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
