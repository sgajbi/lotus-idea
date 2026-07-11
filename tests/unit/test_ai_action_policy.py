from __future__ import annotations

import pytest

from app.domain.ai_action_policy import (
    AI_ACTION_POLICY_VERSION,
    AIActionPolicyReason,
    AIProposedActionType,
    evaluate_ai_action_policy,
)


@pytest.mark.parametrize(
    ("action_type", "label", "canonical_label"),
    [
        (
            AIProposedActionType.ADVISOR_REVIEW,
            "Route to advisor review",
            "Review the evidence as an advisor",
        ),
        (
            AIProposedActionType.ADVISOR_REVIEW,
            "Review evidence internally.",
            "Review the evidence as an advisor",
        ),
        (
            AIProposedActionType.REQUEST_MISSING_EVIDENCE,
            "Request missing governed evidence",
            "Request the missing governed evidence",
        ),
    ],
)
def test_policy_accepts_only_golden_safe_labels_and_returns_server_label(
    action_type: AIProposedActionType,
    label: str,
    canonical_label: str,
) -> None:
    decision = evaluate_ai_action_policy(action_type, label)

    assert decision.allowed is True
    assert decision.reason is AIActionPolicyReason.ALLOWED
    assert decision.canonical_label == canonical_label
    assert decision.policy_version == AI_ACTION_POLICY_VERSION
    assert decision.canonical_label != label


@pytest.mark.parametrize(
    "label",
    [
        "Execute trade immediately",
        "Ex3cute tr@de immediately!!!",
        "Place the order",
        "SELL NOW",
        "Approve suitability",
        "Approve the compliance",
        "Approve mandate",
        "Email the client",
        "Communicate with client",
        "Publish this recommendation",
        "Final investment recommendation",
    ],
)
@pytest.mark.parametrize(
    "action_type",
    [
        AIProposedActionType.ADVISOR_REVIEW,
        AIProposedActionType.REQUEST_MISSING_EVIDENCE,
    ],
)
def test_policy_blocks_forbidden_directives_hidden_in_allowed_action_type(
    action_type: AIProposedActionType,
    label: str,
) -> None:
    decision = evaluate_ai_action_policy(action_type, label)

    assert decision.allowed is False
    assert decision.reason is AIActionPolicyReason.FORBIDDEN_ACTION_CONTENT
    assert label not in decision.canonical_label


@pytest.mark.parametrize(
    "action_type",
    [
        AIProposedActionType.FINAL_INVESTMENT_RECOMMENDATION,
        AIProposedActionType.SUITABILITY_APPROVAL,
        AIProposedActionType.COMPLIANCE_APPROVAL,
        AIProposedActionType.MANDATE_APPROVAL,
        AIProposedActionType.TRADE_OR_ORDER,
        AIProposedActionType.CLIENT_COMMUNICATION,
    ],
)
def test_policy_blocks_every_forbidden_structured_action(action_type: AIProposedActionType) -> None:
    decision = evaluate_ai_action_policy(action_type, "Route to advisor review")

    assert decision.allowed is False
    assert decision.reason is AIActionPolicyReason.FORBIDDEN_ACTION_TYPE
    assert decision.canonical_label == "Action blocked by Lotus Idea policy"


@pytest.mark.parametrize(
    "label",
    [
        "Review the opportunity",
        "Aprobar idoneidad",
        "Review evidence internally then proceed",
        "x" * 161,
    ],
)
def test_policy_fails_closed_on_ambiguous_or_unsupported_content(label: str) -> None:
    decision = evaluate_ai_action_policy(AIProposedActionType.ADVISOR_REVIEW, label)

    assert decision.allowed is False
    assert decision.reason is AIActionPolicyReason.AMBIGUOUS_ACTION_CONTENT


def test_policy_does_not_match_forbidden_fragments_across_word_boundaries() -> None:
    decision = evaluate_ai_action_policy(
        AIProposedActionType.ADVISOR_REVIEW,
        "Portrait orderliness",
    )

    assert decision.reason is AIActionPolicyReason.AMBIGUOUS_ACTION_CONTENT
