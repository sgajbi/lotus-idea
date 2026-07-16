from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


REPORT_EVIDENCE_PACK_OPERATION = (
    "POST",
    "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
)
REPORT_EVIDENCE_PACK_REPLAY_TEST = (
    "tests/integration/test_review_workflow_api.py::"
    "test_report_evidence_pack_api_replays_conflicts_and_blocks_client_ready_publication"
)
REPORT_EVIDENCE_PACK_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_report_evidence_examples.py::"
    "test_report_evidence_pack_success_examples_match_ledger_and_openapi"
)


def validate_report_evidence_pack_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.report_evidence import (
        build_report_evidence_pack_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=REPORT_EVIDENCE_PACK_OPERATION,
        expected=build_report_evidence_pack_response_examples(),
        workflow_name="report-evidence-pack",
        required_test_evidence=(
            (
                REPORT_EVIDENCE_PACK_REPLAY_TEST,
                "idempotent report-evidence-pack replay integration test",
            ),
            (
                REPORT_EVIDENCE_PACK_SUCCESS_CONTRACT_TEST,
                "complete report-evidence-pack success publication contract test",
            ),
        ),
    )


__all__ = ["validate_report_evidence_pack_success_contract"]
