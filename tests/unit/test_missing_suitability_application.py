from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.missing_suitability_signal import (
    EvaluateMissingSuitabilityContextFromAdviseCommand,
    evaluate_missing_suitability_context_signal_from_advise,
    evaluate_missing_suitability_context_readiness_from_advise,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
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


def test_missing_suitability_application_consumes_advise_policy_evidence() -> None:
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

    result = evaluate_missing_suitability_context_signal_from_advise(
        _command(),
        advise_source=advise_source,
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.reason_codes == (
        ReasonCode.SUITABILITY_CONTEXT_MISSING,
        ReasonCode.REVIEW_REQUIRED,
    )
    assert advise_source.requests[0].evaluation_id == "pev_001"


def test_missing_suitability_application_blocks_when_advise_context_is_clear() -> None:
    advise_source = StubAdviseSource(
        AdvisePolicyEvaluationEvidence(
            evaluation_status="READY",
            open_requirement_count=0,
            blocked_requirement_count=0,
            sign_off_status="SIGNED_OFF",
            sign_off_blocker_count=0,
            client_ready_publication="BLOCKED",
            policy_ref=_source_ref(),
            advise_diagnostic="advise_policy_context_available",
        )
    )

    result = evaluate_missing_suitability_context_signal_from_advise(
        _command(),
        advise_source=advise_source,
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_missing_suitability_application_blocks_when_advise_source_unavailable() -> None:
    result = evaluate_missing_suitability_context_signal_from_advise(
        _command(),
        advise_source=StubAdviseSource(
            exception=AdviseSourceUnavailable(code="advise_policy_workflow_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_missing_suitability_application_blocks_entitlement_denial_without_candidate() -> None:
    result = evaluate_missing_suitability_context_signal_from_advise(
        _command(),
        advise_source=StubAdviseSource(exception=AdviseSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_missing_suitability_application_preserves_authoritative_source_evidence() -> None:
    evidence = _evidence()

    result = evaluate_missing_suitability_context_readiness_from_advise(
        _command(),
        advise_source=StubAdviseSource(evidence=evidence),
    )

    assert result.evidence is evidence
    assert result.source_error_code is None
    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED


def test_missing_suitability_application_preserves_source_failure_code() -> None:
    result = evaluate_missing_suitability_context_readiness_from_advise(
        _command(),
        advise_source=StubAdviseSource(
            exception=AdviseSourceUnavailable(code="advise_policy_workflow_timeout")
        ),
    )

    assert result.evidence is None
    assert result.source_error_code == "advise_policy_workflow_timeout"
    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED


def _command() -> EvaluateMissingSuitabilityContextFromAdviseCommand:
    return EvaluateMissingSuitabilityContextFromAdviseCommand(
        evaluation_id="pev_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


def _evidence() -> AdvisePolicyEvaluationEvidence:
    return AdvisePolicyEvaluationEvidence(
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=2,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=1,
        client_ready_publication="BLOCKED",
        policy_ref=_source_ref(),
        advise_diagnostic="advise_policy_requirements_open",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/workflow",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:advisory-policy-evaluation-record",
        data_quality_status="quality_passed",
        freshness=EvidenceFreshness.CURRENT,
    )
