from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_success_contract


CANDIDATE_LIFECYCLE_OPERATION = (
    "POST",
    "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions",
)
CANDIDATE_EVIDENCE_REPLAY_OPERATION = (
    "POST",
    "/api/v1/idea-candidates/{candidateId}/evidence-replay",
)
CANDIDATE_LIFECYCLE_BEHAVIOR_TEST = (
    "tests/integration/test_review_workflow_api.py::"
    "test_lifecycle_transition_api_records_idempotent_transition"
)
CANDIDATE_EVIDENCE_REPLAY_MATCHED_TEST = (
    "tests/integration/test_candidate_evidence_replay_api.py::"
    "test_candidate_evidence_replay_api_returns_matched_posture_without_source_payloads"
)
CANDIDATE_EVIDENCE_REPLAY_COMPARISON_TEST = (
    "tests/integration/test_candidate_evidence_replay_api.py::"
    "test_candidate_evidence_replay_api_reports_hash_mismatch_and_stale_source"
)
CANDIDATE_EVIDENCE_REPLAY_EXPIRED_TEST = (
    "tests/integration/test_candidate_evidence_replay_api.py::"
    "test_candidate_evidence_replay_api_reports_expired_posture"
)
CANDIDATE_LIFECYCLE_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_candidate_state_examples.py::"
    "test_candidate_lifecycle_success_examples_match_ledger_and_openapi"
)
CANDIDATE_EVIDENCE_REPLAY_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_candidate_state_examples.py::"
    "test_candidate_evidence_replay_success_examples_match_ledger_and_openapi"
)


def validate_candidate_lifecycle_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.candidate_state import (
        build_candidate_lifecycle_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CANDIDATE_LIFECYCLE_OPERATION,
        expected=build_candidate_lifecycle_response_examples(),
        workflow_name="candidate-lifecycle",
        required_test_evidence=(
            (
                CANDIDATE_LIFECYCLE_BEHAVIOR_TEST,
                "accepted and replayed candidate-lifecycle integration test",
            ),
            (
                CANDIDATE_LIFECYCLE_SUCCESS_CONTRACT_TEST,
                "complete candidate-lifecycle success publication contract test",
            ),
        ),
    )


def validate_candidate_evidence_replay_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.candidate_state import (
        build_candidate_evidence_replay_response_examples,
    )

    return validate_named_success_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=CANDIDATE_EVIDENCE_REPLAY_OPERATION,
        expected=build_candidate_evidence_replay_response_examples(),
        workflow_name="candidate-evidence-replay",
        required_test_evidence=(
            (
                CANDIDATE_EVIDENCE_REPLAY_MATCHED_TEST,
                "matched candidate-evidence-replay integration test",
            ),
            (
                CANDIDATE_EVIDENCE_REPLAY_COMPARISON_TEST,
                "hash-mismatch and stale-source candidate-evidence-replay integration test",
            ),
            (
                CANDIDATE_EVIDENCE_REPLAY_EXPIRED_TEST,
                "expired candidate-evidence-replay integration test",
            ),
            (
                CANDIDATE_EVIDENCE_REPLAY_SUCCESS_CONTRACT_TEST,
                "complete candidate-evidence-replay success publication contract test",
            ),
        ),
    )


__all__ = [
    "validate_candidate_evidence_replay_success_contract",
    "validate_candidate_lifecycle_success_contract",
]
