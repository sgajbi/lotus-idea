from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


_CALLER = ("POST", "/api/v1/idea-signals/missing-suitability/evaluate")
_SOURCE = ("POST", "/api/v1/idea-signals/missing-suitability/evaluate-from-source")
_TEST = "tests/integration/test_missing_suitability_signal_api.py::"
_UNIT = (
    "tests/unit/api_examples/test_missing_suitability_signal_examples.py::"
    "test_missing_suitability_examples_match_ledger_and_generated_openapi"
)


def validate_missing_suitability_evaluation_success_contract(
    endpoint: dict[str, Any], openapi_spec: dict[str, Any] | None = None
) -> list[str]:
    from app.api.examples.missing_suitability_signal import (
        build_missing_suitability_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=_CALLER,
        expected=build_missing_suitability_evaluation_response_examples(),
        workflow_name="missing-suitability-evaluation",
        required_test_evidence=(
            (
                _TEST + "test_missing_suitability_signal_api_returns_compliance_review_candidate",
                "candidate-created HTTP behavior test",
            ),
            (
                _TEST
                + "test_missing_suitability_signal_api_reports_uncertified_publication_blocker",
                "blocked HTTP behavior test",
            ),
            (
                _TEST + "test_missing_suitability_signal_api_exposes_non_candidate_success_modes",
                "suppressed and not-eligible HTTP behavior test",
            ),
            (_UNIT, "complete missing-suitability success publication contract test"),
        ),
    )


def validate_source_backed_missing_suitability_evaluation_success_contract(
    endpoint: dict[str, Any], openapi_spec: dict[str, Any] | None = None
) -> list[str]:
    from app.api.examples.missing_suitability_signal import (
        build_source_backed_missing_suitability_evaluation_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=_SOURCE,
        expected=build_source_backed_missing_suitability_evaluation_response_examples(),
        workflow_name="source-backed-missing-suitability-evaluation",
        required_test_evidence=(
            (
                _TEST
                + "test_missing_suitability_signal_from_source_api_returns_compliance_review_candidate",
                "source-backed candidate-created behavior test",
            ),
            (
                _TEST
                + "test_missing_suitability_signal_from_source_closes_runtime_on_source_blocker",
                "source-backed blocked behavior test",
            ),
            (
                _TEST
                + "test_missing_suitability_signal_from_source_exposes_non_candidate_success_modes",
                "source-backed suppressed and not-eligible behavior test",
            ),
            (_UNIT, "complete missing-suitability success publication contract test"),
        ),
    )


__all__ = [
    "validate_missing_suitability_evaluation_success_contract",
    "validate_source_backed_missing_suitability_evaluation_success_contract",
]
