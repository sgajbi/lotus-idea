from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from copy import deepcopy
import hashlib
import json
from typing import Any

import pytest

from app.application.core_benchmark_assignment_runtime_evidence import (
    EvaluateCoreBenchmarkAssignmentReadiness,
    build_core_benchmark_assignment_runtime_execution,
    core_benchmark_assignment_runtime_execution_is_valid,
    evaluate_core_benchmark_assignment_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
)

NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
AS_OF = date(2026, 6, 21)


class RecordingSource:
    def __init__(self, evidence: CoreBenchmarkAssignmentEvidence | None = None) -> None:
        self.request: CoreBenchmarkAssignmentEvidenceRequest | None = None
        self.evidence = evidence or _evidence()

    def fetch_benchmark_assignment_evidence(
        self, request: CoreBenchmarkAssignmentEvidenceRequest
    ) -> CoreBenchmarkAssignmentEvidence:
        self.request = request
        return self.evidence


def test_use_case_calls_port_with_exact_scope_and_builds_receipt_bound_evidence() -> None:
    source = RecordingSource()
    command = _command()

    result = evaluate_core_benchmark_assignment_readiness(command, core_source=source)
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)

    assert source.request == CoreBenchmarkAssignmentEvidenceRequest(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr",
        trace_id="trace",
    )
    assert core_benchmark_assignment_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_benchmark_assignment_source_ref_missing"
    ]
    assert payload["nonProofClaims"]["ideaPersistenceRequired"] is False
    assert "tenant-a" not in str(payload) and "portfolio-a" not in str(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("sourceReceipt", "sourceSystem"), "lotus-performance"),
        (("sourceReceipt", "asOfDate"), "2026-06-20"),
        (("sourceReceipt", "freshness"), "stale"),
        (("requestReceipt", "portfolioIdHash"), "sha256:tampered"),
        (("requestReceipt", "reportingCurrency"), "EUR"),
    ],
)
def test_validator_rejects_source_scope_and_digest_tampering(
    path: tuple[str, str], value: object
) -> None:
    payload = _valid_payload()
    payload["execution"][path[0]][path[1]] = value
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


def test_validator_rejects_unknown_or_inflated_claims() -> None:
    unknown = _valid_payload()
    unknown["productionCertified"] = True
    inflated = _valid_payload()
    inflated["nonProofClaims"]["performanceMethodologyCertified"] = True
    assert not core_benchmark_assignment_runtime_execution_is_valid(unknown)
    assert not core_benchmark_assignment_runtime_execution_is_valid(inflated)


@pytest.mark.parametrize(
    "failure_mode",
    ["blank_tenant", "naive_evaluation_time", "invalid_currency"],
)
def test_command_rejects_invalid_scope_time_and_currency(failure_mode: str) -> None:
    with pytest.raises(ValueError):
        if failure_mode == "blank_tenant":
            replace(_command(), tenant_id="")
        elif failure_mode == "naive_evaluation_time":
            replace(_command(), evaluated_at_utc=datetime(2026, 6, 21, 10, 10))
        else:
            replace(_command(), reporting_currency="US")


def test_builder_requires_timezone_aware_generation_time() -> None:
    result = evaluate_core_benchmark_assignment_readiness(_command(), core_source=RecordingSource())
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_core_benchmark_assignment_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10), result=result
        )


