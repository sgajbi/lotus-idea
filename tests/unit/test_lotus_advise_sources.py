from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

import httpx
import pytest

from app.domain import EvidenceFreshness
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.lotus_advise_sources import LotusAdvisePolicyEvaluationSourceAdapter
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def _payload(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evaluation_id": "pev_001",
        "proposal_id": "pp_001",
        "proposal_version_id": "ppv_001",
        "evaluation_status": "PENDING_REVIEW",
        "approval_dependencies": [
            {
                "requirement_id": "approval:structured-note",
                "requirement_type": "approval",
                "status": "OPEN",
                "owner_role": "INVESTMENT_COUNSELLOR",
                "reason_codes": ["POLICY_REQUIREMENT_OPEN"],
            }
        ],
        "disclosure_requirements": [
            {
                "requirement_id": "disclosure:structured-note",
                "requirement_type": "disclosure",
                "status": "BLOCKED",
                "owner_role": "ADVISOR",
                "reason_codes": ["DISCLOSURE_REQUIRED"],
            }
        ],
        "consent_requirements": [],
        "conflict_posture": {"status": "PENDING_REVIEW"},
        "sla_posture": {"status": "WITHIN_SLA", "open_requirement_count": 2},
        "sign_off_status": "PENDING_REVIEW",
        "sign_off_blockers": ["DISCLOSURE_REQUIREMENT_OPEN:structured-note"],
        "maker_checker_required": True,
        "latest_sign_off_event": None,
        "client_ready_publication": "BLOCKED",
        "metadata": {
            "product_id": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "product_version": "v1",
            "evaluation_id": "pev_001",
            "tenant_scope_hash": "sha256:tenant-scope",
            "portfolio_id": "portfolio-001",
            "correlation_id": "corr-advise",
            "trace_id": "trace-advise",
            "generated_at": "2026-06-21T10:00:00Z",
            "as_of_date": "2026-06-21",
            "content_hash": "sha256:advisory-policy-evaluation-record",
            "source_evidence_hash": "sha256:source-evidence",
            "policy_content_hash": "sha256:policy-content",
            "policy_pack_id": "global-mandate-restrictions",
            "policy_version": "2026.06",
            "data_quality_status": "quality_passed",
            "freshness": "current",
        },
    }
    if extra:
        payload.update(extra)
    return payload


def _adapter(handler: httpx.MockTransport) -> LotusAdvisePolicyEvaluationSourceAdapter:
    return LotusAdvisePolicyEvaluationSourceAdapter(
        DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://advise.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://advise.example", transport=handler),
        )
    )


def _request(evaluation_id: str = "pev_001") -> AdvisePolicyEvaluationEvidenceRequest:
    return AdvisePolicyEvaluationEvidenceRequest(
        evaluation_id=evaluation_id,
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


@pytest.mark.parametrize(
    "changes",
    (
        {"evaluation_id": " "},
        {"evaluated_at_utc": EVALUATED_AT.replace(tzinfo=None)},
    ),
)
def test_advise_evidence_request_rejects_invalid_identity_or_time(
    changes: dict[str, Any],
) -> None:
    values: dict[str, Any] = {
        "evaluation_id": "pev_001",
        "as_of_date": AS_OF_DATE,
        "evaluated_at_utc": EVALUATED_AT,
    }
    values.update(changes)

    with pytest.raises(ValueError):
        AdvisePolicyEvaluationEvidenceRequest(**values)


def test_lotus_advise_adapter_fetches_declared_policy_evaluation_source_product() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.headers["X-Correlation-Id"] == "corr-advise"
        assert request.headers["X-Trace-Id"] == "trace-advise"
        return httpx.Response(200, json=_payload())

    evidence = _adapter(httpx.MockTransport(handler)).fetch_policy_evaluation_evidence(_request())

    assert evidence.evaluation_status == "PENDING_REVIEW"
    assert evidence.open_requirement_count == 2
    assert evidence.blocked_requirement_count == 1
    assert evidence.sign_off_status == "PENDING_REVIEW"
    assert evidence.sign_off_blocker_count == 1
    assert evidence.client_ready_publication == "BLOCKED"
    assert evidence.policy_ref is not None
    assert evidence.policy_ref.product_id == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    assert evidence.policy_ref.route == "/advisory/policy-evaluations/pev_001/workflow"
    assert evidence.policy_ref.freshness is EvidenceFreshness.CURRENT
    assert evidence.policy_ref.content_hash == "sha256:advisory-policy-evaluation-record"
    assert evidence.workflow_runtime is not None
    assert evidence.workflow_runtime.evaluation_id == "pev_001"
    assert evidence.workflow_runtime.portfolio_id == "portfolio-001"
    assert evidence.workflow_runtime.tenant_scope_hash == "sha256:tenant-scope"
    assert evidence.workflow_runtime.correlation_id == "corr-advise"
    assert evidence.workflow_runtime.trace_id == "trace-advise"
    assert evidence.workflow_runtime.open_requirement_count == 2
    assert evidence.advise_diagnostic == "advise_policy_requirements_open"
    assert seen == [
        (
            "GET",
            "https://advise.example/advisory/policy-evaluations/pev_001/workflow",
        )
    ]


def test_lotus_advise_adapter_url_encodes_evaluation_id() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=_payload())

    _adapter(httpx.MockTransport(handler)).fetch_policy_evaluation_evidence(
        _request("pev /needs encoding")
    )

    assert seen == [
        "https://advise.example/advisory/policy-evaluations/pev%20%2Fneeds%20encoding/workflow"
    ]


