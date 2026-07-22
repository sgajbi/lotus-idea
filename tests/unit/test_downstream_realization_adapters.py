from __future__ import annotations

from dataclasses import replace
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
    ReviewAccessScope,
    SourceSystem,
)
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.downstream_realization import (
    AdviseRealizationServiceContext,
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpAdviseProposalRealizationClient,
    HttpManageActionRealizationClient,
    HttpReportEvidencePackMaterializationClient,
    ManageRealizationServiceContext,
    ReportRealizationServiceContext,
)
from app.ports.downstream_realization import DownstreamRealizationOutcomePosture


REQUEST_TIME = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
SOURCE_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_advise_adapter_posts_source_safe_conversion_intent_envelope() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
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
            advise_service_context=advise_service_context(),
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
    assert captured["headers"]["x-actor-id"] == "lotus-idea-local-development"
    assert captured["headers"]["x-role"] == "SERVICE"
    assert captured["headers"]["x-tenant-id"] == "tenant-sg"
    assert captured["headers"]["x-legal-entity-code"] == "SGPB"
    assert captured["headers"]["x-service-identity"] == "lotus-idea-local-development"
    assert captured["headers"]["x-capabilities"] == "advisory.idea_proposal_intake.accept"
    assert captured["headers"]["x-principal-status"] == "ACTIVE"
    payload = httpx.Response(200, content=captured["payload"]).json()
    assert payload == {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_high_cash_redacted",
        "conversion_intent_id": "conversion-001",
        "intent_type": "REVIEW_FOR_ADVISORY_PROPOSAL",
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_high_cash_redacted",
                "content_hash": "sha256:evidence-redacted",
            }
        ],
    }
    rendered = str(payload)
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "request_body" not in rendered
    assert "response_body" not in rendered
    assert "source_route" not in rendered


def test_report_adapter_matches_owner_contract_and_omits_sensitive_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = request.read()
        return httpx.Response(202, json={"accepted": True})

    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client("https://report.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_report_evidence_pack_request(
        report_evidence_pack(),
        access_scope=report_access_scope(),
        correlation_id="corr-report",
        trace_id="trace-report",
        idempotency_key="report-submission-idempotency-001",
    )

    assert outcome.accepted is True
    payload = httpx.Response(200, content=captured["payload"]).json()
    assert payload == {
        "idea_evidence_pack": {
            "report_evidence_pack_id": "report-evidence-pack-001",
            "conversion_intent_id": "conversion-report-001",
            "candidate_id": "idea_high_cash_redacted",
            "purpose": "CLIENT_REPORT_EVIDENCE",
            "evidence_packet_id": "iep-redacted",
            "evidence_content_fingerprint": "sha256:evidence-redacted",
            "source_signal_ids": ["signal-redacted"],
            "source_summaries": [
                {
                    "product_id": "lotus-core:PortfolioStateSnapshot:v1",
                    "source_system": "lotus-core",
                    "product_version": "v1",
                    "as_of_date": "2026-06-21",
                    "generated_at_utc": SOURCE_TIME.isoformat(),
                    "data_quality_status": "complete",
                    "freshness": "current",
                }
            ],
            "reason_codes": ["review_approved_for_conversion"],
            "report_source_authority": "lotus-report",
            "render_source_authority": "lotus-render",
            "archive_source_authority": "lotus-archive",
            "boundary": "REPORT_INTAKE_ONLY",
            "retention_policy_ref": "generated-report-standard",
            "requested_at_utc": REQUEST_TIME.isoformat(),
            "grants_client_publication_authority": False,
            "creates_rendered_output": False,
            "creates_archive_record": False,
            "producer": "lotus-idea",
            "supportability_status": "not_certified",
        },
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-06-21",
        "requested_output_formats": ["json"],
        "boundary": "REPORT_JOB_MATERIALIZATION",
        "grants_client_publication_authority": False,
        "producer": "lotus-idea",
        "supportability_status": "not_certified",
    }
    assert captured["headers"]["x-actor-id"] == "lotus-idea-local-development"
    assert captured["headers"]["x-caller-application"] == "lotus-idea"
    assert captured["headers"]["x-tenant-id"] == "tenant-sg"
    assert captured["headers"]["x-region"] == "APAC"
    assert captured["headers"]["x-correlation-id"] == "corr-report"
    assert captured["headers"]["x-trace-id"] == "trace-report"
    assert "client_id" not in str(payload)
    assert "tenant_id" not in str(payload)
    assert captured["headers"]["idempotency-key"] == "report-submission-idempotency-001"
    assert payload["idea_evidence_pack"]["source_summaries"] == [
        {
            "product_id": "lotus-core:PortfolioStateSnapshot:v1",
            "source_system": "lotus-core",
            "product_version": "v1",
            "as_of_date": "2026-06-21",
            "generated_at_utc": SOURCE_TIME.isoformat(),
            "data_quality_status": "complete",
            "freshness": "current",
        }
    ]
    rendered = str(payload)
    assert "route" not in rendered.lower()
    assert "content_hash" not in rendered
    assert "client_id" not in rendered
    assert "book_id" not in rendered