@pytest.mark.parametrize(
    "failure_mode",
    ["missing_ref", "scope_mismatch", "entitlement_denied"],
)
def test_source_authority_scope_and_entitlement_fail_closed(failure_mode: str) -> None:
    evidence = _evidence()
    if failure_mode == "missing_ref":
        evidence = replace(evidence, benchmark_assignment_ref=None)
    elif failure_mode == "scope_mismatch":
        evidence = replace(
            evidence,
            benchmark_assignment_ref=replace(_source_ref(), as_of_date=date(2026, 6, 20)),
        )
    else:
        evidence = replace(evidence, entitlement_allowed=False)
    result = evaluate_core_benchmark_assignment_readiness(
        _command(), core_source=RecordingSource(evidence)
    )
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)
    assert payload["execution"]["qualificationBlockers"]
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "failure_mode",
    [
        "malformed_generated_time",
        "wrong_source_authority",
        "malformed_claims",
        "missing_source_receipt",
        "invalid_as_of_date",
        "malformed_identity_hash",
        "lowercase_currency",
        "empty_source_route",
        "empty_diagnostic",
        "wrong_aggregate_blockers",
        "wrong_remaining_blockers",
    ],
)
def test_closed_contract_rejects_malformed_receipts_and_control_fields(failure_mode: str) -> None:
    payload = _valid_payload()
    execution = payload["execution"]
    if failure_mode == "malformed_generated_time":
        payload["generatedAtUtc"] = "not-an-instant"
    elif failure_mode == "wrong_source_authority":
        payload["sourceAuthority"] = "lotus-performance"
    elif failure_mode == "malformed_claims":
        payload["nonProofClaims"] = {}
    elif failure_mode == "missing_source_receipt":
        execution["sourceReceipt"] = None
    elif failure_mode == "invalid_as_of_date":
        execution["requestReceipt"]["asOfDate"] = "not-a-date"
        _refresh_digest(execution["requestReceipt"], "requestDigest")
    elif failure_mode == "malformed_identity_hash":
        execution["requestReceipt"]["tenantIdHash"] = "not-a-sha256"
        _refresh_digest(execution["requestReceipt"], "requestDigest")
    elif failure_mode == "lowercase_currency":
        execution["requestReceipt"]["reportingCurrency"] = "usd"
        _refresh_digest(execution["requestReceipt"], "requestDigest")
    elif failure_mode == "empty_source_route":
        execution["sourceReceipt"]["route"] = ""
        _refresh_digest(execution["sourceReceipt"], "receiptDigest")
    elif failure_mode == "empty_diagnostic":
        execution["diagnosticCode"] = ""
    elif failure_mode == "wrong_aggregate_blockers":
        payload["aggregateBlockersSatisfied"] = []
    else:
        payload["remainingCertificationBlockers"] = []
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "failure_mode",
    [
        "identity_missing",
        "not_effective",
        "version_missing",
        "inactive",
        "stale",
        "future_source",
    ],
)
def test_unqualified_authoritative_evidence_cannot_clear_aggregate_blocker(
    failure_mode: str,
) -> None:
    evidence = _evidence_for_failure(failure_mode)
    result = evaluate_core_benchmark_assignment_readiness(
        _command(), core_source=RecordingSource(evidence)
    )
    payload = build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)
    assert payload["aggregateBlockersSatisfied"] == []
    assert payload["execution"]["qualificationBlockers"]
    assert not core_benchmark_assignment_runtime_execution_is_valid(payload)


def _valid_payload() -> dict[str, Any]:
    result = evaluate_core_benchmark_assignment_readiness(_command(), core_source=RecordingSource())
    return deepcopy(
        build_core_benchmark_assignment_runtime_execution(generated_at_utc=NOW, result=result)
    )


def _command() -> EvaluateCoreBenchmarkAssignmentReadiness:
    return EvaluateCoreBenchmarkAssignmentReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=AS_OF,
        evaluated_at_utc=NOW,
        reporting_currency="USD",
        correlation_id="corr",
        trace_id="trace",
    )


def _evidence() -> CoreBenchmarkAssignmentEvidence:
    return CoreBenchmarkAssignmentEvidence(
        benchmark_assignment_ref=_source_ref(),
        benchmark_identity_resolved=True,
        assignment_effective_for_as_of_date=True,
        assignment_status="active",
        assignment_version_present=True,
        assignment_diagnostic="core_benchmark_assignment_ready",
    )


def _evidence_for_failure(failure_mode: str) -> CoreBenchmarkAssignmentEvidence:
    evidence = _evidence()
    if failure_mode == "identity_missing":
        return replace(evidence, benchmark_identity_resolved=False)
    if failure_mode == "not_effective":
        return replace(evidence, assignment_effective_for_as_of_date=False)
    if failure_mode == "version_missing":
        return replace(evidence, assignment_version_present=False)
    if failure_mode == "inactive":
        return replace(evidence, assignment_status="inactive")
    if failure_mode == "stale":
        return replace(
            evidence,
            benchmark_assignment_ref=replace(_source_ref(), freshness=EvidenceFreshness.STALE),
        )
    if failure_mode == "future_source":
        return replace(
            evidence,
            benchmark_assignment_ref=replace(
                _source_ref(), generated_at_utc=NOW + timedelta(seconds=1)
            ),
        )
    raise AssertionError(f"unknown failure mode: {failure_mode}")


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:BenchmarkAssignment:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
        as_of_date=AS_OF,
        generated_at_utc=NOW,
        content_hash="sha256:source",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _refresh_digest(receipt: dict[str, Any], digest_key: str) -> None:
    material = {key: value for key, value in receipt.items() if key != digest_key}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt[digest_key] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
