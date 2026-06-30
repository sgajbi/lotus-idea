from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest

from app.domain import (
    ConversionBoundary,
    ConversionTarget,
    EvidenceFreshness,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    IdeaConversionIntent,
    IdeaLifecycleStatus,
    ReasonCode,
    ReportEvidencePackPurpose,
    ReportEvidenceSourceSummary,
    SourceSystem,
)
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpAdviseProposalRealizationClient,
    HttpManageActionRealizationClient,
    HttpReportEvidencePackMaterializationClient,
)


REQUEST_TIME = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
SOURCE_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_advise_adapter_posts_source_safe_conversion_intent_envelope() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["correlation_id"] = request.headers["X-Correlation-Id"]
        captured["trace_id"] = request.headers["X-Trace-Id"]
        captured["idempotency_key"] = request.headers["Idempotency-Key"]
        captured["payload"] = request.read()
        return httpx.Response(202, json={"accepted": True})

    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
        ),
        client=downstream_json_client("https://advise.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_proposal_intent(
        conversion_intent(ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE),
        correlation_id="corr-downstream",
        trace_id="trace-downstream",
        idempotency_key="submission-idempotency-001",
    )

    assert outcome.accepted is True
    assert captured["path"] == "/advisory/idea-intake"
    assert captured["correlation_id"] == "corr-downstream"
    assert captured["trace_id"] == "trace-downstream"
    assert captured["idempotency_key"] == "submission-idempotency-001"
    payload = httpx.Response(200, content=captured["payload"]).json()
    assert payload == {
        "conversionIntentId": "conversion-001",
        "candidateId": "idea_high_cash_redacted",
        "target": "advise_proposal",
        "sourceStatus": "approved",
        "targetSourceAuthority": "lotus-advise",
        "evidencePacketId": "iep-redacted",
        "evidenceContentFingerprint": "sha256:evidence-redacted",
        "sourceSignalIds": ["signal-redacted"],
        "boundary": "intent_only",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": REQUEST_TIME.isoformat(),
        "grantsDownstreamAuthority": False,
        "producer": "lotus-idea",
        "supportabilityStatus": "not_certified",
    }
    rendered = str(payload)
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "request_body" not in rendered
    assert "response_body" not in rendered
    assert "source_route" not in rendered


def test_report_adapter_omits_source_routes_and_raw_hash_keys() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = request.read()
        return httpx.Response(202, json={"accepted": True})

    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-intake",
            source_authority=SourceSystem.LOTUS_REPORT,
        ),
        client=downstream_json_client("https://report.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_report_evidence_pack_request(report_evidence_pack())

    assert outcome.accepted is True
    payload = httpx.Response(200, content=captured["payload"]).json()
    assert payload["reportEvidencePackId"] == "report-evidence-pack-001"
    assert payload["reportSourceAuthority"] == "lotus-report"
    assert payload["renderSourceAuthority"] == "lotus-render"
    assert payload["archiveSourceAuthority"] == "lotus-archive"
    assert payload["createsRenderedOutput"] is False
    assert payload["createsArchiveRecord"] is False
    assert payload["sourceSummaries"] == [
        {
            "productId": "lotus-core:PortfolioStateSnapshot:v1",
            "sourceSystem": "lotus-core",
            "productVersion": "v1",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": SOURCE_TIME.isoformat(),
            "dataQualityStatus": "complete",
            "freshness": "current",
        }
    ]
    rendered = str(payload)
    assert "route" not in rendered.lower()
    assert "contentHash" not in rendered
    assert "content_hash" not in rendered
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered


@pytest.mark.parametrize(
    ("status_code", "failure_reason"),
    [
        (400, "downstream_rejected"),
        (403, "downstream_permission_denied"),
        (500, "downstream_unavailable"),
    ],
)
def test_downstream_http_failures_map_to_bounded_reasons(
    status_code: int,
    failure_reason: str,
) -> None:
    adapter = HttpManageActionRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://manage.example",
            submit_path="/manage/idea-intake",
            source_authority=SourceSystem.LOTUS_MANAGE,
        ),
        client=downstream_json_client(
            "https://manage.example",
            httpx.MockTransport(lambda _request: httpx.Response(status_code, json={})),
        ),
    )

    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE)
    )

    assert outcome.accepted is False
    assert outcome.failure_reason == failure_reason


def test_downstream_transport_errors_do_not_leak_raw_exception_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("raw downstream host must not leak", request=request)

    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
        ),
        client=downstream_json_client("https://advise.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_proposal_intent(
        conversion_intent(ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE)
    )

    assert outcome.accepted is False
    assert outcome.failure_reason == "downstream_unavailable"


