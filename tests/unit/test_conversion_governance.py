from __future__ import annotations

from copy import copy
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import partial

import pytest

from tests.support.candidate_identity import initial_candidate_identity
from tests.support.score_fixture import score_fixture
from tests.support.review_authority import review_authority_grant_for_candidate

from app.domain import (
    CandidateEvidenceIdentity,
    ConversionBoundary,
    ConversionIntentCommand,
    ConversionIntentResult,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    GovernedConversionIntent,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    InvalidConversionIntent,
    InvalidConversionOutcome,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    ReviewAuthorityStatus,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
    record_conversion_outcome as _record_conversion_outcome,
    request_conversion_intent as _request_conversion_intent,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
OUTCOME_AT = datetime(2026, 6, 21, 10, 20, tzinfo=UTC)


def request_conversion_intent(
    source_candidate: IdeaCandidate,
    command: ConversionIntentCommand,
) -> ConversionIntentResult:
    return _request_conversion_intent(
        source_candidate,
        command,
        accepted_at_utc=REQUESTED_AT,
        review_authority_grant=review_authority_grant_for_candidate(
            source_candidate,
            accepted_at_utc=EVALUATED_AT,
            review_id=command.expected_review_id,
        ),
    )


record_conversion_outcome = partial(
    _record_conversion_outcome,
    accepted_at_utc=OUTCOME_AT,
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


def evidence_packet(
    *,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    applicability_expires_at_utc: datetime | None = None,
) -> IdeaEvidencePacket:
    source = source_ref()
    return IdeaEvidencePacket(
        evidence_packet_id="iep_conversion_test",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id="lineage:lotus-idea:conversion:test",
            source_refs=(source,),
            content_hash="sha256:conversion-lineage",
        ),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        unsupported_reasons=(
            (UnsupportedEvidenceReason.STALE_SOURCE,)
            if supportability is EvidenceSupportability.BLOCKED
            else ()
        ),
        created_at_utc=EVALUATED_AT,
        applicability_expires_at_utc=applicability_expires_at_utc,
    )


def candidate(
    *,
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.APPROVED,
    review_posture: ReviewPosture = ReviewPosture.APPROVED_FOR_CONVERSION,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    suppression_reason: SuppressionReason | None = None,
    applicability_expires_at_utc: datetime | None = None,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id="idea-conversion-001",
        identity=initial_candidate_identity("idea-conversion-001"),
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence_packet(
            supportability=supportability,
            applicability_expires_at_utc=applicability_expires_at_utc,
        ),
        source_signal_ids=("signal-conversion-001",),
        score=score_fixture(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("88"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        suppression_reason=suppression_reason,
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
    )


def intent_command(
    target: ConversionTarget = ConversionTarget.REPORT_EVIDENCE,
) -> ConversionIntentCommand:
    source_candidate = candidate()
    return ConversionIntentCommand(
        conversion_intent_id=f"intent-{target.value}",
        target=target,
        actor_subject="advisor-001",
        idempotency_key=f"conversion-{target.value}-request-001",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=REQUESTED_AT,
        expected_review_id="review-authority-test-001",
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(source_candidate),
    )


def test_review_approved_candidate_can_request_report_conversion_intent() -> None:
    result = request_conversion_intent(candidate(), intent_command())

    assert result.candidate.lifecycle_status is IdeaLifecycleStatus.CONVERTED_TO_REPORT
    assert result.conversion_intent.intent.target is ConversionTarget.REPORT_EVIDENCE
    assert result.conversion_intent.target_source_authority is SourceSystem.LOTUS_REPORT
    assert result.conversion_intent.boundary is ConversionBoundary.INTENT_ONLY
    assert result.conversion_intent.grants_downstream_authority is False
    assert result.conversion_intent.evidence_content_hash == "sha256:conversion-lineage"
    assert result.conversion_intent.source_signal_ids == ("signal-conversion-001",)
    assert result.conversion_intent.review_authority_grant is not None
    assert result.conversion_intent.review_authority_grant.review_id == (
        "review-authority-test-001"
    )
    assert result.audit_event.event_type == "idea.conversion.intent_requested"
    assert result.audit_event.attributes["target_source_authority"] == "lotus-report"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes


def test_conversion_intent_uses_server_acceptance_time_for_control_chronology() -> None:
    accepted_at = REQUESTED_AT + datetime.resolution

    result = _request_conversion_intent(
        candidate(),
        intent_command(),
        accepted_at_utc=accepted_at,
        review_authority_grant=review_authority_grant_for_candidate(
            candidate(),
            accepted_at_utc=EVALUATED_AT,
        ),
    )

    assert result.conversion_intent.intent.requested_at_utc == REQUESTED_AT
    assert result.conversion_intent.accepted_at_utc == accepted_at
    assert result.candidate.updated_at_utc == accepted_at
    assert result.audit_event.occurred_at_utc == accepted_at
    assert result.audit_event.attributes["observed_at_utc"] == REQUESTED_AT.isoformat()


@pytest.mark.parametrize(
    ("target", "expected_status", "expected_source"),
    [
        (
            ConversionTarget.ADVISE_PROPOSAL,
            IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL,
            SourceSystem.LOTUS_ADVISE,
        ),
        (
            ConversionTarget.MANAGE_REVIEW,
            IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW,
            SourceSystem.LOTUS_MANAGE,
        ),
        (
            ConversionTarget.REPORT_EVIDENCE,
            IdeaLifecycleStatus.CONVERTED_TO_REPORT,
            SourceSystem.LOTUS_REPORT,
        ),
    ],
)
def test_conversion_target_maps_to_downstream_authority_and_lifecycle(
    target: ConversionTarget,
    expected_status: IdeaLifecycleStatus,
    expected_source: SourceSystem,
) -> None:
    source_candidate = candidate()
    result = request_conversion_intent(source_candidate, intent_command(target))

    assert result.source_candidate is source_candidate
    assert result.candidate.lifecycle_status is expected_status
    assert result.conversion_intent.target_source_authority is expected_source


def test_conversion_intent_requires_human_review_approved_ready_candidate() -> None:
    with pytest.raises(InvalidConversionIntent, match="candidate lifecycle is not approved"):
        request_conversion_intent(
            candidate(
                lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
                review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            ),
            intent_command(),
        )

    contradictory_legacy_candidate = copy(candidate())
    object.__setattr__(
        contradictory_legacy_candidate,
        "review_posture",
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    )
    with pytest.raises(InvalidConversionIntent, match="review posture is not approved"):
        request_conversion_intent(
            contradictory_legacy_candidate,
            intent_command(),
        )

    with pytest.raises(InvalidConversionIntent, match="evidence is not ready"):
        request_conversion_intent(
            candidate(supportability=EvidenceSupportability.BLOCKED),
            intent_command(),
        )


@pytest.mark.parametrize("expiry", [REQUESTED_AT, REQUESTED_AT - datetime.resolution])
def test_conversion_intent_refuses_candidate_at_or_after_server_time_expiry(
    expiry: datetime,
) -> None:
    with pytest.raises(InvalidConversionIntent, match="candidate applicability has expired"):
        request_conversion_intent(
            candidate(applicability_expires_at_utc=expiry),
            intent_command(),
        )


def test_conversion_intent_allows_candidate_immediately_before_server_time_expiry() -> None:
    result = request_conversion_intent(
        candidate(applicability_expires_at_utc=REQUESTED_AT + datetime.resolution),
        intent_command(),
    )

    assert result.conversion_intent.accepted_at_utc == REQUESTED_AT


def test_conversion_intent_rejects_stale_candidate_evidence_identity() -> None:
    source_candidate = candidate()
    command = replace(
        intent_command(),
        expected_candidate_evidence=replace(
            CandidateEvidenceIdentity.from_candidate(source_candidate),
            evidence_version=2,
        ),
    )

    with pytest.raises(InvalidConversionIntent, match="evidence identity is stale"):
        request_conversion_intent(source_candidate, command)


def test_conversion_intent_rejects_different_or_inactive_review_authority() -> None:
    source_candidate = candidate()
    command = intent_command()
    grant = review_authority_grant_for_candidate(
        source_candidate,
        accepted_at_utc=EVALUATED_AT,
        review_id=command.expected_review_id,
    )

    with pytest.raises(InvalidConversionIntent, match="review authority identity differs"):
        _request_conversion_intent(
            source_candidate,
            command,
            accepted_at_utc=REQUESTED_AT,
            review_authority_grant=replace(grant, review_id="different-review"),
        )

    with pytest.raises(InvalidConversionIntent, match="review authority is revoked"):
        _request_conversion_intent(
            source_candidate,
            command,
            accepted_at_utc=REQUESTED_AT,
            review_authority_grant=replace(grant, status=ReviewAuthorityStatus.REVOKED),
        )

    with pytest.raises(InvalidConversionIntent, match="review authority is revoked"):
        _request_conversion_intent(
            source_candidate,
            command,
            accepted_at_utc=REQUESTED_AT,
            review_authority_grant=replace(
                grant,
                authority_policy_version="idea-review-authority-v0",
            ),
        )

    with pytest.raises(InvalidConversionIntent, match="review authority evidence differs"):
        _request_conversion_intent(
            source_candidate,
            command,
            accepted_at_utc=REQUESTED_AT,
            review_authority_grant=replace(
                grant,
                candidate_evidence=replace(
                    grant.candidate_evidence,
                    evidence_version=grant.candidate_evidence.evidence_version + 1,
                ),
            ),
        )


def test_persisted_conversion_intent_rejects_inconsistent_review_authority() -> None:
    governed = request_conversion_intent(candidate(), intent_command()).conversion_intent
    assert governed.review_authority_grant is not None
    grant = governed.review_authority_grant

    conflicting_grants = (
        (
            replace(
                grant,
                candidate_evidence=replace(
                    grant.candidate_evidence,
                    candidate_id="idea-conversion-other",
                ),
            ),
            "candidate must match",
        ),
        (
            replace(
                grant,
                candidate_evidence=replace(
                    grant.candidate_evidence,
                    evidence_packet_id="evidence-other",
                ),
            ),
            "evidence packet must match",
        ),
        (
            replace(
                grant,
                candidate_evidence=replace(
                    grant.candidate_evidence,
                    evidence_content_hash="sha256:evidence-other",
                ),
            ),
            "evidence hash must match",
        ),
        (
            replace(grant, accepted_at_utc=governed.accepted_at_utc + datetime.resolution),
            "cannot postdate",
        ),
    )
    for conflicting_grant, message in conflicting_grants:
        with pytest.raises(ValueError, match=message):
            replace(governed, review_authority_grant=conflicting_grant)


def test_conversion_command_validates_idempotency_reason_and_time() -> None:
    opaque_identity = ConversionIntentCommand(
        conversion_intent_id="legacy/intent?version=1",
        target=ConversionTarget.REPORT_EVIDENCE,
        actor_subject="advisor-001",
        idempotency_key="conversion-request-opaque",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=REQUESTED_AT,
        expected_review_id="review-authority-test-001",
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate()),
    )
    assert opaque_identity.conversion_intent_id == "legacy/intent?version=1"

    with pytest.raises(ValueError, match="at most 160 characters"):
        ConversionIntentCommand(
            conversion_intent_id="i" * 161,
            target=ConversionTarget.REPORT_EVIDENCE,
            actor_subject="advisor-001",
            idempotency_key="conversion-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
            expected_review_id="review-authority-test-001",
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate()),
        )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        ConversionIntentCommand(
            conversion_intent_id="intent-invalid",
            target=ConversionTarget.REPORT_EVIDENCE,
            actor_subject="advisor-001",
            idempotency_key=" ",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=REQUESTED_AT,
            expected_review_id="review-authority-test-001",
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate()),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        ConversionIntentCommand(
            conversion_intent_id="intent-invalid",
            target=ConversionTarget.REPORT_EVIDENCE,
            actor_subject="advisor-001",
            idempotency_key="conversion-request-001",
            reason_codes=(),
            requested_at_utc=REQUESTED_AT,
            expected_review_id="review-authority-test-001",
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate()),
        )

    with pytest.raises(ValueError, match="requested_at_utc must be timezone-aware"):
        ConversionIntentCommand(
            conversion_intent_id="intent-invalid",
            target=ConversionTarget.REPORT_EVIDENCE,
            actor_subject="advisor-001",
            idempotency_key="conversion-request-001",
            reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
            requested_at_utc=datetime(2026, 6, 21, 10, 15),
            expected_review_id="review-authority-test-001",
            expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate()),
        )


