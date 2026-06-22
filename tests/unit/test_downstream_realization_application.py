from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeConversionIntentCommand,
    RealizeReportEvidencePackCommand,
    submit_conversion_intent_to_downstream,
    submit_report_evidence_pack_to_downstream,
)
from app.domain import (
    CandidatePersistenceResult,
    ConversionIntentCommand,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    InMemoryIdeaRepository,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.ports.downstream_realization import DownstreamRealizationOutcome


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
PACK_REQUESTED_AT = datetime(2026, 6, 21, 10, 25, tzinfo=UTC)


@dataclass
class CapturingAdviseClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[GovernedConversionIntent, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None

    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        return self.outcome


@dataclass
class CapturingManageClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[GovernedConversionIntent, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None

    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        return self.outcome


@dataclass
class CapturingReportClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[GovernedReportEvidencePack, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, evidence_pack)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        return self.outcome


def test_submit_conversion_intent_routes_advise_intent_without_recording_outcome() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            correlation_id="corr-realization",
            trace_id="trace-realization",
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )

    assert result.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert result.source_authority is SourceSystem.LOTUS_ADVISE
    assert result.target is ConversionTarget.ADVISE_PROPOSAL
    assert result.records_downstream_outcome is False
    assert result.grants_downstream_authority is False
    assert result.supported_feature_promoted is False
    assert (
        advise_client.submitted[0].intent.conversion_intent_id == "conversion-advise_proposal-001"
    )
    assert advise_client.correlation_id == "corr-realization"
    assert advise_client.trace_id == "trace-realization"
    assert manage_client.submitted == ()
    assert "portfolio_id" not in str(result)
    assert "client_id" not in str(result)


def test_submit_conversion_intent_maps_downstream_rejection_to_bounded_status() -> None:
    repository = repository_with_conversion(ConversionTarget.MANAGE_REVIEW)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(
        DownstreamRealizationOutcome.rejected_by_downstream("downstream_timeout")
    )

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-manage_review-001",
            correlation_id="corr-manage-realization",
            trace_id="trace-manage-realization",
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )

    assert result.status is DownstreamRealizationStatus.REJECTED_BY_DOWNSTREAM
    assert result.source_authority is SourceSystem.LOTUS_MANAGE
    assert result.target is ConversionTarget.MANAGE_REVIEW
    assert result.downstream_failure_reason == "downstream_timeout"
    assert advise_client.submitted == ()
    assert manage_client.submitted[0].target_source_authority is SourceSystem.LOTUS_MANAGE
    assert manage_client.correlation_id == "corr-manage-realization"
    assert manage_client.trace_id == "trace-manage-realization"


def test_report_conversion_intent_requires_report_evidence_pack_request_submission() -> None:
    repository = repository_with_conversion(ConversionTarget.REPORT_EVIDENCE)

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(conversion_intent_id="conversion-report_evidence-001"),
        repository=repository,
        advise_client=CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream()),
        manage_client=CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream()),
    )

    assert result.status is DownstreamRealizationStatus.UNSUPPORTED_TARGET
    assert result.source_authority is SourceSystem.LOTUS_REPORT
    assert result.target is ConversionTarget.REPORT_EVIDENCE
    assert result.downstream_failure_reason == "report_evidence_pack_request_required"


def test_submit_report_evidence_pack_uses_report_materialization_client() -> None:
    repository = repository_with_report_pack()
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())

    result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(
            report_evidence_pack_id="report-evidence-pack-001",
            correlation_id="corr-report-realization",
            trace_id="trace-report-realization",
        ),
        repository=repository,
        report_client=report_client,
    )

    assert result.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert result.source_authority is SourceSystem.LOTUS_REPORT
    assert result.target is ConversionTarget.REPORT_EVIDENCE
    assert result.records_downstream_outcome is False
    assert report_client.submitted[0].report_evidence_pack_id == "report-evidence-pack-001"
    assert report_client.correlation_id == "corr-report-realization"
    assert report_client.trace_id == "trace-report-realization"


def test_downstream_realization_returns_not_found_without_calling_clients() -> None:
    repository = InMemoryIdeaRepository()
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())

    conversion_result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(conversion_intent_id="missing-conversion"),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )
    pack_result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(report_evidence_pack_id="missing-pack"),
        repository=repository,
        report_client=report_client,
    )

    assert conversion_result.status is DownstreamRealizationStatus.NOT_FOUND
    assert pack_result.status is DownstreamRealizationStatus.NOT_FOUND
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()
    assert report_client.submitted == ()


def repository_with_conversion(target: ConversionTarget) -> InMemoryIdeaRepository:
    repository = repository_with_candidate()
    conversion = request_conversion_intent(
        candidate(),
        ConversionIntentCommand(
            conversion_intent_id=f"conversion-{target.value}-001",
            target=target,
            actor_subject="advisor-redacted",
            idempotency_key=f"conversion-{target.value}-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
        ),
    )
    repository.record_conversion_intent(
        conversion,
        idempotency_key=f"conversion-{target.value}-request-001",
        payload={"target": target.value},
    )
    return repository


def repository_with_report_pack() -> InMemoryIdeaRepository:
    repository = repository_with_conversion(ConversionTarget.REPORT_EVIDENCE)
    record = repository.snapshot().candidate_records["idea-downstream-001"]
    evidence_pack = request_report_evidence_pack(
        record.candidate,
        record.conversion_intents[0],
        ReportEvidencePackCommand(
            report_evidence_pack_id="report-evidence-pack-001",
            purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
            actor_subject="advisor-redacted",
            idempotency_key="report-evidence-pack-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=PACK_REQUESTED_AT,
            retention_policy_ref="lotus-report:idea-evidence-retention:v1",
        ),
    )
    repository.record_report_evidence_pack(
        evidence_pack,
        idempotency_key="report-evidence-pack-request-001",
        payload={"report_evidence_pack_id": "report-evidence-pack-001"},
    )
    return repository


def repository_with_candidate() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate(),
        idempotency_key="candidate-persist-001",
        payload={"candidate_id": "idea-downstream-001"},
        actor_subject="system",
        occurred_at_utc=EVALUATED_AT,
    )
    assert isinstance(persisted, CandidatePersistenceResult)
    return repository


def candidate() -> IdeaCandidate:
    source = source_ref()
    return IdeaCandidate(
        candidate_id="idea-downstream-001",
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        evidence_packet=IdeaEvidencePacket(
            evidence_packet_id="iep-downstream-001",
            supportability=EvidenceSupportability.READY,
            source_refs=(source,),
            lineage_ref=LineageRef(
                lineage_id="lineage:lotus-idea:downstream:test",
                source_refs=(source,),
                content_hash="sha256:downstream-evidence",
            ),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
            created_at_utc=EVALUATED_AT,
        ),
        source_signal_ids=("signal-downstream-001",),
        score=IdeaScore(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("88"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
    )


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