def test_lotus_advise_adapter_prefers_source_declared_diagnostic() -> None:
    payload = _payload(extra={"diagnostic_codes": ["mandate_restriction_review_required"]})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.advise_diagnostic == "mandate_restriction_review_required"


def test_lotus_advise_adapter_accepts_direct_source_diagnostic() -> None:
    payload = _payload(extra={"source_diagnostic": " mandate_restriction_review_required "})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.advise_diagnostic == "mandate_restriction_review_required"


def test_lotus_advise_adapter_maps_forbidden_source_response_to_entitlement_denied() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(403, json={})))

    with pytest.raises(AdviseSourceEntitlementDenied):
        adapter.fetch_policy_evaluation_evidence(_request())


def test_lotus_advise_adapter_maps_server_error_to_source_unavailable() -> None:
    adapter = _adapter(httpx.MockTransport(lambda request: httpx.Response(503, json={})))

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        adapter.fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == "upstream_unavailable"


def test_lotus_advise_adapter_maps_malformed_requirements_to_source_unavailable() -> None:
    payload = _payload(extra={"approval_dependencies": "not-list"})

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == "advise_approval_dependencies_malformed"


def test_lotus_advise_adapter_ignores_requirement_without_a_status() -> None:
    payload = _payload(extra={"approval_dependencies": [{"requirement_id": "approval:missing"}]})

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.blocked_requirement_count == 1


def test_lotus_advise_adapter_maps_malformed_sign_off_blockers_to_source_unavailable() -> None:
    payload = _payload(extra={"sign_off_blockers": ["valid", 123]})

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == "advise_sign_off_blockers_malformed"


@pytest.mark.parametrize(
    ("sla_posture", "expected_code"),
    [
        ({"open_requirement_count": True}, "advise_open_requirement_count_malformed"),
        ({"open_requirement_count": -1}, "advise_open_requirement_count_malformed"),
        ("not-object", "advise_sla_posture_malformed"),
    ],
)
def test_lotus_advise_adapter_rejects_malformed_sla_posture(
    sla_posture: object,
    expected_code: str,
) -> None:
    payload = _payload(extra={"sla_posture": sla_posture})

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == expected_code


def test_lotus_advise_adapter_preserves_missing_generated_at_as_unqualified_evidence() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("generated_at")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.policy_ref is None
    assert evidence.workflow_runtime is not None
    assert evidence.workflow_runtime.generated_at_utc is None


def test_lotus_advise_adapter_rejects_malformed_metadata_object() -> None:
    payload = _payload(extra={"metadata": "not-object"})

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == "advise_metadata_malformed"


def test_lotus_advise_adapter_rejects_naive_generated_at_metadata() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["generated_at"] = "2026-06-21T10:00:00"

    with pytest.raises(AdviseSourceUnavailable) as exc_info:
        _adapter(
            httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ).fetch_policy_evaluation_evidence(_request())

    assert exc_info.value.code == "advise_generated_at_naive"


