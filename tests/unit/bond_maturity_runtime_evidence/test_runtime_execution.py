from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
import json
from typing import Any, Callable

import pytest

from app.application.bond_maturity_runtime_evidence import (
    BOND_MATURITY_REMAINING_BLOCKERS,
    BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateBondMaturityReadiness,
    bond_maturity_runtime_execution_is_valid,
    build_blocked_bond_maturity_runtime_execution,
    build_bond_maturity_runtime_execution,
    evaluate_bond_maturity_readiness,
)
from app.application.core_runtime_evidence import sha256_json
from app.domain import EvidenceFreshness
from app.ports.core_sources import CoreBondMaturityEvidence, CoreBondMaturityEvidenceRequest
from tests.support.bond_maturity_runtime_evidence import (
    authoritative_bond_maturity_evidence,
    valid_bond_maturity_runtime_evidence,
)

NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
AS_OF = date(2026, 6, 21)


class RecordingSource:
    def __init__(self, evidence: CoreBondMaturityEvidence | None = None) -> None:
        request = CoreBondMaturityEvidenceRequest(
            tenant_id="tenant-a",
            portfolio_id="portfolio-a",
            as_of_date=AS_OF,
            evaluated_at_utc=NOW,
            maturity_window_days=30,
            correlation_id="corr-a",
            trace_id="trace-a",
        )
        self.evidence = evidence or authoritative_bond_maturity_evidence(request=request)
        self.request: CoreBondMaturityEvidenceRequest | None = None

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        self.request = request
        return self.evidence


def test_use_case_preserves_scope_and_builds_source_safe_closed_receipts() -> None:
    source = RecordingSource()
    command = _command()

    result = evaluate_bond_maturity_readiness(command, core_source=source)
    payload = build_bond_maturity_runtime_execution(generated_at_utc=NOW, result=result)

    assert source.request == CoreBondMaturityEvidenceRequest(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        maturity_window_days=30,
        correlation_id="corr-a",
        trace_id="trace-a",
    )
    request = payload["execution"]["requestReceipt"]
    receipt = payload["execution"]["sourceReceipt"]
    assert request["maturityWindowDays"] == 30
    assert request["includeProjected"] is False
    assert request["tenantIdHash"].startswith("sha256:")
    assert receipt["responseProductName"] == "PortfolioMaturitySummary"
    assert receipt["upstreamProductId"] == "lotus-core:HoldingsAsOf:v1"
    assert receipt["maturityBasis"] == "CONTRACTUAL_INSTRUMENT_MATURITY_DATE"
    assert receipt["supportabilityStatus"] == "SUPPORTED"
    assert payload["execution"]["opportunityDetected"] is True
    assert payload["aggregateBlockersSatisfied"] == list(
        BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(BOND_MATURITY_REMAINING_BLOCKERS)
    assert payload["nonProofClaims"]["maturityFactsOwned"] == "lotus-core"
    assert all(
        value is False
        for key, value in payload["nonProofClaims"].items()
        if key != "maturityFactsOwned"
    )
    serialized = json.dumps(payload)
    assert "tenant-a" not in serialized
    assert "portfolio-a" not in serialized
    assert "corr-a" not in serialized
    assert bond_maturity_runtime_execution_is_valid(payload)


def test_supported_empty_window_is_valid_without_false_opportunity() -> None:
    payload = valid_bond_maturity_runtime_evidence(
        evaluated_at_utc=NOW,
        opportunity_detected=False,
    )

    assert payload["execution"]["opportunityDetected"] is False
    assert payload["execution"]["sourceReceipt"]["nextMaturityDate"] is None
    assert payload["execution"]["sourceReceipt"]["maturingHoldingCount"] == 0
    assert bond_maturity_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    [
        (lambda value: replace(value, maturity_fact_ref=None), "core_maturity_source_ref_missing"),
        (
            lambda value: replace(
                value,
                maturity_fact_ref=replace(
                    value.maturity_fact_ref, freshness=EvidenceFreshness.STALE
                ),
            ),
            "core_maturity_evidence_not_current",
        ),
        (lambda value: replace(value, holdings_ref=None), "core_maturity_upstream_holdings_ref_missing"),
        (lambda value: replace(value, entitlement_allowed=False), "core_maturity_entitlement_denied"),
        (lambda value: replace(value, response_product_name="Other"), "core_maturity_product_identity_mismatch"),
        (lambda value: replace(value, response_tenant_id="tenant-b"), "core_maturity_response_scope_mismatch"),
        (lambda value: replace(value, response_portfolio_id="portfolio-b"), "core_maturity_response_scope_mismatch"),
        (lambda value: replace(value, horizon_days=31), "core_maturity_window_scope_mismatch"),
        (lambda value: replace(value, include_projected=True), "core_maturity_window_scope_mismatch"),
        (lambda value: replace(value, maturity_basis="CALL_DATE"), "core_maturity_basis_unsupported"),
        (lambda value: replace(value, source_reported_maturing_position_count=-1), "core_maturity_counts_invalid"),
        (lambda value: replace(value, source_reported_next_maturity_date=None), "core_maturity_fact_inconsistent"),
        (lambda value: replace(value, supportability_status="PARTIAL"), "core_maturity_supportability_not_supported"),
        (lambda value: replace(value, supportability_reasons=("HOLDINGS_PARTIAL",)), "core_maturity_supportability_reasons_present"),
        (lambda value: replace(value, missing_maturity_date_count=1), "core_maturity_dates_incomplete"),
        (lambda value: replace(value, unsupported_maturity_feature_count=1), "core_maturity_product_features_unsupported"),
        (lambda value: replace(value, request_fingerprint="summary"), "core_maturity_request_fingerprint_invalid"),
        (lambda value: replace(value, snapshot_id=None), "core_maturity_snapshot_identity_missing"),
        (lambda value: replace(value, response_content_hash="sha256:" + "c" * 64), "core_maturity_source_digest_mismatch"),
        (lambda value: replace(value, reconciliation_status="UNKNOWN"), "core_maturity_reconciliation_incomplete"),
        (
            lambda value: replace(
                value,
                maturity_fact_ref=replace(value.maturity_fact_ref, data_quality_status="PARTIAL"),
            ),
            "core_maturity_data_quality_incomplete",
        ),
        (lambda value: replace(value, source_evidence_current=False), "core_maturity_source_current_posture_missing"),
        (lambda value: replace(value, latest_evidence_at_utc=NOW + timedelta(seconds=1)), "core_maturity_latest_evidence_time_invalid"),
        (lambda value: replace(value, source_correlation_id="corr-b"), "core_maturity_correlation_binding_missing"),
    ],
)
def test_domain_failures_cannot_clear_aggregate_blocker(
    mutation: Callable[[CoreBondMaturityEvidence], CoreBondMaturityEvidence],
    expected_blocker: str,
) -> None:
    source = RecordingSource()
    source.evidence = mutation(source.evidence)
    result = evaluate_bond_maturity_readiness(_command(), core_source=source)

    payload = build_bond_maturity_runtime_execution(generated_at_utc=NOW, result=result)

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not bond_maturity_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "tamper",
    [
        "top_level",
        "proof_type",
        "claim_shape",
        "execution",
        "request",
        "source",
        "request_digest",
        "source_digest",
        "tenant_binding",
        "portfolio_binding",
        "correlation_binding",
        "horizon_binding",
        "source_substitution",
        "content_hash",
        "upstream_hash",
        "future_generated",
        "future_latest_evidence",
        "claim_inflation",
        "remaining_blockers",
        "evidence_refs",
    ],
)
def test_closed_contract_rejects_tampering(tamper: str) -> None:
    payload = valid_bond_maturity_runtime_evidence(evaluated_at_utc=NOW)
    _tamper(payload, tamper)

    assert not bond_maturity_runtime_execution_is_valid(payload)


