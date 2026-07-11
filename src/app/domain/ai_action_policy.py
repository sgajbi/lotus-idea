from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata


AI_ACTION_POLICY_VERSION = "lotus-idea.ai-action-content-policy.v1"
MAX_ACTION_LABEL_LENGTH = 160


class AIProposedActionType(StrEnum):
    ADVISOR_REVIEW = "advisor_review"
    REQUEST_MISSING_EVIDENCE = "request_missing_evidence"
    FINAL_INVESTMENT_RECOMMENDATION = "final_investment_recommendation"
    SUITABILITY_APPROVAL = "suitability_approval"
    COMPLIANCE_APPROVAL = "compliance_approval"
    MANDATE_APPROVAL = "mandate_approval"
    TRADE_OR_ORDER = "trade_or_order"
    CLIENT_COMMUNICATION = "client_communication"


class AIActionPolicyReason(StrEnum):
    ALLOWED = "allowed"
    FORBIDDEN_ACTION_TYPE = "forbidden_action_type"
    FORBIDDEN_ACTION_CONTENT = "forbidden_action_content"
    AMBIGUOUS_ACTION_CONTENT = "ambiguous_action_content"


@dataclass(frozen=True)
class AIActionPolicyDecision:
    allowed: bool
    canonical_label: str
    reason: AIActionPolicyReason
    policy_version: str = AI_ACTION_POLICY_VERSION


_CANONICAL_LABELS = {
    AIProposedActionType.ADVISOR_REVIEW: "Review the evidence as an advisor",
    AIProposedActionType.REQUEST_MISSING_EVIDENCE: "Request the missing governed evidence",
}
_BLOCKED_LABEL = "Action blocked by Lotus Idea policy"
_SAFE_LABEL_PATTERNS = {
    AIProposedActionType.ADVISOR_REVIEW: re.compile(
        r"^(?:route\s+to\s+)?advisor\s+review$|^review\s+(?:the\s+)?evidence(?:\s+internally)?$"
    ),
    AIProposedActionType.REQUEST_MISSING_EVIDENCE: re.compile(
        r"^request\s+(?:the\s+)?missing\s+(?:governed\s+)?evidence$"
    ),
}
_FORBIDDEN_PATTERNS = (
    re.compile(r"\b(?:execute|place|submit|create|send)\s+(?:a\s+|the\s+)?(?:trade|order)\b"),
    re.compile(r"\b(?:buy|sell|trade|rebalance)\s+(?:now|immediately|the\s+portfolio)\b"),
    re.compile(r"\bapprove\s+(?:the\s+)?(?:suitability|compliance|mandate)\b"),
    re.compile(r"\b(?:email|message|contact|notify|communicate\s+with)\s+(?:the\s+)?client\b"),
    re.compile(r"\bpublish\s+(?:this\s+|the\s+)?(?:recommendation|communication)\b"),
    re.compile(r"\bfinal\s+(?:investment\s+)?recommendation\b"),
)
_LEET_TRANSLATION = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)


def evaluate_ai_action_policy(
    action_type: AIProposedActionType,
    action_label: str,
) -> AIActionPolicyDecision:
    canonical = _CANONICAL_LABELS.get(action_type, _BLOCKED_LABEL)
    if action_type not in _CANONICAL_LABELS:
        return AIActionPolicyDecision(False, canonical, AIActionPolicyReason.FORBIDDEN_ACTION_TYPE)
    if len(action_label) > MAX_ACTION_LABEL_LENGTH or not action_label.isascii():
        return AIActionPolicyDecision(
            False,
            canonical,
            AIActionPolicyReason.AMBIGUOUS_ACTION_CONTENT,
        )
    normalized = _normalize_action_label(action_label)
    if any(pattern.search(normalized) for pattern in _FORBIDDEN_PATTERNS):
        return AIActionPolicyDecision(
            False,
            canonical,
            AIActionPolicyReason.FORBIDDEN_ACTION_CONTENT,
        )
    if not _SAFE_LABEL_PATTERNS[action_type].fullmatch(normalized):
        return AIActionPolicyDecision(
            False,
            canonical,
            AIActionPolicyReason.AMBIGUOUS_ACTION_CONTENT,
        )
    return AIActionPolicyDecision(True, canonical, AIActionPolicyReason.ALLOWED)


def _normalize_action_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().translate(_LEET_TRANSLATION)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())
