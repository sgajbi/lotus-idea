from __future__ import annotations

import pytest

from app.domain.ai_metadata_policy import (
    AI_METADATA_ENVELOPE_VERSION,
    InvalidAIMetadataEnvelope,
    validate_ai_metadata_envelope,
)


def test_ai_metadata_envelope_accepts_only_closed_safe_values() -> None:
    assert AI_METADATA_ENVELOPE_VERSION == "lotus-idea.ai-metadata-envelope.v1"
    assert validate_ai_metadata_envelope(
        {"channel": "advisor-workbench"},
        purpose="missing_evidence_check",
    ) == {"channel": "advisor-workbench"}
    assert validate_ai_metadata_envelope(
        {
            "channel": "advisor-workbench",
            "audience": "internal_advisor_review",
        },
        purpose="advisor_rationale_draft",
    ) == {
        "channel": "advisor-workbench",
        "audience": "internal_advisor_review",
    }


@pytest.mark.parametrize(
    "metadata",
    [
        {"customerEmail": "client@example.com"},
        {"accountNumber": "ACCT-123"},
        {"authorization": "Bearer secret"},
        {"neutral": "client@example.com"},
        {"channel": "client@example.com"},
        {"channel": "Bearer eyJhbGciOiJIUzI1NiJ9.secret"},
        {"channel": "ACCT-123"},
    ],
)
def test_ai_metadata_envelope_rejects_unknown_keys_and_value_only_leakage(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(InvalidAIMetadataEnvelope):
        validate_ai_metadata_envelope(metadata, purpose="missing_evidence_check")


def test_ai_metadata_envelope_enforces_purpose_count_length_and_controls() -> None:
    invalid_cases = (
        (
            {"audience": "internal_advisor_review"},
            "missing_evidence_check",
            "not allowed for this purpose",
        ),
        (
            {"channel": "advisor-workbench", "audience": "internal_advisor_review", "x": "y"},
            "advisor_rationale_draft",
            "too many fields",
        ),
        ({"x" * 33: "value"}, "missing_evidence_check", "key exceeds"),
        ({"channel": "x" * 65}, "missing_evidence_check", "value exceeds"),
        ({"channel": "advisor-workbench\n"}, "missing_evidence_check", "trimmed"),
        ({"chan\u0000nel": "advisor-workbench"}, "missing_evidence_check", "control"),
    )
    for metadata, purpose, message in invalid_cases:
        with pytest.raises(InvalidAIMetadataEnvelope, match=message):
            validate_ai_metadata_envelope(metadata, purpose=purpose)
