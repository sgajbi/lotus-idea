from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.mandate_restriction_signal import (
    EvaluateMandateRestrictionFromAdviseCommand,
    EvaluateMandateRestrictionSignalCommand,
    evaluate_mandate_restriction_signal_command,
    evaluate_mandate_restriction_signal_from_advise,
    evaluate_mandate_restriction_readiness_from_advise,
    mandate_restriction_review_ready_from_advise_diagnostic,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubAdviseSource:
    def __init__(
        self,
        evidence: AdvisePolicyEvaluationEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[AdvisePolicyEvaluationEvidenceRequest] = []

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_mandate_restriction_command_maps_source_input() -> None:
    result = evaluate_mandate_restriction_signal_command(
        EvaluateMandateRestrictionSignalCommand(
            as_of_date=AS_OF_DATE,
            restriction_ref=_source_ref(),
            restriction_status="REVIEW_REQUIRED",
            changed_since_last_review=True,
            actionability_blocked=True,
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_mandate_restriction_")
    assert result.reason_codes == (
        ReasonCode.MANDATE_RESTRICTION_REVIEW,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_mandate_restriction_command_preserves_entitlement_blocker() -> None:
    result = evaluate_mandate_restriction_signal_command(
        EvaluateMandateRestrictionSignalCommand(
            as_of_date=AS_OF_DATE,
            restriction_ref=_source_ref(),
            restriction_status="REVIEW_REQUIRED",
            changed_since_last_review=True,
            actionability_blocked=True,
            evaluated_at_utc=EVALUATED_AT,
            entitlement_allowed=False,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_mandate_restriction_application_consumes_explicit_advise_diagnostic() -> None:
    evidence = AdvisePolicyEvaluationEvidence(
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=0,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=0,
        client_ready_publication="BLOCKED",
        policy_ref=_source_ref(),
        advise_diagnostic="mandate_restriction_review_required",
    )
    advise_source = StubAdviseSource(evidence)

    source_evaluation = evaluate_mandate_restriction_readiness_from_advise(
        _advise_command(),
        advise_source=advise_source,
    )
    result = source_evaluation.evaluation

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.reason_codes == (
        ReasonCode.MANDATE_RESTRICTION_REVIEW,
        ReasonCode.REVIEW_REQUIRED,
    )
    assert result.candidate.access_scope == _access_scope()
    assert advise_source.requests[0].evaluation_id == "pev_001"
    assert advise_source.requests[0].trace_id == "trace-advise"
    assert source_evaluation.evidence is evidence
    assert source_evaluation.source_error_code is None


def test_mandate_restriction_application_ignores_generic_advise_policy_gap() -> None:
    advise_source = StubAdviseSource(
        AdvisePolicyEvaluationEvidence(
            evaluation_status="PENDING_REVIEW",
            open_requirement_count=2,
            blocked_requirement_count=0,
            sign_off_status="PENDING_REVIEW",
            sign_off_blocker_count=1,
            client_ready_publication="BLOCKED",
            policy_ref=_source_ref(),
            advise_diagnostic="advise_policy_requirements_open",
        )
    )

    result = evaluate_mandate_restriction_signal_from_advise(
        _advise_command(),
        advise_source=advise_source,
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_mandate_restriction_application_blocks_when_advise_source_unavailable() -> None:
    source_evaluation = evaluate_mandate_restriction_readiness_from_advise(
        _advise_command(),
        advise_source=StubAdviseSource(
            exception=AdviseSourceUnavailable(code="advise_policy_workflow_pending")
        ),
    )
    result = source_evaluation.evaluation

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert source_evaluation.evidence is None
    assert source_evaluation.source_error_code == "advise_policy_workflow_pending"


def test_mandate_restriction_application_blocks_entitlement_denial() -> None:
    result = evaluate_mandate_restriction_signal_from_advise(
        _advise_command(),
        advise_source=StubAdviseSource(exception=AdviseSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_mandate_restriction_application_maps_source_product_diagnostics() -> None:
    assert mandate_restriction_review_ready_from_advise_diagnostic(None) is False
    assert (
        mandate_restriction_review_ready_from_advise_diagnostic(
            "product_restriction_review_required"
        )
        is True
    )
    assert (
        mandate_restriction_review_ready_from_advise_diagnostic("advise_policy_requirements_open")
        is False
    )


def _advise_command() -> EvaluateMandateRestrictionFromAdviseCommand:
    return EvaluateMandateRestrictionFromAdviseCommand(
        evaluation_id="pev_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        access_scope=_access_scope(),
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/restriction-posture",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:mandate-restriction-review",
        data_quality_status="quality_passed",
        freshness=EvidenceFreshness.CURRENT,
    )


def _access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-sg",
        book_id="global-balanced",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )
