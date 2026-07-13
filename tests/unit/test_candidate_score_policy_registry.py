from app.application.bond_maturity_signal import DEFAULT_BOND_MATURITY_POLICY
from app.application.concentration_risk_signal import DEFAULT_CONCENTRATION_RISK_POLICY
from app.application.drawdown_review_signal import DEFAULT_DRAWDOWN_REVIEW_POLICY
from app.application.high_cash_signal import DEFAULT_HIGH_CASH_POLICY
from app.application.high_volatility_signal import DEFAULT_HIGH_VOLATILITY_POLICY
from app.application.low_income_signal import DEFAULT_LOW_INCOME_POLICY
from app.application.mandate_health_signal import DEFAULT_MANDATE_HEALTH_POLICY
from app.application.mandate_restriction_signal import DEFAULT_MANDATE_RESTRICTION_POLICY
from app.application.missing_benchmark_signal import DEFAULT_MISSING_BENCHMARK_POLICY
from app.application.missing_risk_profile_signal import DEFAULT_MISSING_RISK_PROFILE_POLICY
from app.application.missing_suitability_signal import DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY
from app.application.underperformance_signal import DEFAULT_UNDERPERFORMANCE_POLICY
from app.domain import (
    CandidateScorePolicyVersion,
    DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS,
    DEFAULT_SCORING_POLICY,
)


def test_default_candidate_score_policies_are_registered_for_queue_ranking() -> None:
    signal_policy_versions = {
        DEFAULT_BOND_MATURITY_POLICY.policy_version,
        DEFAULT_CONCENTRATION_RISK_POLICY.policy_version,
        DEFAULT_DRAWDOWN_REVIEW_POLICY.policy_version,
        DEFAULT_HIGH_CASH_POLICY.policy_version,
        DEFAULT_HIGH_VOLATILITY_POLICY.policy_version,
        DEFAULT_LOW_INCOME_POLICY.policy_version,
        DEFAULT_MANDATE_HEALTH_POLICY.policy_version,
        DEFAULT_MANDATE_RESTRICTION_POLICY.policy_version,
        DEFAULT_MISSING_BENCHMARK_POLICY.policy_version,
        DEFAULT_MISSING_RISK_PROFILE_POLICY.policy_version,
        DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY.policy_version,
        DEFAULT_UNDERPERFORMANCE_POLICY.policy_version,
    }
    registered_versions = {version.value for version in CandidateScorePolicyVersion}

    assert signal_policy_versions | {DEFAULT_SCORING_POLICY.policy_version} == registered_versions
    assert set(DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS) == registered_versions


def test_signal_defaults_use_their_domain_owned_policy_identity() -> None:
    assert DEFAULT_HIGH_CASH_POLICY.policy_version == CandidateScorePolicyVersion.HIGH_CASH
    assert (
        DEFAULT_CONCENTRATION_RISK_POLICY.policy_version
        == CandidateScorePolicyVersion.CONCENTRATION
    )
    assert (
        DEFAULT_MANDATE_HEALTH_POLICY.policy_version == CandidateScorePolicyVersion.ALLOCATION_DRIFT
    )
    assert (
        DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY.policy_version
        == CandidateScorePolicyVersion.MISSING_SUITABILITY
    )
