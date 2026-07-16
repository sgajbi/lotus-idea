from __future__ import annotations

from typing import Any

from app.api.review_workflow_models import FeedbackResponse, ReviewActionResponse


REVIEW_ACTION_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/review-actions"
FEEDBACK_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/feedback"
REVIEW_ACTION_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New review decision accepted and persisted",
    "replayed": "Existing review decision replayed without duplicate mutation",
}
FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New feedback event accepted and persisted",
    "replayed": "Existing feedback resource replayed without duplicate mutation",
}


def build_review_action_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_review_action_response(
            {
                "reviewDecision": {
                    "reviewId": "review-suppress-001",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                    "action": "suppress",
                    "resultingPosture": "suppressed",
                    "actorRole": "advisor",
                    "reasonCodes": ["review_suppressed", "review_required"],
                    "decidedAtUtc": "2026-06-21T10:05:00Z",
                    "suppressionReason": "manual_suppression",
                    "snoozedUntilUtc": None,
                    "grantsDownstreamAuthority": False,
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "generated",
                    "reviewPosture": "suppressed",
                    "auditEventType": "idea.review.decision_recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_review_action_response(
            {
                "reviewDecision": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "generated",
                    "reviewPosture": "suppressed",
                    "auditEventType": "idea.review.decision_recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_feedback_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_feedback_response(
            {
                "feedbackEvent": {
                    "feedbackId": "feedback-useful-001",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                    "outcome": "useful",
                    "actorRole": "advisor",
                    "reasonCodes": ["feedback_recorded", "review_required"],
                    "recordedAtUtc": "2026-06-21T10:06:00Z",
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "generated",
                    "reviewPosture": "advisor_review_required",
                    "auditEventType": "idea.feedback.recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_feedback_response(
            {
                "feedbackEvent": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "generated",
                    "reviewPosture": "advisor_review_required",
                    "auditEventType": "idea.feedback.recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_review_action_openapi_examples() -> dict[str, dict[str, Any]]:
    return _build_openapi_examples(
        build_review_action_response_examples(),
        REVIEW_ACTION_SUCCESS_EXAMPLE_SUMMARIES,
    )


def build_feedback_openapi_examples() -> dict[str, dict[str, Any]]:
    return _build_openapi_examples(
        build_feedback_response_examples(),
        FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES,
    )


def apply_review_workflow_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    _apply_operation_examples(
        openapi_schema,
        REVIEW_ACTION_OPERATION_PATH,
        build_review_action_openapi_examples(),
    )
    _apply_operation_examples(
        openapi_schema,
        FEEDBACK_OPERATION_PATH,
        build_feedback_openapi_examples(),
    )
    return openapi_schema


def _build_openapi_examples(
    examples: dict[str, dict[str, Any]],
    summaries: dict[str, str],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "summary": summaries[name],
            "value": value,
        }
        for name, value in examples.items()
    }


def _apply_operation_examples(
    openapi_schema: dict[str, Any],
    operation_path: str,
    examples: dict[str, dict[str, Any]],
) -> None:
    operation = openapi_schema["paths"][operation_path]["post"]
    media = operation["responses"]["200"]["content"]["application/json"]
    media.pop("example", None)
    media["examples"] = examples


def _validated_review_action_response(payload: dict[str, Any]) -> dict[str, Any]:
    return ReviewActionResponse.model_validate(payload).model_dump(mode="json", by_alias=True)


def _validated_feedback_response(payload: dict[str, Any]) -> dict[str, Any]:
    return FeedbackResponse.model_validate(payload).model_dump(mode="json", by_alias=True)


__all__ = [
    "FEEDBACK_OPERATION_PATH",
    "FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES",
    "REVIEW_ACTION_OPERATION_PATH",
    "REVIEW_ACTION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_review_workflow_openapi_examples",
    "build_feedback_openapi_examples",
    "build_feedback_response_examples",
    "build_review_action_openapi_examples",
    "build_review_action_response_examples",
]
