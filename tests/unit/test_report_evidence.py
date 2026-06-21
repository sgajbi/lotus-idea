from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    ConversionTarget,
    ConversionIntentResult,
    EvidenceFreshness,
    EvidenceSupportability,
    GovernedReportEvidencePack,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReportEvidencePackBoundary,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReportEvidenceSourceSummary,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.domain.conversion_governance import ConversionIntentCommand
from app.domain.report_evidence import InvalidReportEvidencePack


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
PACK_REQUESTED_AT = datetime(2026, 6, 21, 10, 25, tzinfo=UTC)


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


def candidate() -> IdeaCandidate:
    source = source_ref()
    return IdeaCandidate(
        candidate_id="idea-report-evidence-001",
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        evidence_packet=IdeaEvidencePacket(
            evidence_packet_id="iep_report_evidence_test",
            supportability=EvidenceSupportability.READY,
            source_refs=(source,),
            lineage_ref=LineageRef(
                lineage_id="lineage:lotus-idea:report-evidence:test",
                source_refs=(source,),
                content_hash="sha256:report-evidence-lineage",
            ),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
            created_at_utc=EVALUATED_AT,
        ),
        source_signal_ids=("signal-report-evidence-001",),
        score=IdeaScore(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("88"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
    )


def report_conversion_intent(candidate_: IdeaCandidate) -> ConversionIntentResult:
    return request_conversion_intent(
        candidate_,
        ConversionIntentCommand(
            conversion_intent_id="conversion-report-evidence-001",
            target=ConversionTarget.REPORT_EVIDENCE,
            actor_subject="advisor-001",
            idempotency_key="conversion-report-evidence-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
        ),
    )


def command(
    *,
    client_ready_publication_requested: bool = False,
) -> ReportEvidencePackCommand:
    return ReportEvidencePackCommand(
        report_evidence_pack_id="report-evidence-pack-001",
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject="advisor-001",
        idempotency_key="report-evidence-pack-request-001",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=PACK_REQUESTED_AT,
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
        client_ready_publication_requested=client_ready_publication_requested,
    )


def test_report_evidence_pack_requires_report_conversion_intent_and_preserves_authorities() -> None:
    conversion = report_conversion_intent(candidate())

    result = request_report_evidence_pack(
        conversion.candidate,
        conversion.conversion_intent,
        command(),
    )

    evidence_pack = result.evidence_pack
    assert evidence_pack.conversion_intent_id == "conversion-report-evidence-001"
    assert evidence_pack.candidate_id == "idea-report-evidence-001"
    assert evidence_pack.report_source_authority is SourceSystem.LOTUS_REPORT
    assert evidence_pack.render_source_authority is SourceSystem.LOTUS_RENDER
    assert evidence_pack.archive_source_authority is SourceSystem.LOTUS_ARCHIVE
    assert evidence_pack.boundary is ReportEvidencePackBoundary.REQUEST_ONLY
    assert evidence_pack.grants_client_publication_authority is False
    assert evidence_pack.creates_rendered_output is False
    assert evidence_pack.creates_archive_record is False
    assert evidence_pack.source_summaries[0].product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert result.audit_event.event_type == "idea.report_evidence_pack.requested"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes


def test_report_evidence_pack_blocks_client_ready_publication_and_non_report_targets() -> None:
    conversion = report_conversion_intent(candidate())

    with pytest.raises(InvalidReportEvidencePack, match="client-ready publication"):
        request_report_evidence_pack(
            conversion.candidate,
            conversion.conversion_intent,
            command(client_ready_publication_requested=True),
        )

    advise_conversion = request_conversion_intent(
        candidate(),
        ConversionIntentCommand(
            conversion_intent_id="conversion-advise-evidence-001",
            target=ConversionTarget.ADVISE_PROPOSAL,
            actor_subject="advisor-001",
            idempotency_key="conversion-advise-evidence-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
        ),
    )
    with pytest.raises(InvalidReportEvidencePack, match="conversion target is not report evidence"):
        request_report_evidence_pack(
            advise_conversion.candidate,
            advise_conversion.conversion_intent,
            command(),
        )


def test_report_evidence_pack_rejects_mismatched_or_unready_conversion_state() -> None:
    conversion = report_conversion_intent(candidate())

    with pytest.raises(InvalidReportEvidencePack, match="candidate mismatch"):
        request_report_evidence_pack(
            replace(conversion.candidate, candidate_id="different-candidate"),
            conversion.conversion_intent,
            command(),
        )

    with pytest.raises(InvalidReportEvidencePack, match="target source authority"):
        request_report_evidence_pack(
            conversion.candidate,
            replace(
                conversion.conversion_intent, target_source_authority=SourceSystem.LOTUS_MANAGE
            ),
            command(),
        )

    with pytest.raises(InvalidReportEvidencePack, match="candidate lifecycle"):
        request_report_evidence_pack(
            candidate(),
            conversion.conversion_intent,
            command(),
        )

    with pytest.raises(InvalidReportEvidencePack, match="review posture"):
        request_report_evidence_pack(
            replace(conversion.candidate, review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED),
            conversion.conversion_intent,
            command(),
        )

    blocked_evidence = replace(
        conversion.candidate.evidence_packet,
        supportability=EvidenceSupportability.BLOCKED,
        unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
    )
    with pytest.raises(InvalidReportEvidencePack, match="evidence is not ready"):
        request_report_evidence_pack(
            replace(conversion.candidate, evidence_packet=blocked_evidence),
            conversion.conversion_intent,
            command(),
        )

    mismatched_intent = replace(
        conversion.conversion_intent,
        evidence_content_hash="sha256:different-evidence",
    )
    with pytest.raises(InvalidReportEvidencePack, match="evidence hash"):
        request_report_evidence_pack(
            conversion.candidate,
            mismatched_intent,
            command(),
        )


def test_governed_report_evidence_pack_requires_source_signal_summary_and_reason() -> None:
    conversion = report_conversion_intent(candidate())
    result = request_report_evidence_pack(
        conversion.candidate,
        conversion.conversion_intent,
        command(),
    )
    evidence_pack = result.evidence_pack

    with pytest.raises(ValueError, match="source_signal_ids is required"):
        GovernedReportEvidencePack(
            report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
            conversion_intent_id=evidence_pack.conversion_intent_id,
            candidate_id=evidence_pack.candidate_id,
            evidence_packet_id=evidence_pack.evidence_packet_id,
            evidence_content_hash=evidence_pack.evidence_content_hash,
            source_signal_ids=(),
            source_summaries=evidence_pack.source_summaries,
            purpose=evidence_pack.purpose,
            actor_subject=evidence_pack.actor_subject,
            idempotency_key=evidence_pack.idempotency_key,
            reason_codes=evidence_pack.reason_codes,
            requested_at_utc=evidence_pack.requested_at_utc,
            retention_policy_ref=evidence_pack.retention_policy_ref,
        )

    with pytest.raises(ValueError, match="source_summaries is required"):
        GovernedReportEvidencePack(
            report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
            conversion_intent_id=evidence_pack.conversion_intent_id,
            candidate_id=evidence_pack.candidate_id,
            evidence_packet_id=evidence_pack.evidence_packet_id,
            evidence_content_hash=evidence_pack.evidence_content_hash,
            source_signal_ids=evidence_pack.source_signal_ids,
            source_summaries=(),
            purpose=evidence_pack.purpose,
            actor_subject=evidence_pack.actor_subject,
            idempotency_key=evidence_pack.idempotency_key,
            reason_codes=evidence_pack.reason_codes,
            requested_at_utc=evidence_pack.requested_at_utc,
            retention_policy_ref=evidence_pack.retention_policy_ref,
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        GovernedReportEvidencePack(
            report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
            conversion_intent_id=evidence_pack.conversion_intent_id,
            candidate_id=evidence_pack.candidate_id,
            evidence_packet_id=evidence_pack.evidence_packet_id,
            evidence_content_hash=evidence_pack.evidence_content_hash,
            source_signal_ids=evidence_pack.source_signal_ids,
            source_summaries=(ReportEvidenceSourceSummary.from_source_ref(source_ref()),),
            purpose=evidence_pack.purpose,
            actor_subject=evidence_pack.actor_subject,
            idempotency_key=evidence_pack.idempotency_key,
            reason_codes=(),
            requested_at_utc=evidence_pack.requested_at_utc,
            retention_policy_ref=evidence_pack.retention_policy_ref,
        )


def test_report_evidence_pack_command_validates_identity_time_reason_and_retention() -> None:
    with pytest.raises(ValueError, match="report_evidence_pack_id is required"):
        ReportEvidencePackCommand(
            report_evidence_pack_id=" ",
            purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
            actor_subject="advisor-001",
            idempotency_key="report-evidence-pack-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=PACK_REQUESTED_AT,
            retention_policy_ref="lotus-report:idea-evidence-retention:v1",
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        ReportEvidencePackCommand(
            report_evidence_pack_id="report-evidence-pack-001",
            purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
            actor_subject="advisor-001",
            idempotency_key="report-evidence-pack-request-001",
            reason_codes=(),
            requested_at_utc=PACK_REQUESTED_AT,
            retention_policy_ref="lotus-report:idea-evidence-retention:v1",
        )

    with pytest.raises(ValueError, match="requested_at_utc must be timezone-aware"):
        ReportEvidencePackCommand(
            report_evidence_pack_id="report-evidence-pack-001",
            purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
            actor_subject="advisor-001",
            idempotency_key="report-evidence-pack-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=datetime(2026, 6, 21, 10, 25),
            retention_policy_ref="lotus-report:idea-evidence-retention:v1",
        )
