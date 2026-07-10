from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

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
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionMutationResult,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.ports.downstream_realization import (
    DownstreamRealizationOutcome,
    DownstreamRealizationOutcomePosture,
)


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
    idempotency_key: str | None = None

    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome


@dataclass
class RaisingAdviseClient:
    call_count: int = 0

    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.call_count += 1
        raise RuntimeError("downstream response lost")


@dataclass
class CapturingManageClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[GovernedConversionIntent, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None

    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, intent)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome


@dataclass
class CapturingReportClient:
    outcome: DownstreamRealizationOutcome
    submitted: tuple[GovernedReportEvidencePack, ...] = ()
    correlation_id: str | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        self.submitted = (*self.submitted, evidence_pack)
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.idempotency_key = idempotency_key
        return self.outcome


def test_submit_conversion_intent_routes_advise_intent_without_recording_outcome() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="submission-advise-001",
            actor_subject="advisor-redacted",
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
    assert advise_client.idempotency_key == "submission-advise-001"
    assert manage_client.submitted == ()
    assert "portfolio_id" not in str(result)
    assert "client_id" not in str(result)


def test_submit_conversion_intent_replays_local_downstream_submission_without_client_call() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())
    command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-advise_proposal-001",
        idempotency_key="submission-advise-replay-001",
        actor_subject="advisor-redacted",
        correlation_id="corr-realization",
        trace_id="trace-realization",
        submitted_at_utc=EVALUATED_AT,
    )

    first = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )
    second = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )

    assert first.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert first.idempotency_replayed is False
    assert second.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert second.idempotency_replayed is True
    assert len(advise_client.submitted) == 1
    assert manage_client.submitted == ()


def test_downstream_acceptance_with_failed_local_finalize_requires_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-advise_proposal-001",
        idempotency_key="submission-finalize-failure-001",
        actor_subject="advisor-redacted",
        submitted_at_utc=EVALUATED_AT,
    )
    original_finalize = repository.finalize_downstream_submission

    def fail_finalize(**_: object) -> None:
        raise RuntimeError("simulated local commit failure")

    monkeypatch.setattr(repository, "finalize_downstream_submission", fail_finalize)
    first = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=None,
    )
    monkeypatch.setattr(repository, "finalize_downstream_submission", original_finalize)
    retry = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=None,
    )

    persisted = repository.downstream_submission_by_idempotency_key(command.idempotency_key)
    assert first.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert first.downstream_failure_reason == "downstream_submission_finalization_failed"
    assert first.grants_downstream_authority is False
    assert retry.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert retry.idempotency_replayed is True
    assert persisted is not None
    assert persisted.status.value == "in_flight"
    assert len(advise_client.submitted) == 1


def test_unknown_downstream_outcome_is_durable_and_never_retried_automatically() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    advise_client = CapturingAdviseClient(
        DownstreamRealizationOutcome.unknown("downstream_timeout")
    )
    command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-advise_proposal-001",
        idempotency_key="submission-timeout-001",
        actor_subject="advisor-redacted",
        submitted_at_utc=EVALUATED_AT,
    )

    first = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=None,
    )
    retry = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=None,
    )

    assert first.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert first.downstream_failure_reason == "downstream_timeout"
    assert first.support_reference is not None
    assert retry.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert retry.idempotency_replayed is True
    assert len(advise_client.submitted) == 1


def test_downstream_client_exception_is_durable_and_not_retried() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    client = RaisingAdviseClient()
    command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-advise_proposal-001",
        idempotency_key="submission-client-exception-001",
        actor_subject="advisor-redacted",
        submitted_at_utc=EVALUATED_AT,
    )

    first = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=client,
        manage_client=None,
    )
    replay = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=client,
        manage_client=None,
    )

    assert first.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert first.downstream_failure_reason == "downstream_call_outcome_unknown"
    assert replay.idempotency_replayed is True
    assert client.call_count == 1


