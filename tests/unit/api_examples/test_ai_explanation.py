from __future__ import annotations

import json
from pathlib import Path

from app.api.ai_governance_models import AIExplanationEvaluationResponse
from app.api.examples.ai_explanation import build_ai_explanation_evaluation_examples
from app.domain import AIExplanationPosture
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"


def test_ai_explanation_success_examples_match_ledger_and_openapi() -> None:
    expected = build_ai_explanation_evaluation_examples()
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == OPERATION_PATH
    )
    ledger_examples = [json.loads(value) for value in endpoint["response_examples"]]
    operation = app.openapi()["paths"][OPERATION_PATH]["post"]
    openapi_examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    published = {name: metadata["value"] for name, metadata in openapi_examples.items()}

    assert ledger_examples == list(expected.values())
    assert published == expected
    assert all(AIExplanationEvaluationResponse.model_validate(value) for value in expected.values())

    fallback = expected["deterministicFallback"]
    assert fallback["verifiedOutput"] is None
    assert fallback["executionProvenancePosture"] == "not_applicable_fallback"
    assert fallback["grantsDownstreamAuthority"] is False

    for name in (
        "blockedUnsupportedClaim",
        "blockedForbiddenAction",
        "blockedUnsafeActionContent",
    ):
        blocked = expected[name]
        assert blocked["verifiedOutput"]["groundedClaims"] == []
        assert blocked["explanationText"].startswith("AI explanation was blocked because")
        assert blocked["grantsDownstreamAuthority"] is False


def test_ai_explanation_posture_schema_exposes_only_executable_states() -> None:
    assert {posture.value for posture in AIExplanationPosture} == {
        "ready_for_advisor_review",
        "fallback_used",
        "blocked_unsupported_claim",
        "blocked_forbidden_action",
    }
