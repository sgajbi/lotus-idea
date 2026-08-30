from __future__ import annotations

from copy import deepcopy

from tests.support.opportunity_quality_golden import evaluate_golden_set, load_golden_set

from app.domain.scoring import CandidateScorePolicyVersion


def test_independently_authored_opportunity_quality_golden_set_passes() -> None:
    golden_set = load_golden_set()

    assert evaluate_golden_set(golden_set) == ()


def test_golden_set_covers_every_implemented_signal_policy() -> None:
    golden_set = load_golden_set()
    covered_policies = {
        (case["family"], case.get("signalType", case["family"])) for case in golden_set["cases"]
    }

    assert covered_policies == {
        ("allocation_drift", "allocation_drift"),
        ("bond_maturity", "bond_maturity"),
        ("concentration", "concentration"),
        ("high_cash", "high_cash"),
        ("high_volatility", "drawdown_review"),
        ("high_volatility", "volatility"),
        ("low_income", "low_income"),
        ("mandate_restriction", "mandate_restriction"),
        ("missing_benchmark", "missing_benchmark"),
        ("missing_risk_profile", "missing_risk_profile"),
        ("missing_suitability_context", "missing_suitability_context"),
        ("underperformance", "underperformance"),
    }
    covered_score_policy_versions = {
        case["expected"]["scorePolicyVersion"]
        for case in golden_set["cases"]
        if case["expected"]["outcome"] == "candidate_created"
    }
    registered_signal_policy_versions = {
        version.value
        for version in CandidateScorePolicyVersion
        if version is not CandidateScorePolicyVersion.WEIGHTED_EVIDENCE
    }
    assert covered_score_policy_versions == registered_signal_policy_versions


def test_golden_set_detects_outcome_regression() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["cases"][0]["expected"]["outcome"] = "not_eligible"

    errors = evaluate_golden_set(golden_set)

    assert any("active-high-cash outcome expected 'not_eligible'" in error for error in errors)


def test_golden_set_detects_explanation_regression() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["cases"][1]["expected"]["reasonCodes"] = ["review_required"]

    errors = evaluate_golden_set(golden_set)

    assert any("active-concentration reasonCodes" in error for error in errors)


def test_golden_set_detects_ranking_regression() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["queueExpectations"][0]["orderedCaseIds"] = [
        "active-underperformance",
        "active-concentration",
        "active-high-cash",
    ]

    errors = evaluate_golden_set(golden_set)

    assert any("active-opportunities:advisor orderedCaseIds" in error for error in errors)


def test_golden_set_detects_score_component_regression() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["scoringExpectations"][0]["expected"]["contributions"]["materiality"] = "17.00"

    errors = evaluate_golden_set(golden_set)

    assert any("weighted-evidence-score contributions" in error for error in errors)


def test_golden_set_detects_candidate_reopen_regression() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["lifecycleExpectations"][2]["expected"]["evidenceVersion"] = 2

    errors = evaluate_golden_set(golden_set)

    assert any(
        "expired-condition-reopens-for-review evidenceVersion expected 2" in error
        for error in errors
    )


def test_golden_set_rejects_production_derived_expectations() -> None:
    golden_set = deepcopy(load_golden_set())
    golden_set["authorship"]["expectedResultsDerivedFromProductionCode"] = True

    assert evaluate_golden_set(golden_set) == (
        "expected results must not be derived from production code",
    )
