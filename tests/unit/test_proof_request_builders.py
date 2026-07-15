from __future__ import annotations

from datetime import UTC, date, datetime

from scripts.proof_request_builders import (
    build_advise_policy_evaluation_evidence_request,
    build_manage_mandate_health_evidence_request,
)


AS_OF_DATE = date(2026, 6, 28)
EVALUATED_AT = datetime(2026, 6, 28, 10, 10, tzinfo=UTC)


def test_build_advise_policy_evaluation_evidence_request_preserves_source_context() -> None:
    request = build_advise_policy_evaluation_evidence_request(
        evaluation_id="advise-policy-evaluation:demo-001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-123",
        trace_id="trace-123",
    )

    assert request.evaluation_id == "advise-policy-evaluation:demo-001"
    assert request.as_of_date == AS_OF_DATE
    assert request.evaluated_at_utc == EVALUATED_AT
    assert request.correlation_id == "corr-123"
    assert request.trace_id == "trace-123"


def test_build_manage_mandate_health_evidence_request_preserves_source_context() -> None:
    request = build_manage_mandate_health_evidence_request(
        tenant_id="tenant-a",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-123",
        trace_id="trace-123",
    )

    assert request.tenant_id == "tenant-a"
    assert request.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert request.as_of_date == AS_OF_DATE
    assert request.evaluated_at_utc == EVALUATED_AT
    assert request.correlation_id == "corr-123"
    assert request.trace_id == "trace-123"