def test_blocked_execution_is_source_safe_and_never_valid() -> None:
    payload = build_blocked_bond_maturity_runtime_execution(
        generated_at_utc=NOW,
        command=_command(),
        error_code="core_source_entitlement_denied",
    )

    assert payload["execution"]["sourceReceipt"] is None
    assert payload["aggregateBlockersSatisfied"] == []
    assert "core_source_entitlement_denied" in payload["execution"]["qualificationBlockers"]
    assert "tenant-a" not in json.dumps(payload)
    assert not bond_maturity_runtime_execution_is_valid(payload)


def _command() -> EvaluateBondMaturityReadiness:
    return EvaluateBondMaturityReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        maturity_window_days=30,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def _tamper(payload: dict[str, Any], tamper: str) -> None:
    execution = payload["execution"]
    request = execution["requestReceipt"]
    source = execution["sourceReceipt"]
    if tamper == "top_level":
        payload["invented"] = True
    elif tamper == "proof_type":
        payload["proofType"] = "caller_summary"
    elif tamper == "claim_shape":
        del payload["nonProofClaims"]["orderExecutionReady"]
    elif tamper == "execution":
        execution["invented"] = True
    elif tamper == "request":
        request["invented"] = True
    elif tamper == "source":
        source["invented"] = True
    elif tamper == "request_digest":
        request["requestDigest"] = "sha256:" + "0" * 64
    elif tamper == "source_digest":
        source["receiptDigest"] = "sha256:" + "0" * 64
    elif tamper == "tenant_binding":
        source["responseTenantIdHash"] = "sha256:" + "1" * 64
        _refresh_source_digest(source)
    elif tamper == "portfolio_binding":
        source["responsePortfolioIdHash"] = "sha256:" + "2" * 64
        _refresh_source_digest(source)
    elif tamper == "correlation_binding":
        source["sourceCorrelationIdHash"] = "sha256:" + "3" * 64
        _refresh_source_digest(source)
    elif tamper == "horizon_binding":
        source["horizonDays"] = 45
        _refresh_source_digest(source)
    elif tamper == "source_substitution":
        source["sourceSystem"] = "lotus-risk"
        _refresh_source_digest(source)
    elif tamper == "content_hash":
        source["responseContentHash"] = "sha256:" + "c" * 64
        _refresh_source_digest(source)
    elif tamper == "upstream_hash":
        source["upstreamContentHash"] = "sha256:" + "d" * 64
        _refresh_source_digest(source)
    elif tamper == "future_generated":
        source["generatedAtUtc"] = "2026-06-21T10:11:00Z"
        _refresh_source_digest(source)
    elif tamper == "future_latest_evidence":
        source["latestEvidenceAtUtc"] = "2026-06-21T10:11:00Z"
        _refresh_source_digest(source)
    elif tamper == "claim_inflation":
        payload["nonProofClaims"]["reinvestmentAdviceProduced"] = True
    elif tamper == "remaining_blockers":
        payload["remainingCertificationBlockers"] = []
    elif tamper == "evidence_refs":
        payload["evidenceRefs"] = []
    else:
        raise AssertionError(f"unknown tamper: {tamper}")


def _refresh_source_digest(source: dict[str, Any]) -> None:
    source["receiptDigest"] = sha256_json(
        {key: value for key, value in source.items() if key != "receiptDigest"}
    )
