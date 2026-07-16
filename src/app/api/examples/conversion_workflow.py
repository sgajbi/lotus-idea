from __future__ import annotations

from typing import Any

from app.api.conversion_governance_models import (
    ConversionIntentApiResponse,
    ConversionOutcomeApiResponse,
)
from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)


CONVERSION_INTENT_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/conversion-intents"
CONVERSION_OUTCOME_OPERATION_PATH = "/api/v1/conversion-intents/{conversionIntentId}/outcomes"
CONVERSION_INTENT_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New conversion intent accepted and persisted",
    "replayed": "Existing conversion intent replayed without duplicate mutation",
}
CONVERSION_OUTCOME_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New conversion outcome accepted and persisted",
    "replayed": "Existing conversion outcome replayed without duplicate mutation",
}


def build_conversion_intent_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_conversion_intent_response(
            {
                "conversionIntent": {
                    "conversionIntentId": "conversion-report-001",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "target": "report_evidence",
                    "sourceStatus": "approved",
                    "targetSourceAuthority": "lotus-report",
                    "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                    "evidenceContentHash": "sha256:evidence-lineage",
                    "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                    "boundary": "intent_only",
                    "reasonCodes": ["review_approved_for_conversion"],
                    "requestedAtUtc": "2026-06-21T10:15:00Z",
                    "grantsDownstreamAuthority": False,
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.conversion.intent_requested",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_conversion_intent_response(
            {
                "conversionIntent": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.conversion.intent_requested",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_conversion_outcome_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_conversion_outcome_response(
            {
                "conversionOutcome": {
                    "conversionOutcomeId": "conversion-report-outcome-001",
                    "conversionIntentId": "conversion-report-001",
                    "target": "report_evidence",
                    "status": "accepted",
                    "sourceSystem": "lotus-report",
                    "sourceEventVersion": 1,
                    "downstreamReference": "report-evidence-pack-001",
                    "supersedesConversionOutcomeId": None,
                    "correctionReason": None,
                    "boundary": "downstream_realization_required",
                    "recordedAtUtc": "2026-06-21T10:20:00Z",
                    "grantsExecutionAuthority": False,
                    "grantsClientCommunicationAuthority": False,
                    "grantsSuitabilityAuthority": False,
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.conversion.outcome_recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_conversion_outcome_response(
            {
                "conversionOutcome": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.conversion.outcome_recorded",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_conversion_intent_openapi_examples() -> dict[str, dict[str, Any]]:
    return build_named_openapi_examples(
        build_conversion_intent_response_examples(),
        CONVERSION_INTENT_SUCCESS_EXAMPLE_SUMMARIES,
    )


def build_conversion_outcome_openapi_examples() -> dict[str, dict[str, Any]]:
    return build_named_openapi_examples(
        build_conversion_outcome_response_examples(),
        CONVERSION_OUTCOME_SUCCESS_EXAMPLE_SUMMARIES,
    )


def apply_conversion_workflow_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    apply_named_response_examples(
        openapi_schema,
        operation_path=CONVERSION_INTENT_OPERATION_PATH,
        examples=build_conversion_intent_openapi_examples(),
    )
    apply_named_response_examples(
        openapi_schema,
        operation_path=CONVERSION_OUTCOME_OPERATION_PATH,
        examples=build_conversion_outcome_openapi_examples(),
    )
    return openapi_schema


def _validated_conversion_intent_response(payload: dict[str, Any]) -> dict[str, Any]:
    return ConversionIntentApiResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


def _validated_conversion_outcome_response(payload: dict[str, Any]) -> dict[str, Any]:
    return ConversionOutcomeApiResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


__all__ = [
    "CONVERSION_INTENT_OPERATION_PATH",
    "CONVERSION_INTENT_SUCCESS_EXAMPLE_SUMMARIES",
    "CONVERSION_OUTCOME_OPERATION_PATH",
    "CONVERSION_OUTCOME_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_conversion_workflow_openapi_examples",
    "build_conversion_intent_openapi_examples",
    "build_conversion_intent_response_examples",
    "build_conversion_outcome_openapi_examples",
    "build_conversion_outcome_response_examples",
]