@pytest.mark.parametrize(
    ("status_code", "failure_reason", "expected_posture"),
    [
        (400, "downstream_rejected", DownstreamRealizationOutcomePosture.REJECTED),
        (403, "downstream_permission_denied", DownstreamRealizationOutcomePosture.REJECTED),
        (500, "downstream_unavailable", DownstreamRealizationOutcomePosture.UNKNOWN),
    ],
)
def test_downstream_http_failures_map_to_bounded_reasons(
    status_code: int,
    failure_reason: str,
    expected_posture: DownstreamRealizationOutcomePosture,
) -> None:
    adapter = HttpManageActionRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://manage.example",
            submit_path="/manage/idea-intake",
            source_authority=SourceSystem.LOTUS_MANAGE,
            manage_service_context=manage_service_context(),
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
    assert outcome.posture is expected_posture
    assert outcome.failure_reason == failure_reason


def test_downstream_transport_errors_do_not_leak_raw_exception_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("raw downstream host must not leak", request=request)

    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        ),
        client=downstream_json_client("https://advise.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_proposal_intent(
        conversion_intent(ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE)
    )

    assert outcome.accepted is False
    assert outcome.posture is DownstreamRealizationOutcomePosture.UNKNOWN
    assert outcome.failure_reason == "downstream_unavailable"


def test_downstream_malformed_response_errors_map_to_bounded_reason() -> None:
    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
        ),
        client=downstream_json_client(
            "https://advise.example",
            httpx.MockTransport(lambda _request: httpx.Response(202, content=b"not-json")),
        ),
    )

    outcome = adapter.submit_proposal_intent(
        conversion_intent(ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE)
    )

    assert outcome.accepted is False
    assert outcome.posture is DownstreamRealizationOutcomePosture.UNKNOWN
    assert outcome.failure_reason == "downstream_malformed_response"


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
            advise_service_context=advise_service_context(),
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
    assert outcome.posture is DownstreamRealizationOutcomePosture.UNKNOWN
    assert outcome.failure_reason == "downstream_timeout"
    assert attempts == 2


def test_downstream_adapter_rejects_wrong_conversion_target() -> None:
    adapter = HttpAdviseProposalRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://advise.example",
            submit_path="/advisory/idea-intake",
            source_authority=SourceSystem.LOTUS_ADVISE,
            advise_service_context=advise_service_context(),
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


def test_conversion_envelope_rejects_non_intake_target() -> None:
    from app.infrastructure.downstream_realization import _conversion_intent_envelope

    with pytest.raises(ValueError, match="unsupported conversion target"):
        _conversion_intent_envelope(
            conversion_intent(ConversionTarget.REPORT_EVIDENCE, SourceSystem.LOTUS_REPORT)
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
                manage_service_context=manage_service_context(),
            )
        )