def test_conversion_outcome_must_come_from_target_source_authority() -> None:
    intent = request_conversion_intent(
        candidate(), intent_command(ConversionTarget.ADVISE_PROPOSAL)
    ).conversion_intent

    with pytest.raises(InvalidConversionOutcome, match="outcome source must be lotus-advise"):
        record_conversion_outcome(
            intent,
            ConversionOutcomeCommand(
                conversion_outcome_id="outcome-wrong-source",
                status=ConversionOutcomeStatus.ACCEPTED,
                source_system=SourceSystem.LOTUS_MANAGE,
                source_event_version=1,
                downstream_reference="manage-review-001",
                recorded_at_utc=OUTCOME_AT,
            ),
        )


def test_conversion_outcome_records_downstream_status_without_granting_authority() -> None:
    intent = request_conversion_intent(candidate(), intent_command()).conversion_intent

    result = record_conversion_outcome(
        intent,
        ConversionOutcomeCommand(
            conversion_outcome_id="outcome-report-accepted",
            status=ConversionOutcomeStatus.ACCEPTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=1,
            downstream_reference="report-evidence-pack-001",
            recorded_at_utc=OUTCOME_AT,
        ),
    )

    assert result.conversion_outcome.outcome.status is ConversionOutcomeStatus.ACCEPTED
    assert result.conversion_outcome.source_system is SourceSystem.LOTUS_REPORT
    assert result.conversion_outcome.boundary is ConversionBoundary.DOWNSTREAM_REALIZATION_REQUIRED
    assert result.conversion_outcome.grants_execution_authority is False
    assert result.conversion_outcome.grants_client_communication_authority is False
    assert result.conversion_outcome.grants_suitability_authority is False
    assert result.audit_event.event_type == "idea.conversion.outcome_recorded"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes


