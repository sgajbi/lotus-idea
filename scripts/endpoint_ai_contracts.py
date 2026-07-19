# ruff: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

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
AI_EVALUATION_SUCCESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_ai_explanation.py::"
    "test_ai_explanation_success_examples_match_ledger_and_openapi"
)
AI_READINESS_OPERATION = ("GET", "/api/v1/ai-explanations/readiness")
AI_READINESS_CONTRACT_TEST = (
    "tests/unit/test_ai_explanation_readiness.py::"
    "test_ai_explanation_readiness_published_examples_match_runtime_contract"
)


def validate_ai_evaluation_success_contract(
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

    from app.api.examples.ai_explanation import build_ai_explanation_evaluation_examples

    expected = build_ai_explanation_evaluation_examples()
    if json_object_examples(endpoint.get("response_examples")) != tuple(expected.values()):
        errors.append(
            f"{operation}: response_examples must exactly match every code-owned AI evaluation "
            "success mode"
        )

    test_evidence = tuple(str(value) for value in endpoint.get("test_evidence", ()))
    if AI_ATTESTED_SUCCESS_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the attested AI API success integration test"
        )
    if AI_EVALUATION_SUCCESS_CONTRACT_TEST not in test_evidence:
        errors.append(
            f"{operation}: test_evidence must cite the complete AI evaluation publication "
            "contract test"
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
        published = {
            str(name): metadata.get("value")
            for name, metadata in examples.items()
            if isinstance(metadata, dict)
        }
        if published != expected:
            errors.append(
                f"{operation}: OpenAPI 200 examples must exactly match every named code-owned "
                "AI evaluation success mode"
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