def test_downstream_finalization_lease_conflict_returns_uncertain_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    monkeypatch.setattr(
        repository,
        "finalize_downstream_submission",
        lambda **kwargs: DownstreamSubmissionMutationResult(
            decision=DownstreamSubmissionMutationDecision.LEASE_CONFLICT,
            record=None,
            blocker="downstream_submission_lease_conflict",
        ),
    )

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="submission-finalize-conflict-001",
            actor_subject="advisor-redacted",
            submitted_at_utc=EVALUATED_AT,
        ),
        repository=repository,
        advise_client=CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream()),
        manage_client=None,
    )

    assert result.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
    assert result.downstream_failure_reason == "downstream_submission_lease_conflict"


@pytest.mark.parametrize(
    ("submitted_at", "message"),
    [
        (datetime(2026, 6, 21, 10, 0), "must be timezone-aware"),
        (
            datetime(2026, 6, 21, 11, 0, tzinfo=timezone(timedelta(hours=1))),
            "must be UTC",
        ),
    ],
)
def test_downstream_submission_requires_utc_submission_time(
    submitted_at: datetime,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        submit_conversion_intent_to_downstream(
            RealizeConversionIntentCommand(
                conversion_intent_id="conversion-advise_proposal-001",
                idempotency_key="submission-invalid-time-001",
                actor_subject="advisor-redacted",
                submitted_at_utc=submitted_at,
            ),
            repository=repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL),
            advise_client=CapturingAdviseClient(
                DownstreamRealizationOutcome.accepted_by_downstream()
            ),
            manage_client=None,
        )


def test_downstream_outcome_contract_rejects_ambiguous_postures() -> None:
    with pytest.raises(ValueError, match="accepted outcome forbids failure_reason"):
        DownstreamRealizationOutcome(
            posture=DownstreamRealizationOutcomePosture.ACCEPTED,
            failure_reason="unexpected",
        )
    with pytest.raises(ValueError, match="non-accepted outcome requires failure_reason"):
        DownstreamRealizationOutcome(posture=DownstreamRealizationOutcomePosture.UNKNOWN)
    with pytest.raises(ValueError, match="failure_reason is required"):
        DownstreamRealizationOutcome.rejected_by_downstream(" ")


def test_submit_conversion_intent_rejects_same_key_for_different_resource() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    second = request_conversion_intent(
        candidate(),
        ConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-002",
            target=ConversionTarget.ADVISE_PROPOSAL,
            actor_subject="advisor-redacted",
            idempotency_key="conversion-advise_proposal-request-002",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
        ),
    )
    repository.record_conversion_intent(
        second,
        idempotency_key="conversion-advise_proposal-request-002",
        payload={"target": ConversionTarget.ADVISE_PROPOSAL.value, "sequence": "2"},
    )
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())

    accepted = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-001",
            idempotency_key="submission-advise-conflict-001",
            actor_subject="advisor-redacted",
            submitted_at_utc=EVALUATED_AT,
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )
    conflict = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-advise_proposal-002",
            idempotency_key="submission-advise-conflict-001",
            actor_subject="advisor-redacted",
            submitted_at_utc=EVALUATED_AT,
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )

    assert accepted.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert conflict.status is DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT
    assert conflict.downstream_failure_reason == "idempotency_conflict"
    assert len(advise_client.submitted) == 1


def test_submit_conversion_intent_persists_not_configured_posture_for_replay() -> None:
    repository = repository_with_conversion(ConversionTarget.ADVISE_PROPOSAL)
    command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-advise_proposal-001",
        idempotency_key="submission-advise-not-configured-001",
        actor_subject="advisor-redacted",
        submitted_at_utc=EVALUATED_AT,
    )
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())

    first = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=None,
        manage_client=None,
    )
    replayed = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=advise_client,
        manage_client=CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream()),
    )

    assert first.status is DownstreamRealizationStatus.NOT_CONFIGURED
    assert first.downstream_failure_reason == "downstream_realization_not_configured"
    assert replayed.status is DownstreamRealizationStatus.NOT_CONFIGURED
    assert replayed.idempotency_replayed is True
    assert advise_client.submitted == ()


