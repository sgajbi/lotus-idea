from __future__ import annotations

from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeConversionIntentCommand,
    RealizeReportEvidencePackCommand,
    submit_conversion_intent_to_downstream,
    submit_report_evidence_pack_to_downstream,
)
from app.domain import (
    ConversionTarget,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
)
from app.ports.downstream_realization import DownstreamRealizationOutcome
from tests.unit.test_downstream_realization_application import (
    CapturingAdviseClient,
    CapturingReportClient,
    repository_with_conversion,
    repository_with_report_pack,
)


def test_downstream_conversion_submission_uses_lookup_without_snapshot() -> None:
    source_repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    conversion_intent = source_repository.conversion_intent_by_id("conversion-advise_proposal-001")
    assert conversion_intent is not None
    repository = LookupOnlyDownstreamRepository(conversion_intent=conversion_intent)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="downstream-lookup-conversion",
            actor_subject="advisor-redacted",
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=None,
    )

    assert result.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert repository.requested_conversion_intent_ids == ["conversion-advise_proposal-001"]
    assert (
        repository.downstream_submission_by_idempotency_key("downstream-lookup-conversion")
        is not None
    )


def test_downstream_report_pack_submission_uses_lookup_without_snapshot() -> None:
    source_repository = repository_with_report_pack()
    evidence_pack = source_repository.report_evidence_pack_by_id("report-evidence-pack-001")
    assert evidence_pack is not None
    repository = LookupOnlyDownstreamRepository(report_evidence_pack=evidence_pack)
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())

    result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(
            report_evidence_pack_id="report-evidence-pack-001",
            idempotency_key="downstream-lookup-report-pack",
            actor_subject="advisor-redacted",
        ),
        repository=repository,
        report_client=report_client,
    )

    assert result.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert repository.requested_report_evidence_pack_ids == ["report-evidence-pack-001"]
    assert (
        repository.downstream_submission_by_idempotency_key("downstream-lookup-report-pack")
        is not None
    )


class LookupOnlyDownstreamRepository(InMemoryIdeaRepository):
    def __init__(
        self,
        *,
        conversion_intent: GovernedConversionIntent | None = None,
        report_evidence_pack: GovernedReportEvidencePack | None = None,
    ) -> None:
        super().__init__()
        self.conversion_intent = conversion_intent
        self.report_evidence_pack = report_evidence_pack
        self.requested_conversion_intent_ids: list[str] = []
        self.requested_report_evidence_pack_ids: list[str] = []

    def conversion_intent_by_id(
        self,
        conversion_intent_id: str,
    ) -> GovernedConversionIntent | None:
        self.requested_conversion_intent_ids.append(conversion_intent_id)
        if (
            self.conversion_intent is not None
            and self.conversion_intent.intent.conversion_intent_id == conversion_intent_id
        ):
            return self.conversion_intent
        return None

    def report_evidence_pack_by_id(
        self,
        report_evidence_pack_id: str,
    ) -> GovernedReportEvidencePack | None:
        self.requested_report_evidence_pack_ids.append(report_evidence_pack_id)
        if (
            self.report_evidence_pack is not None
            and self.report_evidence_pack.report_evidence_pack_id == report_evidence_pack_id
        ):
            return self.report_evidence_pack
        return None

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("downstream realization lookup must not hydrate a full snapshot")