def test_conversion_outcome_preserves_owner_time_and_uses_idea_acceptance_time() -> None:
    intent = request_conversion_intent(candidate(), intent_command()).conversion_intent
    accepted_at = OUTCOME_AT + datetime.resolution
    command = ConversionOutcomeCommand(
        conversion_outcome_id="outcome-report-received",
        status=ConversionOutcomeStatus.ACCEPTED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=1,
        downstream_reference="report-evidence-pack-accepted",
        recorded_at_utc=OUTCOME_AT,
    )

    result = _record_conversion_outcome(
        intent,
        command,
        accepted_at_utc=accepted_at,
    )

    assert result.conversion_outcome.outcome.recorded_at_utc == OUTCOME_AT
    assert result.conversion_outcome.accepted_at_utc == accepted_at
    assert result.conversion_outcome.source_event_version == 1
    assert result.audit_event.occurred_at_utc == accepted_at
    assert result.audit_event.attributes["observed_at_utc"] == OUTCOME_AT.isoformat()


def test_conversion_outcome_validates_optional_reference_and_time() -> None:
    with pytest.raises(ValueError, match="source_event_version must be positive"):
        ConversionOutcomeCommand(
            conversion_outcome_id="outcome-invalid-version",
            status=ConversionOutcomeStatus.REQUESTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=0,
            recorded_at_utc=OUTCOME_AT,
        )

    with pytest.raises(ValueError, match="downstream_reference is required"):
        ConversionOutcomeCommand(
            conversion_outcome_id="outcome-invalid",
            status=ConversionOutcomeStatus.ACCEPTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=1,
            downstream_reference=" ",
            recorded_at_utc=OUTCOME_AT,
        )

    with pytest.raises(ValueError, match="recorded_at_utc must be timezone-aware"):
        ConversionOutcomeCommand(
            conversion_outcome_id="outcome-invalid",
            status=ConversionOutcomeStatus.ACCEPTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=1,
            recorded_at_utc=datetime(2026, 6, 21, 10, 20),
        )


