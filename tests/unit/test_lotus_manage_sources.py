from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_manage_sources import LotusManageMandateHealthSourceAdapter
from app.ports.manage_sources import (
    ManageMandateHealthEvidenceRequest,
    ManageSourceEntitlementDenied,
    ManageSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "store_backend": "INMEMORY",
        "retention_days": 7,
        "run_count": 1,
        "operation_count": 1,
        "operation_status_counts": {"PENDING": 1},
        "run_status_counts": {"READY": 1},
        "workflow_decision_count": 2,
        "workflow_action_counts": {"APPROVE": 2},
        "workflow_reason_code_counts": {"REVIEW_APPROVED": 2},
        "lineage_edge_count": 4,
        "newest_run_created_at": "2026-06-21T10:00:00+00:00",
        "newest_operation_created_at": "2026-06-21T10:00:00+00:00",
        "supportability": {
            "state": "ready",
            "reason": "supportability_summary_ready",
            "freshness_bucket": "current",
            "run_count": 1,
            "operation_count": 1,
            "workflow_decision_count": 2,
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusManageMandateHealthSourceAdapter:
    return LotusManageMandateHealthSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://manage.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://manage.example", transport=handler),
        )
    )


def _request() -> ManageMandateHealthEvidenceRequest:
    return ManageMandateHealthEvidenceRequest(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-manage",
        trace_id="trace-manage",
    )


def test_lotus_manage_adapter_fetches_declared_action_register_source_product() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-manage"
        assert request.headers["X-Trace-Id"] == "trace-manage"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_mandate_health_evidence(_request())

    assert evidence.workflow_decision_count == 2
    assert evidence.lineage_edge_count == 4
    assert evidence.supportability_state == "ready"
    assert evidence.supportability_reason == "supportability_summary_ready"
    assert evidence.freshness_bucket == "current"
    assert evidence.portfolio_scope_confirmed is False
    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.product_id == "lotus-manage:PortfolioActionRegister:v1"
    assert evidence.action_register_ref.route == "/api/v1/rebalance/supportability/summary"
    assert evidence.action_register_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.action_register_ref.content_hash.startswith("sha256:")
    assert evidence.manage_diagnostic == "manage_action_register_ready_store_wide_scope"
    assert seen == [
        (
            "GET",
            "https://manage.example/api/v1/rebalance/supportability/summary",
        )
    ]


def test_lotus_manage_adapter_recognizes_future_portfolio_scoped_evidence() -> None:
    evidence = _adapter(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_payload(extra={"portfolio_id": "PB_SG_GLOBAL_BAL_001"}),
            )
        )
    ).fetch_mandate_health_evidence(_request())

    assert evidence.portfolio_scope_confirmed is True
    assert evidence.manage_diagnostic == "manage_action_register_ready_portfolio_scope"


def test_lotus_manage_adapter_recognizes_supportability_scoped_portfolio_evidence() -> None:
    payload = _payload()
    supportability = payload["supportability"]
    assert isinstance(supportability, dict)
    supportability["portfolioId"] = "PB_SG_GLOBAL_BAL_001"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.portfolio_scope_confirmed is True


def test_lotus_manage_adapter_recognizes_explicit_portfolio_scope_flag() -> None:
    evidence = _adapter(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_payload(extra={"portfolio_scope_confirmed": True}),
            )
        )
    ).fetch_mandate_health_evidence(_request())

    assert evidence.portfolio_scope_confirmed is True


def test_lotus_manage_adapter_preserves_mandate_health_source_refs() -> None:
    payload = _payload(
        extra={
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "sourceRefs": [
                {
                    "productId": "lotus-performance:MandatePerformanceHealthContext:v1",
                    "productVersion": "v1",
                    "route": "/performance/mandate-health-context",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:mandate-performance-health",
                    "dataQualityStatus": "ready",
                    "freshness": "current",
                },
                {
                    "productId": "lotus-risk:MandateRiskHealthContext:v1",
                    "productVersion": "v1",
                    "route": "/analytics/risk/mandate-health-context",
                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                    "contentHash": "sha256:mandate-risk-health",
                    "dataQualityStatus": "attention",
                    "freshness": "same_day",
                },
            ],
        }
    )

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.mandate_performance_health_ref is not None
    assert (
        evidence.mandate_performance_health_ref.product_id
        == "lotus-performance:MandatePerformanceHealthContext:v1"
    )
    assert evidence.mandate_performance_health_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.mandate_performance_health_ref.content_hash == (
        "sha256:mandate-performance-health"
    )
    assert evidence.mandate_risk_health_ref is not None
    assert evidence.mandate_risk_health_ref.product_id == "lotus-risk:MandateRiskHealthContext:v1"
    assert evidence.mandate_risk_health_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.mandate_risk_health_ref.data_quality_status == "attention"


