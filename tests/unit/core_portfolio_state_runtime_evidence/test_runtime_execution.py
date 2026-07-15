from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
import json
from typing import Any

import pytest

from app.application.core_portfolio_state_runtime_evidence import (
    CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS,
    CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateCorePortfolioStateReadiness,
    build_blocked_core_portfolio_state_runtime_execution,
    build_core_portfolio_state_runtime_execution,
    core_portfolio_state_runtime_execution_is_valid,
    evaluate_core_portfolio_state_readiness,
)
from app.application.core_runtime_evidence import sha256_json
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
)

NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
AS_OF = date(2026, 6, 21)
CONTENT_HASH = "sha256:" + "a" * 64


class RecordingSource:
    def __init__(self, evidence: CorePortfolioStateEvidence | None = None) -> None:
        self.request: CorePortfolioStateEvidenceRequest | None = None
        self.evidence = evidence or _evidence()

    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        self.request = request
        return self.evidence


def test_use_case_preserves_exact_scope_and_builds_closed_receipts() -> None:
    source = RecordingSource()
    command = _command()

    result = evaluate_core_portfolio_state_readiness(command, core_source=source)
    payload = build_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert source.request == CorePortfolioStateEvidenceRequest(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        correlation_id="corr-a",
        trace_id="trace-a",
    )
    request = payload["execution"]["requestReceipt"]
    receipt = payload["execution"]["sourceReceipt"]
    assert request["snapshotMode"] == "BASELINE"
    assert request["requestedSections"] == ["portfolio_state", "portfolio_totals"]
    assert request["tenantIdHash"].startswith("sha256:")
    assert request["portfolioIdHash"].startswith("sha256:")
    assert receipt["snapshotId"] == "pss_test_snapshot"
    assert receipt["reconciliationStatus"] == "COMPLETE"
    assert receipt["appliedSections"] == ["portfolio_state", "portfolio_totals"]
    assert payload["aggregateBlockersSatisfied"] == list(
        CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS
    )
    assert payload["nonProofClaims"]["portfolioStateOwned"] == "lotus-core"
    assert all(
        value is False
        for key, value in payload["nonProofClaims"].items()
        if key != "portfolioStateOwned"
    )
    serialized = json.dumps(payload)
    assert "tenant-a" not in serialized
    assert "portfolio-a" not in serialized
    assert "corr-a" not in serialized
    assert core_portfolio_state_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("failure_mode", "expected_blocker"),
    [
        ("missing_ref", "core_portfolio_state_source_ref_missing"),
        ("stale", "core_portfolio_state_evidence_not_current"),
        ("future_source", "core_portfolio_state_source_time_invalid"),
        ("entitlement", "core_portfolio_state_entitlement_denied"),
        ("unavailable", "core_portfolio_state_evidence_unavailable"),
        ("product", "core_portfolio_state_product_identity_mismatch"),
        ("tenant", "core_portfolio_state_response_scope_mismatch"),
        ("portfolio", "core_portfolio_state_response_scope_mismatch"),
        ("simulation", "core_portfolio_state_non_baseline_snapshot"),
        ("sections", "core_portfolio_state_section_governance_mismatch"),
        ("dropped", "core_portfolio_state_section_governance_mismatch"),
        ("request_fingerprint", "core_portfolio_state_request_fingerprint_missing"),
        ("snapshot_id", "core_portfolio_state_snapshot_identity_missing"),
        ("restatement", "core_portfolio_state_restatement_version_missing"),
        ("policy", "core_portfolio_state_policy_version_missing"),
        ("hash", "core_portfolio_state_source_digest_mismatch"),
        ("reconciliation", "core_portfolio_state_reconciliation_incomplete"),
        ("quality", "core_portfolio_state_data_quality_incomplete"),
        ("source_current", "core_portfolio_state_source_current_posture_missing"),
        ("latest_evidence", "core_portfolio_state_latest_evidence_time_invalid"),
        ("correlation", "core_portfolio_state_correlation_binding_missing"),
    ],
)
def test_domain_failures_cannot_clear_aggregate_blocker(
    failure_mode: str,
    expected_blocker: str,
) -> None:
    source = RecordingSource(_evidence_for_failure(failure_mode))
    result = evaluate_core_portfolio_state_readiness(_command(), core_source=source)

    payload = build_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not core_portfolio_state_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "tamper",
    [
        "top_level",
        "execution",
        "request",
        "source",
        "request_digest",
        "source_digest",
        "tenant_binding",
        "portfolio_binding",
        "correlation_binding",
        "requested_sections",
        "applied_sections",
        "source_substitution",
        "snapshot_mode",
        "content_hash",
        "future_generated",
        "future_latest_evidence",
        "claim_inflation",
        "remaining_blockers",
        "evidence_refs",
    ],
)
def test_closed_contract_rejects_tampering(tamper: str) -> None:
    payload = _valid_payload()
    _tamper(payload, tamper)

    assert not core_portfolio_state_runtime_execution_is_valid(payload)


def test_blocked_execution_is_source_safe_and_never_qualifies() -> None:
    payload = build_blocked_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        command=_command(),
        error_code="core_source_entitlement_denied",
    )

    assert payload["execution"]["status"] == "blocked"
    assert payload["execution"]["sourceReceipt"] is None
    assert payload["aggregateBlockersSatisfied"] == []
    assert "tenant-a" not in json.dumps(payload)
    assert not core_portfolio_state_runtime_execution_is_valid(payload)