def test_manage_adapter_posts_owner_contract_payload_and_server_context() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = request.read()
        return httpx.Response(202, json={"accepted": True})

    adapter = HttpManageActionRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://manage.example",
            submit_path="/api/v1/rebalance/idea-action-intake",
            source_authority=SourceSystem.LOTUS_MANAGE,
            manage_service_context=manage_service_context(),
        ),
        client=downstream_json_client("https://manage.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
        correlation_id="corr-downstream",
        trace_id="trace-downstream",
        idempotency_key="submission-idempotency-001",
    )

    assert outcome.accepted is True
    assert httpx.Response(200, content=captured["payload"]).json() == {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_high_cash_redacted",
        "conversion_intent_id": "conversion-001",
        "intent_type": "REVIEW_FOR_REBALANCE",
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_high_cash_redacted",
                "content_hash": "sha256:evidence-redacted",
            }
        ],
    }
    assert captured["headers"]["x-actor-id"] == "lotus-idea-local-development"
    assert captured["headers"]["x-role"] == "service"
    assert captured["headers"]["x-tenant-id"] == "local-development"
    assert captured["headers"]["x-service-identity"] == "lotus-idea-local-development"
    assert captured["headers"]["x-capabilities"] == "manage.write"
    assert captured["headers"]["x-correlation-id"] == "corr-downstream"
    assert captured["headers"]["x-trace-id"] == "trace-downstream"
    assert captured["headers"]["idempotency-key"] == "submission-idempotency-001"


def test_manage_adapter_requires_server_context() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="service context"):
        HttpManageActionRealizationClient(
            DownstreamRealizationAdapterConfig(
                base_url="https://manage.example",
                submit_path="/api/v1/rebalance/idea-action-intake",
                source_authority=SourceSystem.LOTUS_MANAGE,
            )
        )


def test_advise_adapter_requires_server_context() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="service context"):
        HttpAdviseProposalRealizationClient(
            DownstreamRealizationAdapterConfig(
                base_url="https://advise.example",
                submit_path="/advisory/proposals/idea-intake",
                source_authority=SourceSystem.LOTUS_ADVISE,
            )
        )


def test_report_adapter_requires_server_context() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="service context"):
        HttpReportEvidencePackMaterializationClient(
            DownstreamRealizationAdapterConfig(
                base_url="https://report.example",
                submit_path="/reports/idea-evidence-packs/materializations",
                source_authority=SourceSystem.LOTUS_REPORT,
            )
        )


def test_report_adapter_rejects_candidate_tenant_mismatch_before_http_call() -> None:
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(
                lambda _request: pytest.fail("Report must not receive mismatched tenant scope")
            ),
        ),
    )

    with pytest.raises(DownstreamRealizationConfigurationError, match="tenant does not match"):
        adapter.submit_report_evidence_pack_request(
            report_evidence_pack(),
            access_scope=replace(report_access_scope(), tenant_id="tenant-other"),
        )


def test_report_adapter_rejects_inconsistent_source_dates_before_http_call() -> None:
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(
                lambda _request: pytest.fail("Report must not receive inconsistent source dates")
            ),
        ),
    )
    evidence_pack = replace(
        report_evidence_pack(),
        source_summaries=(
            *report_evidence_pack().source_summaries,
            replace(report_evidence_pack().source_summaries[0], as_of_date="2026-06-22"),
        ),
    )

    with pytest.raises(
        DownstreamRealizationConfigurationError, match="consistent source as_of_date"
    ):
        adapter.submit_report_evidence_pack_request(
            evidence_pack,
            access_scope=report_access_scope(),
        )


def test_report_adapter_rejects_malformed_source_date_before_http_call() -> None:
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(
                lambda _request: pytest.fail("Report must not receive a malformed source date")
            ),
        ),
    )
    evidence_pack = replace(
        report_evidence_pack(),
        source_summaries=(
            replace(report_evidence_pack().source_summaries[0], as_of_date="not-an-iso-date"),
        ),
    )

    with pytest.raises(DownstreamRealizationConfigurationError, match="must be ISO-8601"):
        adapter.submit_report_evidence_pack_request(
            evidence_pack,
            access_scope=report_access_scope(),
        )