def test_lotus_manage_adapter_accepts_nested_mandate_health_refs() -> None:
    payload = _payload()
    supportability = payload["supportability"]
    assert isinstance(supportability, dict)
    supportability["mandatePerformanceHealthRef"] = {
        "content_hash": "sha256:performance-nested",
        "health_state": "ready",
        "freshness_bucket": "current",
    }
    supportability["mandateRiskHealthRef"] = {
        "content_hash": "sha256:risk-nested",
        "health_state": "unavailable",
    }

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.mandate_performance_health_ref is not None
    assert (
        evidence.mandate_performance_health_ref.product_id
        == "lotus-performance:MandatePerformanceHealthContext:v1"
    )
    assert evidence.mandate_performance_health_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.mandate_risk_health_ref is not None
    assert evidence.mandate_risk_health_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_manage_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(ManageSourceEntitlementDenied):
        adapter.fetch_mandate_health_evidence(_request())


def test_lotus_manage_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(ManageSourceUnavailable) as exc_info:
        adapter.fetch_mandate_health_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_manage_adapter_accepts_missing_supportability_as_unknown_unavailable() -> None:
    payload = _payload()
    payload.pop("supportability")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.supportability_state is None
    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.data_quality_status == "unknown"
    assert evidence.action_register_ref.freshness is EvidenceFreshness.UNAVAILABLE
    assert evidence.manage_diagnostic == "manage_action_register_unknown_store_wide_scope"


def test_lotus_manage_adapter_maps_malformed_supportability_to_source_unavailable() -> None:
    payload = _payload(extra={"supportability": "not-object"})

    with pytest.raises(ManageSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_mandate_health_evidence(_request())

    assert exc_info.value.code == "manage_supportability_malformed"


def test_lotus_manage_adapter_maps_missing_counts_to_source_unavailable() -> None:
    payload = _payload()
    payload.pop("workflow_decision_count")

    with pytest.raises(ManageSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_mandate_health_evidence(_request())

    assert exc_info.value.code == "manage_workflow_decision_count_malformed"


def test_lotus_manage_adapter_maps_bool_count_to_source_unavailable() -> None:
    payload = _payload(extra={"workflow_decision_count": True})

    with pytest.raises(ManageSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_mandate_health_evidence(_request())

    assert exc_info.value.code == "manage_workflow_decision_count_malformed"


def test_lotus_manage_adapter_maps_negative_lineage_count_to_source_unavailable() -> None:
    payload = _payload(extra={"lineage_edge_count": -1})

    with pytest.raises(ManageSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_mandate_health_evidence(_request())

    assert exc_info.value.code == "manage_lineage_edge_count_malformed"


def test_lotus_manage_adapter_maps_stale_supportability_freshness() -> None:
    payload = _payload()
    supportability = payload["supportability"]
    assert isinstance(supportability, dict)
    supportability["freshness_bucket"] = "stale"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.freshness is EvidenceFreshness.STALE


def test_lotus_manage_adapter_accepts_same_day_freshness_bucket_as_current() -> None:
    payload = _payload()
    supportability = payload["supportability"]
    assert isinstance(supportability, dict)
    supportability["freshness_bucket"] = "same_day"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.freshness is EvidenceFreshness.CURRENT


def test_lotus_manage_adapter_uses_source_metadata_when_present() -> None:
    payload = _payload(
        extra={
            "generated_at": "2026-06-21T10:00:00Z",
            "source_batch_fingerprint": "manage-batch",
        }
    )

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.generated_at_utc == EVALUATED_AT
    assert evidence.action_register_ref.content_hash == "sha256:manage-batch"


def test_lotus_manage_adapter_normalizes_naive_source_timestamp() -> None:
    payload = _payload(extra={"generated_at": "2026-06-21T10:00:00"})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.generated_at_utc == EVALUATED_AT


def test_lotus_manage_adapter_uses_request_time_when_source_timestamps_are_absent() -> None:
    payload = _payload()
    payload.pop("newest_run_created_at")
    payload.pop("newest_operation_created_at")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.generated_at_utc == EVALUATED_AT


def test_lotus_manage_adapter_preserves_prefixed_source_fingerprint() -> None:
    payload = _payload(extra={"lineageFingerprint": "sha256:manage-lineage"})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.content_hash == "sha256:manage-lineage"


def test_lotus_manage_adapter_treats_ready_without_freshness_bucket_as_current() -> None:
    payload = _payload()
    supportability = payload["supportability"]
    assert isinstance(supportability, dict)
    supportability.pop("freshness_bucket")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_mandate_health_evidence(_request())

    assert evidence.action_register_ref is not None
    assert evidence.action_register_ref.freshness is EvidenceFreshness.CURRENT


def test_manage_mandate_health_evidence_request_requires_portfolio_id() -> None:
    with pytest.raises(ValueError, match="portfolio_id is required"):
        ManageMandateHealthEvidenceRequest(
            portfolio_id=" ",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=EVALUATED_AT,
        )


def test_manage_mandate_health_evidence_request_requires_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        ManageMandateHealthEvidenceRequest(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=AS_OF_DATE,
            evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
        )
