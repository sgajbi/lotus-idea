from datetime import UTC, datetime
from typing import Any, Callable

import pytest

from app.domain.ai_governance import AIProposedActionType
from app.domain.lotus_ai_execution_digest import lotus_ai_output_content_sha256
from app.application.lotus_ai_idea_explanation_output import (
    map_lotus_ai_idea_workflow_output,
)
from app.integration.lotus_ai_idea_explanation_output import LotusAIExecutionOutputEvidence


VERIFIED_AT = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)


def test_maps_exact_hashed_producer_output_to_idea_workflow_output() -> None:
    evidence = _evidence()

    output = map_lotus_ai_idea_workflow_output(
        evidence.to_domain(),
        request_id="request-001",
        workflow_pack_id="lotus-ai:idea-explanation:v1",
        workflow_pack_version="v1",
        verifier_ran_at_utc=VERIFIED_AT,
    )

    assert output.output_id == "output-001"
    assert output.explanation_text == evidence.message
    assert output.claims[0].source_product_ids == ("lotus-core:PortfolioStateSnapshot:v1",)
    assert output.proposed_actions[0].action_type is AIProposedActionType.ADVISOR_REVIEW
    assert lotus_ai_output_content_sha256(evidence.to_domain()) == (
        "0894af1f1c81fe4e6991c605ed94ba8e68354fb45772910c0aed1cf0c27b90ec"
    )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: payload.update(status="FAILED"), "must be completed"),
        (lambda payload: payload.update(output_label="STRUCTURED_OUTPUT"), "label is invalid"),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"].update(
                explanation_text="different"
            ),
            "message does not match",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"].update(claims=[]),
            "claims are required",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"].update(
                proposed_actions=[]
            ),
            "proposed actions are required",
        ),
        (
            lambda payload: payload["structured_output"].update(idea_workflow_output=None),
            "missing idea_workflow_output",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"].update(
                claims=["not-an-object"]
            ),
            "claims must contain objects",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"].update(
                output_id=" "
            ),
            "output_id is required",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"]["claims"][
                0
            ].update(source_product_ids=[]),
            "source_product_ids is required",
        ),
        (
            lambda payload: payload["structured_output"]["idea_workflow_output"]["claims"][
                0
            ].update(source_product_ids=["lotus-core:PortfolioStateSnapshot:v1", None]),
            "source_product_ids contains invalid values",
        ),
    ],
)
def test_rejects_non_binding_or_malformed_producer_output(
    mutator: Callable[[dict[str, Any]], None], message: str
) -> None:
    payload = _evidence().model_dump()
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        map_lotus_ai_idea_workflow_output(
            LotusAIExecutionOutputEvidence.model_validate(payload).to_domain(),
            request_id="request-001",
            workflow_pack_id="lotus-ai:idea-explanation:v1",
            workflow_pack_version="v1",
            verifier_ran_at_utc=VERIFIED_AT,
        )


def _evidence() -> LotusAIExecutionOutputEvidence:
    message = "The evidence supports an internal advisor review of idle cash."
    return LotusAIExecutionOutputEvidence(
        status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        message=message,
        structured_output={
            "idea_workflow_output": {
                "output_id": "output-001",
                "explanation_text": message,
                "claims": [
                    {
                        "claim_id": "claim-001",
                        "claim_text": "Cash attention is supported by Core portfolio state.",
                        "source_product_ids": ["lotus-core:PortfolioStateSnapshot:v1"],
                    }
                ],
                "proposed_actions": [
                    {
                        "action_type": "advisor_review",
                        "action_label": "Review evidence internally",
                    }
                ],
            }
        },
    )