def test_downstream_retry_exhaustion_maps_to_bounded_timeout_reason() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("raw timeout must not leak", request=request)

    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=downstream_json_client(
            "https://advise.example",
            httpx.MockTransport(handler),
            retry_max_attempts=2,
        ),
    )

    outcome = adapter.submit_proposal_intent(
        conversion_intent(ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE),
        idempotency_key="submission-idempotency-001",
    )

    assert outcome.accepted is False
    assert outcome.failure_reason == "downstream_timeout"
    assert attempts == 2


def test_downstream_adapter_rejects_wrong_conversion_target() -> None:
    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
        ),
        client=downstream_json_client(
            "https://advise.example",
            httpx.MockTransport(lambda _request: httpx.Response(202, json={})),
        ),
    )

    with pytest.raises(ValueError, match="advise_proposal"):
        adapter.submit_proposal_intent(
            conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE)
        )


@pytest.mark.parametrize(
    ("config_kwargs", "message"),
    [
        (
            {
                "base_url": "not-a-url",
                "submit_path": "/x",
                "source_authority": SourceSystem.LOTUS_ADVISE,
            },
            "absolute HTTP",
        ),
        (
            {
                "base_url": "https://advise.example",
                "submit_path": "x",
                "source_authority": SourceSystem.LOTUS_ADVISE,
            },
            "start with '/'",
        ),
        (
            {
                "base_url": "https://advise.example",
                "submit_path": "/x?debug=true",
                "source_authority": SourceSystem.LOTUS_ADVISE,
            },
            "query string",
        ),
        (
            {
                "base_url": "https://advise.example",
                "submit_path": "/x",
                "source_authority": SourceSystem.LOTUS_ADVISE,
                "timeout_seconds": 0,
            },
            "positive",
        ),
    ],
)
def test_downstream_adapter_config_rejects_invalid_values(
    config_kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match=message):
        DownstreamRealizationAdapterConfig(**config_kwargs)


def test_downstream_adapter_rejects_wrong_source_authority() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="lotus-advise"):
        HttpAdviseProposalRealizationClient(
            DownstreamRealizationAdapterConfig(
                base_url="https://manage.example",
                submit_path="/manage/idea-intake",
                source_authority=SourceSystem.LOTUS_MANAGE,
            )
        )


def downstream_json_client(
    base_url: str,
    transport: httpx.MockTransport,
    *,
    retry_max_attempts: int = 1,
) -> DownstreamJsonClient:
    return DownstreamJsonClient(
        DownstreamClientConfig(
            base_url=base_url,
            timeout_seconds=0.5,
            retry_max_attempts=retry_max_attempts,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(base_url=base_url, transport=transport),
    )


def conversion_intent(
    target: ConversionTarget,
    source_authority: SourceSystem,
) -> GovernedConversionIntent:
    return GovernedConversionIntent(
        intent=IdeaConversionIntent(
            conversion_intent_id="conversion-001",
            candidate_id="idea_high_cash_redacted",
            target=target,
            source_status=IdeaLifecycleStatus.APPROVED,
            requested_at_utc=REQUEST_TIME,
        ),
        evidence_packet_id="iep-redacted",
        evidence_content_hash="sha256:evidence-redacted",
        source_signal_ids=("signal-redacted",),
        actor_subject="advisor-redacted",
        idempotency_key="idempotency-redacted",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        target_source_authority=source_authority,
        boundary=ConversionBoundary.INTENT_ONLY,
    )


def report_evidence_pack() -> GovernedReportEvidencePack:
    return GovernedReportEvidencePack(
        report_evidence_pack_id="report-evidence-pack-001",
        conversion_intent_id="conversion-report-001",
        candidate_id="idea_high_cash_redacted",
        evidence_packet_id="iep-redacted",
        evidence_content_hash="sha256:evidence-redacted",
        source_signal_ids=("signal-redacted",),
        source_summaries=(
            ReportEvidenceSourceSummary(
                product_id="lotus-core:PortfolioStateSnapshot:v1",
                source_system=SourceSystem.LOTUS_CORE,
                product_version="v1",
                as_of_date=date(2026, 6, 21).isoformat(),
                generated_at_utc=SOURCE_TIME,
                content_hash="sha256:source-content-redacted",
                data_quality_status="complete",
                freshness=EvidenceFreshness.CURRENT.value,
            ),
        ),
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject="advisor-redacted",
        idempotency_key="idempotency-redacted",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=REQUEST_TIME,
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
    )