def test_submit_conversion_intent_maps_downstream_rejection_to_bounded_status() -> None:
    repository = repository_with_conversion(ConversionTarget.MANAGE_REVIEW)
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(
        DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected")
    )

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-manage_review-001",
            idempotency_key="submission-manage-001",
            actor_subject="advisor-redacted",
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
    assert result.downstream_failure_reason == "downstream_rejected"
    assert advise_client.submitted == ()
    assert manage_client.submitted[0].target_source_authority is SourceSystem.LOTUS_MANAGE
    assert manage_client.correlation_id == "corr-manage-realization"
    assert manage_client.trace_id == "trace-manage-realization"
    assert manage_client.idempotency_key == "submission-manage-001"


def test_report_conversion_intent_requires_report_evidence_pack_request_submission() -> None:
    repository = repository_with_conversion(ConversionTarget.REPORT_EVIDENCE)

    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="conversion-report_evidence-001",
            idempotency_key="submission-report-intent-001",
            actor_subject="advisor-redacted",
        ),
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
            idempotency_key="submission-report-pack-001",
            actor_subject="advisor-redacted",
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
    assert report_client.idempotency_key == "submission-report-pack-001"


def test_submit_report_evidence_pack_replays_local_submission_without_client_call() -> None:
    repository = repository_with_report_pack()
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())
    command = RealizeReportEvidencePackCommand(
        report_evidence_pack_id="report-evidence-pack-001",
        idempotency_key="submission-report-pack-replay-001",
        actor_subject="advisor-redacted",
        submitted_at_utc=EVALUATED_AT,
    )

    first = submit_report_evidence_pack_to_downstream(
        command,
        repository=repository,
        report_client=report_client,
    )
    second = submit_report_evidence_pack_to_downstream(
        command,
        repository=repository,
        report_client=report_client,
    )

    assert first.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert first.idempotency_replayed is False
    assert second.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
    assert second.idempotency_replayed is True
    assert len(report_client.submitted) == 1


def test_downstream_realization_returns_not_found_without_calling_clients() -> None:
    repository = InMemoryIdeaRepository()
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())

    conversion_result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id="missing-conversion",
            idempotency_key="submission-missing-conversion-001",
            actor_subject="advisor-redacted",
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )
    pack_result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(
            report_evidence_pack_id="missing-pack",
            idempotency_key="submission-missing-pack-001",
            actor_subject="advisor-redacted",
        ),
        repository=repository,
        report_client=report_client,
    )

    assert conversion_result.status is DownstreamRealizationStatus.NOT_FOUND
    assert pack_result.status is DownstreamRealizationStatus.NOT_FOUND
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()
    assert report_client.submitted == ()


def test_submit_conversion_intent_requires_non_blank_identifier() -> None:
    advise_client = CapturingAdviseClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingManageClient(DownstreamRealizationOutcome.accepted_by_downstream())

    with pytest.raises(ValueError, match="conversion_intent_id is required"):
        submit_conversion_intent_to_downstream(
            RealizeConversionIntentCommand(
                conversion_intent_id=" ",
                idempotency_key="submission-blank-conversion-001",
                actor_subject="advisor-redacted",
            ),
            repository=InMemoryIdeaRepository(),
            advise_client=advise_client,
            manage_client=manage_client,
        )

    assert advise_client.submitted == ()
    assert manage_client.submitted == ()


def test_submit_report_evidence_pack_requires_non_blank_identifier() -> None:
    report_client = CapturingReportClient(DownstreamRealizationOutcome.accepted_by_downstream())

    with pytest.raises(ValueError, match="report_evidence_pack_id is required"):
        submit_report_evidence_pack_to_downstream(
            RealizeReportEvidencePackCommand(
                report_evidence_pack_id=" ",
                idempotency_key="submission-blank-report-pack-001",
                actor_subject="advisor-redacted",
            ),
            repository=InMemoryIdeaRepository(),
            report_client=report_client,
        )

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