def test_command_and_builder_reject_invalid_time_or_scope() -> None:
    with pytest.raises(ValueError, match="tenant_id and portfolio_id are required"):
        replace(_command(), tenant_id=" ")
    with pytest.raises(ValueError, match="correlation_id must not be blank"):
        replace(_command(), correlation_id=" ")
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        replace(_command(), evaluated_at_utc=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_core_portfolio_state_runtime_execution(
            generated_at_utc=NOW.replace(tzinfo=None),
            result=evaluate_core_portfolio_state_readiness(
                _command(),
                core_source=RecordingSource(),
            ),
        )


def _command() -> EvaluateCorePortfolioStateReadiness:
    return EvaluateCorePortfolioStateReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=AS_OF,
        generated_at_utc=NOW - timedelta(minutes=1),
        content_hash=CONTENT_HASH,
        data_quality_status="COMPLETE",
        freshness=EvidenceFreshness.CURRENT,
    )


def _evidence() -> CorePortfolioStateEvidence:
    return CorePortfolioStateEvidence(
        portfolio_state_ref=_source_ref(),
        source_evidence_available=True,
        response_product_name="PortfolioStateSnapshot",
        response_product_version="v1",
        response_tenant_id="tenant-a",
        response_portfolio_id="portfolio-a",
        snapshot_mode="BASELINE",
        request_fingerprint="core-snapshot-request:test",
        snapshot_id="pss_test_snapshot",
        source_batch_fingerprint=CONTENT_HASH,
        response_content_hash=CONTENT_HASH,
        response_source_digest=CONTENT_HASH,
        restatement_version="restatement-v1",
        reconciliation_status="COMPLETE",
        latest_evidence_at_utc=NOW - timedelta(minutes=2),
        source_evidence_current=True,
        policy_version="tenant-policy-v1",
        source_correlation_id="corr-a",
        applied_sections=("portfolio_state", "portfolio_totals"),
        dropped_sections=(),
        portfolio_state_diagnostic="core_portfolio_state_ready",
    )


def _evidence_for_failure(failure_mode: str) -> CorePortfolioStateEvidence:
    evidence = _evidence()
    changes: dict[str, object] = {
        "missing_ref": {"portfolio_state_ref": None},
        "entitlement": {"entitlement_allowed": False},
        "unavailable": {"source_evidence_available": False},
        "product": {"response_product_name": "HoldingsAsOf"},
        "tenant": {"response_tenant_id": "tenant-b"},
        "portfolio": {"response_portfolio_id": "portfolio-b"},
        "simulation": {"snapshot_mode": "SIMULATION"},
        "sections": {"applied_sections": ("portfolio_state",)},
        "dropped": {"dropped_sections": ("portfolio_totals",)},
        "request_fingerprint": {"request_fingerprint": None},
        "snapshot_id": {"snapshot_id": None},
        "restatement": {"restatement_version": None},
        "policy": {"policy_version": None},
        "hash": {"response_source_digest": "sha256:" + "b" * 64},
        "reconciliation": {"reconciliation_status": "UNKNOWN"},
        "source_current": {"source_evidence_current": False},
        "latest_evidence": {"latest_evidence_at_utc": NOW + timedelta(seconds=1)},
        "correlation": {"source_correlation_id": "corr-b"},
    }.get(failure_mode, {})
    if changes:
        return replace(evidence, **changes)
    if failure_mode == "stale":
        return replace(
            evidence,
            portfolio_state_ref=replace(_source_ref(), freshness=EvidenceFreshness.STALE),
        )
    if failure_mode == "future_source":
        return replace(
            evidence,
            portfolio_state_ref=replace(_source_ref(), generated_at_utc=NOW + timedelta(seconds=1)),
        )
    if failure_mode == "quality":
        return replace(
            evidence,
            portfolio_state_ref=replace(_source_ref(), data_quality_status="PARTIAL"),
        )
    raise AssertionError(f"unknown failure mode: {failure_mode}")


def _valid_payload() -> dict[str, Any]:
    result = evaluate_core_portfolio_state_readiness(
        _command(),
        core_source=RecordingSource(),
    )
    return build_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )


def _tamper(payload: dict[str, Any], tamper: str) -> None:
    execution = payload["execution"]
    request = execution["requestReceipt"]
    source = execution["sourceReceipt"]
    if tamper == "top_level":
        payload["invented"] = True
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
    elif tamper == "requested_sections":
        request["requestedSections"] = ["portfolio_state"]
        _refresh_request_digest(request)
    elif tamper == "applied_sections":
        source["appliedSections"] = ["portfolio_state"]
        _refresh_source_digest(source)
    elif tamper == "source_substitution":
        source["sourceSystem"] = "lotus-risk"
        _refresh_source_digest(source)
    elif tamper == "snapshot_mode":
        source["snapshotMode"] = "SIMULATION"
        _refresh_source_digest(source)
    elif tamper == "content_hash":
        source["responseContentHash"] = "sha256:" + "b" * 64
        _refresh_source_digest(source)
    elif tamper == "future_generated":
        source["generatedAtUtc"] = "2026-06-21T10:11:00Z"
        _refresh_source_digest(source)
    elif tamper == "future_latest_evidence":
        source["latestEvidenceAtUtc"] = "2026-06-21T10:11:00Z"
        _refresh_source_digest(source)
    elif tamper == "claim_inflation":
        payload["nonProofClaims"]["rebalanceConstructed"] = True
    elif tamper == "remaining_blockers":
        payload["remainingCertificationBlockers"] = []
    elif tamper == "evidence_refs":
        payload["evidenceRefs"] = []
    else:
        raise AssertionError(f"unknown tamper: {tamper}")


def _refresh_request_digest(request: dict[str, Any]) -> None:
    request["requestDigest"] = sha256_json(
        {key: value for key, value in request.items() if key != "requestDigest"}
    )


def _refresh_source_digest(source: dict[str, Any]) -> None:
    source["receiptDigest"] = sha256_json(
        {key: value for key, value in source.items() if key != "receiptDigest"}
    )
