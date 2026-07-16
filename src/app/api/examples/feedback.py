from __future__ import annotations

from typing import Any

from app.api.review_workflow_models import FeedbackResponse


FEEDBACK_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/feedback"
FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New feedback event accepted and persisted",
    "replayed": "Existing feedback resource replayed without duplicate mutation",
}


def build_feedback_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_response(
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
        "replayed": _validated_response(
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


def build_feedback_openapi_examples() -> dict[str, dict[str, Any]]:
    examples = build_feedback_response_examples()
    return {
        name: {
            "summary": FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES[name],
            "value": value,
        }
        for name, value in examples.items()
    }


def apply_feedback_openapi_examples(openapi_schema: dict[str, Any]) -> dict[str, Any]:
    operation = openapi_schema["paths"][FEEDBACK_OPERATION_PATH]["post"]
    media = operation["responses"]["200"]["content"]["application/json"]
    media.pop("example", None)
    media["examples"] = build_feedback_openapi_examples()
    return openapi_schema


def _validated_response(payload: dict[str, Any]) -> dict[str, Any]:
    return FeedbackResponse.model_validate(payload).model_dump(mode="json", by_alias=True)


__all__ = [
    "FEEDBACK_OPERATION_PATH",
    "FEEDBACK_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_feedback_openapi_examples",
    "build_feedback_openapi_examples",
    "build_feedback_response_examples",
]
