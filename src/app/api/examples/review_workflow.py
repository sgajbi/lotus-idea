from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
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
    accepted = _validated_review_action_response(
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
                "acceptedAtUtc": "2026-06-21T10:05:01Z",
                "acceptanceTimeSource": "server_accepted",
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
    )
    return {
        "accepted": accepted,
        "replayed": _replayed_example(accepted, _validated_review_action_response),
    }


def build_feedback_response_examples() -> dict[str, dict[str, Any]]:
    accepted = _validated_feedback_response(
        {
            "feedbackEvent": {
                "feedbackId": "feedback-useful-001",
                "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                "taxonomyVersion": "idea-feedback-taxonomy-v1",
                "outcome": "useful",
                "reason": "relevant",
                "actorRole": "advisor",
                "recordedAtUtc": "2026-06-21T10:06:00Z",
                "acceptedAtUtc": "2026-06-21T10:06:01Z",
                "acceptanceTimeSource": "server_accepted",
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
    )
    return {
        "accepted": accepted,
        "replayed": _replayed_example(accepted, _validated_feedback_response),
    }


def _replayed_example(
    accepted: dict[str, Any],
    validate: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    return validate(
        {
            **accepted,
            "persistence": {
                **accepted["persistence"],
                "decision": "replayed",
            },
        }
    )


def build_review_action_openapi_examples() -> dict[str, dict[str, Any]]:
    return build_named_openapi_examples(
        build_review_action_response_examples(),
        REVIEW_ACTION_SUCCESS_EXAMPLE_SUMMARIES,
    )


def build_feedback_openapi_examples() -> dict[str, dict[str, Any]]:
    return build_named_openapi_examples(
        build_feedback_response_examples(),
        FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES,
    )


def apply_review_workflow_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    apply_named_response_examples(
        openapi_schema,
        operation_path=REVIEW_ACTION_OPERATION_PATH,
        examples=build_review_action_openapi_examples(),
    )
    apply_named_response_examples(
        openapi_schema,
        operation_path=FEEDBACK_OPERATION_PATH,
        examples=build_feedback_openapi_examples(),
    )
    return openapi_schema


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
