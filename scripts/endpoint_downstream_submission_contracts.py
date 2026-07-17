from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_status_contract


_CONVERSION = (
    "POST",
    "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
)
_REPORT = (
    "POST",
    "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
)
_TEST = "tests/integration/test_downstream_realization_api.py::"
_UNIT = (
    "tests/unit/api_examples/test_downstream_submission_examples.py::"
    "test_downstream_submission_examples_match_ledger_and_generated_openapi"
)


def validate_conversion_downstream_submission_success_contract(
    endpoint: dict[str, Any], openapi_spec: dict[str, Any] | None = None
) -> list[str]:
    from app.api.examples.downstream_submission import (
        build_conversion_downstream_submission_200_response_examples,
        build_conversion_downstream_submission_202_response_examples,
    )

    return validate_named_success_status_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=_CONVERSION,
        expected_by_status=(
            ("200", build_conversion_downstream_submission_200_response_examples()),
            ("202", build_conversion_downstream_submission_202_response_examples()),
        ),
        workflow_name="conversion-downstream-submission",
        required_test_evidence=(
            (
                _TEST
                + "test_conversion_downstream_submission_api_accepts_advise_intent_with_support_reference",
                "accepted HTTP behavior test",
            ),
            (
                _TEST + "test_conversion_downstream_submission_api_returns_bounded_rejection",
                "rejected HTTP behavior test",
            ),
            (
                _TEST + "test_conversion_downstream_submission_api_replays_same_idempotency_key",
                "replay no-duplicate-call behavior test",
            ),
            (
                _TEST
                + "test_conversion_downstream_submission_api_returns_durable_uncertain_posture",
                "202 reconciliation-required behavior test",
            ),
            (_UNIT, "complete conversion downstream-submission publication contract test"),
        ),
    )


def validate_report_downstream_submission_success_contract(
    endpoint: dict[str, Any], openapi_spec: dict[str, Any] | None = None
) -> list[str]:
    from app.api.examples.downstream_submission import (
        build_report_downstream_submission_200_response_examples,
        build_report_downstream_submission_202_response_examples,
    )

    return validate_named_success_status_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=_REPORT,
        expected_by_status=(
            ("200", build_report_downstream_submission_200_response_examples()),
            ("202", build_report_downstream_submission_202_response_examples()),
        ),
        workflow_name="report-downstream-submission",
        required_test_evidence=(
            (
                _TEST + "test_report_downstream_submission_api_accepts_pack_with_support_reference",
                "accepted HTTP behavior test",
            ),
            (
                _TEST + "test_report_downstream_submission_api_returns_bounded_rejection",
                "rejected HTTP behavior test",
            ),
            (
                _TEST + "test_report_downstream_submission_api_replays_same_idempotency_key",
                "replay no-duplicate-call behavior test",
            ),
            (
                _TEST + "test_report_downstream_submission_api_returns_durable_uncertain_posture",
                "202 reconciliation-required behavior test",
            ),
            (_UNIT, "complete report downstream-submission publication contract test"),
        ),
    )


__all__ = [
    "validate_conversion_downstream_submission_success_contract",
    "validate_report_downstream_submission_success_contract",
]
