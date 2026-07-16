from __future__ import annotations

from typing import Any

from endpoint_contract_support import (
    json_object_examples,
    openapi_operation,
    openapi_success_object_examples,
)


AI_EXPLANATION_OPERATION = (
    "POST",
    "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
)
AI_ATTESTED_SUCCESS_TEST = (
    "tests/integration/test_attested_ai_governance_api.py::"
    "test_api_accepts_signed_bound_lotus_ai_output"
)
AI_READINESS_OPERATION = ("GET", "/api/v1/ai-explanations/readiness")
AI_READINESS_CONTRACT_TEST = (
    "tests/unit/test_ai_explanation_readiness.py::"
    "test_ai_explanation_readiness_published_examples_match_runtime_contract"
)


def validate_ai_attested_success_mode(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if operation != AI_EXPLANATION_OPERATION:
        return []

    errors: list[str] = []
    use_text = " ".join(
        (
            str(endpoint.get("purpose", "")),
            str(endpoint.get("when_to_use", "")),
        )
    )
    if "currently reject workflow output" in use_text:
        errors.append(
            f"{operation}: certification truth must not reject verified attested workflow output"
        )
    if "verified Lotus AI run attestation" not in use_text:
        errors.append(
            f"{operation}: certification truth must document verified Lotus AI run attestation"
        )

    response_examples = json_object_examples(endpoint.get("response_examples"))
    if not any(_is_verified_ai_attestation_success(example) for example in response_examples):
        errors.append(
            f"{operation}: response_examples must include verified attested AI success posture"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    if AI_ATTESTED_SUCCESS_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the attested AI API success integration test"
        )

    if openapi_spec is not None:
        operation_schema = openapi_operation(openapi_spec, operation)
        media = (
            operation_schema.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            if operation_schema is not None
            else {}
        )
        examples = media.get("examples", {}) if isinstance(media, dict) else {}
        values = [
            metadata.get("value") for metadata in examples.values() if isinstance(metadata, dict)
        ]
        if not any(
            isinstance(value, dict) and _is_verified_ai_attestation_success(value)
            for value in values
        ):
            errors.append(
                f"{operation}: OpenAPI 200 examples must include verified attested AI success"
            )
        if "unattestedLocalTestFixture" not in examples:
            errors.append(
                f"{operation}: OpenAPI 200 examples must preserve local/test fixture posture"
            )

    return errors


def validate_ai_readiness_success_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    operation = (str(endpoint["method"]).upper(), str(endpoint["path"]))
    if operation != AI_READINESS_OPERATION:
        return []

    from app.api.ai_governance_models import build_ai_explanation_readiness_response

    expected = build_ai_explanation_readiness_response().model_dump(mode="json", by_alias=True)
    errors: list[str] = []
    if expected not in json_object_examples(endpoint.get("response_examples")):
        errors.append(
            f"{operation}: response_examples must exactly match the code-owned default "
            "AI readiness response"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    if AI_READINESS_CONTRACT_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the complete AI readiness publication "
            "contract test"
        )

    if openapi_spec is not None and expected not in openapi_success_object_examples(
        openapi_spec,
        operation,
    ):
        errors.append(
            f"{operation}: OpenAPI success example must exactly match the code-owned default "
            "AI readiness response"
        )
    return errors


def _is_verified_ai_attestation_success(payload: dict[str, Any]) -> bool:
    return (
        payload.get("executionProvenancePosture") == "lotus_ai_attestation_verified"
        and payload.get("lotusAiRuntimeExecuted") is True
        and payload.get("grantsDownstreamAuthority") is False
        and payload.get("supportedFeaturePromoted") is False
    )