def test_lotus_advise_adapter_preserves_missing_content_hash_as_unqualified_evidence() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("content_hash")

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.policy_ref is None
    assert evidence.workflow_runtime is not None
    assert evidence.workflow_runtime.content_hash is None


def test_lotus_advise_adapter_maps_stale_policy_source() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["freshness"] = "stale"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.policy_ref is not None
    assert evidence.policy_ref.freshness is EvidenceFreshness.STALE


@pytest.mark.parametrize(
    ("freshness_value", "expected"),
    [
        ("expired", EvidenceFreshness.EXPIRED),
        ("unavailable", EvidenceFreshness.UNAVAILABLE),
    ],
)
def test_lotus_advise_adapter_maps_non_current_policy_source_freshness(
    freshness_value: str,
    expected: EvidenceFreshness,
) -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["freshness"] = freshness_value

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.policy_ref is not None
    assert evidence.policy_ref.freshness is expected


def test_lotus_advise_adapter_maps_unknown_freshness_to_unavailable() -> None:
    payload = _payload()
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["freshness"] = "producer-specific-state"

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.policy_ref is not None
    assert evidence.policy_ref.freshness is EvidenceFreshness.UNAVAILABLE


def test_lotus_advise_adapter_does_not_substitute_request_as_of_for_missing_source_time() -> None:
    payload = _payload(
        extra={
            "approval_dependencies": [],
            "disclosure_requirements": [],
            "consent_requirements": [],
            "evaluation_status": "  ",
            "sign_off_status": "  ",
            "sign_off_blockers": [],
            "client_ready_publication": "BLOCKED",
            "sla_posture": {},
            "metadata": {
                "generated_at": "2026-06-21T10:00:00Z",
                "content_hash": "fallback-hash",
            },
        }
    )

    evidence = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert evidence.evaluation_status is None
    assert evidence.sign_off_status is None
    assert evidence.open_requirement_count == 0
    assert evidence.policy_ref is None
    assert evidence.workflow_runtime is not None
    assert evidence.workflow_runtime.as_of_date is None
    assert evidence.workflow_runtime.content_hash == "sha256:fallback-hash"
    assert evidence.workflow_runtime.data_quality_status == "unknown"
    assert evidence.workflow_runtime.freshness == EvidenceFreshness.UNAVAILABLE.value
    assert evidence.advise_diagnostic == "advise_policy_evaluation_source_partial"


def test_lotus_advise_adapter_distinguishes_sign_off_and_available_diagnostics() -> None:
    sign_off_blocked_payload = _payload(
        extra={
            "approval_dependencies": [],
            "disclosure_requirements": [],
            "consent_requirements": [],
            "evaluation_status": "READY",
            "sign_off_status": "PENDING_REVIEW",
            "sign_off_blockers": ["DISCLOSURE_PENDING"],
            "sla_posture": {"open_requirement_count": 0},
        }
    )
    available_payload = _payload(
        extra={
            "approval_dependencies": [],
            "disclosure_requirements": [],
            "consent_requirements": [],
            "evaluation_status": "READY",
            "sign_off_status": "SIGNED_OFF",
            "sign_off_blockers": [],
            "sla_posture": {"open_requirement_count": 0},
        }
    )

    sign_off_blocked = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=sign_off_blocked_payload))
    ).fetch_policy_evaluation_evidence(_request())
    available = _adapter(
        httpx.MockTransport(lambda request: httpx.Response(200, json=available_payload))
    ).fetch_policy_evaluation_evidence(_request())

    assert sign_off_blocked.advise_diagnostic == "advise_policy_sign_off_blocked"
    assert available.advise_diagnostic == "advise_policy_context_available"


def test_lotus_advise_adapter_close_releases_owned_client() -> None:
    class CloseAwareClient:
        closed = False

        def close(self) -> None:
            self.closed = True

    client = CloseAwareClient()
    adapter = LotusAdvisePolicyEvaluationSourceAdapter(cast(DownstreamJsonClient, client))

    adapter.close()

    assert client.closed is True