def test_report_service_context_rejects_blank_required_values() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="actor_id is required"):
        ReportRealizationServiceContext(
            actor_id=" ",
            caller_application="lotus-idea",
            tenant_id="local-development",
            region="local",
            requested_output_formats=("json",),
        )


def test_advise_service_context_rejects_blank_required_values() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="actor_id is required"):
        AdviseRealizationServiceContext(
            actor_id=" ",
            role="SERVICE",
            tenant_id="tenant-sg",
            legal_entity_code="SGPB",
            service_identity="lotus-idea-local-development",
            capabilities="advisory.idea_proposal_intake.accept",
        )


def test_manage_service_context_rejects_blank_required_values() -> None:
    with pytest.raises(DownstreamRealizationConfigurationError, match="actor_id is required"):
        ManageRealizationServiceContext(
            actor_id=" ",
            role="service",
            tenant_id="local-development",
            service_identity="lotus-idea-local-development",
            capabilities="manage.write",
        )


def test_report_service_context_requires_output_formats() -> None:
    with pytest.raises(
        DownstreamRealizationConfigurationError,
        match="requested_output_formats is required",
    ):
        ReportRealizationServiceContext(
            actor_id="lotus-idea-local-development",
            caller_application="lotus-idea",
            tenant_id="tenant-sg",
            region="APAC",
            requested_output_formats=(),
        )


def test_report_service_context_rejects_blank_output_formats() -> None:
    with pytest.raises(
        DownstreamRealizationConfigurationError,
        match="requested_output_formats cannot contain blanks",
    ):
        ReportRealizationServiceContext(
            actor_id="lotus-idea-local-development",
            caller_application="lotus-idea",
            tenant_id="tenant-sg",
            region="APAC",
            requested_output_formats=("json", " "),
        )


@pytest.mark.parametrize(
    ("purpose", "expected_intake_purpose"),
    [
        (ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION, "CLIENT_REPORT_EVIDENCE"),
        (ReportEvidencePackPurpose.ADVISOR_REVIEW_EVIDENCE, "ADVISOR_REVIEW_APPENDIX"),
        (ReportEvidencePackPurpose.AUDIT_EVIDENCE, "ADVISOR_REVIEW_APPENDIX"),
    ],
)
def test_report_adapter_maps_governed_purpose_to_owner_vocabulary(
    purpose: ReportEvidencePackPurpose,
    expected_intake_purpose: str,
) -> None:
    from app.infrastructure.downstream_realization import _report_evidence_pack_envelope

    payload = _report_evidence_pack_envelope(replace(report_evidence_pack(), purpose=purpose))

    assert payload["purpose"] == expected_intake_purpose


def test_report_adapter_fails_closed_when_owner_retention_policy_mapping_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure import downstream_realization

    monkeypatch.delitem(
        downstream_realization._REPORT_OWNER_RETENTION_POLICY_BY_IDEA_REFERENCE,
        "lotus-report:idea-evidence-retention:v1",
    )
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(
                lambda _request: pytest.fail("Report must not be called without a policy mapping")
            ),
        ),
    )

    with pytest.raises(DownstreamRealizationConfigurationError, match="not mapped"):
        adapter.submit_report_evidence_pack_request(
            report_evidence_pack(),
            access_scope=report_access_scope(),
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


def manage_service_context() -> ManageRealizationServiceContext:
    return ManageRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        role="service",
        tenant_id="local-development",
        service_identity="lotus-idea-local-development",
        capabilities="manage.write",
    )


def advise_service_context() -> AdviseRealizationServiceContext:
    return AdviseRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        role="SERVICE",
        tenant_id="tenant-sg",
        legal_entity_code="SGPB",
        service_identity="lotus-idea-local-development",
        capabilities="advisory.idea_proposal_intake.accept",
    )


def report_service_context() -> ReportRealizationServiceContext:
    return ReportRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        caller_application="lotus-idea",
        tenant_id="tenant-sg",
        region="APAC",
        requested_output_formats=("json",),
    )


def report_access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-sg",
        book_id="book-private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-redacted",
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