def test_accepted_conversion_outcome_requires_owner_business_reference() -> None:
    intent = request_conversion_intent(candidate(), intent_command()).conversion_intent

    with pytest.raises(
        InvalidConversionOutcome,
        match="accepted or completed outcome requires downstream reference",
    ):
        record_conversion_outcome(
            intent,
            ConversionOutcomeCommand(
                conversion_outcome_id="outcome-report-unreferenced",
                status=ConversionOutcomeStatus.ACCEPTED,
                source_system=SourceSystem.LOTUS_REPORT,
                source_event_version=1,
                recorded_at_utc=OUTCOME_AT,
            ),
        )


def test_conversion_targets_do_not_include_execution_or_client_communication() -> None:
    forbidden_targets = {
        "trade_order",
        "order_execution",
        "client_email",
        "client_message",
        "suitability_approval",
        "compliance_approval",
    }

    assert forbidden_targets.isdisjoint({target.value for target in ConversionTarget})


def test_governed_conversion_intent_requires_source_provenance() -> None:
    intent = request_conversion_intent(candidate(), intent_command()).conversion_intent

    with pytest.raises(ValueError, match="source_signal_ids is required"):
        GovernedConversionIntent(
            intent=intent.intent,
            evidence_packet_id=intent.evidence_packet_id,
            evidence_content_hash=intent.evidence_content_hash,
            source_signal_ids=(),
            actor_subject=intent.actor_subject,
            idempotency_key=intent.idempotency_key,
            reason_codes=intent.reason_codes,
            target_source_authority=intent.target_source_authority,
            accepted_at_utc=intent.accepted_at_utc,
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        GovernedConversionIntent(
            intent=intent.intent,
            evidence_packet_id=intent.evidence_packet_id,
            evidence_content_hash=intent.evidence_content_hash,
            source_signal_ids=intent.source_signal_ids,
            actor_subject=intent.actor_subject,
            idempotency_key=intent.idempotency_key,
            reason_codes=(),
            target_source_authority=intent.target_source_authority,
            accepted_at_utc=intent.accepted_at_utc,
        )
