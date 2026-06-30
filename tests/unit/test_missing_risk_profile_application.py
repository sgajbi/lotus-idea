from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.application.missing_risk_profile_signal import (
    EvaluateMissingRiskProfileFromAdviseCommand,
    EvaluateMissingRiskProfileSignalCommand,
    RiskProfilePosture,
    evaluate_missing_risk_profile_signal_command,
    evaluate_missing_risk_profile_signal_from_advise,
    _risk_profile_posture_from_advise_diagnostic,
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


def test_missing_risk_profile_command_maps_source_input() -> None:
    result = evaluate_missing_risk_profile_signal_command(
        EvaluateMissingRiskProfileSignalCommand(
            as_of_date=AS_OF_DATE,
            risk_profile_ref=_source_ref(),
            risk_profile_status="MISSING",
            risk_profile_effective_for_as_of_date=False,
            risk_profile_review_due=True,
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_missing_risk_profile_")
    assert result.reason_codes == (ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED)


def test_missing_risk_profile_application_consumes_explicit_advise_diagnostic() -> None:
    advise_source = StubAdviseSource(
        AdvisePolicyEvaluationEvidence(
            evaluation_status="PENDING_REVIEW",
            open_requirement_count=1,
            blocked_requirement_count=0,
            sign_off_status="PENDING_REVIEW",
            sign_off_blocker_count=0,
            client_ready_publication="BLOCKED",
            policy_ref=_source_ref(),
            advise_diagnostic="advise_policy_requirements_open,risk_profile_missing",
        )
    )

    result = evaluate_missing_risk_profile_signal_from_advise(
        _command(),
        advise_source=advise_source,
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.reason_codes == (ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED)
    assert advise_source.requests[0].evaluation_id == "pev_001"
    assert advise_source.requests[0].trace_id == "trace-advise"


def test_missing_risk_profile_application_ignores_generic_suitability_gap() -> None:
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

    result = evaluate_missing_risk_profile_signal_from_advise(
        _command(),
        advise_source=advise_source,
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    (
        ("client_risk_profile_stale", RiskProfilePosture.STALE),
        ("risk_profile_expired", RiskProfilePosture.EXPIRED),
        ("risk_profile_review_due", RiskProfilePosture.REVIEW_DUE),
        ("client_risk_profile_current", RiskProfilePosture.CURRENT),
        ("advise_policy_requirements_open", None),
    ),
)
def test_missing_risk_profile_application_maps_advise_risk_profile_diagnostics(
    diagnostic: str,
    expected: RiskProfilePosture | None,
) -> None:
    assert _risk_profile_posture_from_advise_diagnostic(diagnostic) is expected


def test_missing_risk_profile_application_blocks_when_advise_source_unavailable() -> None:
    result = evaluate_missing_risk_profile_signal_from_advise(
        _command(),
        advise_source=StubAdviseSource(
            exception=AdviseSourceUnavailable(code="advise_policy_workflow_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_missing_risk_profile_application_blocks_entitlement_denial() -> None:
    result = evaluate_missing_risk_profile_signal_from_advise(
        _command(),
        advise_source=StubAdviseSource(exception=AdviseSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def _command() -> EvaluateMissingRiskProfileFromAdviseCommand:
    return EvaluateMissingRiskProfileFromAdviseCommand(
        evaluation_id="pev_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/workflow",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:advise-risk-profile-gap",
        data_quality_status="quality_passed",
        freshness=EvidenceFreshness.CURRENT,
    )
