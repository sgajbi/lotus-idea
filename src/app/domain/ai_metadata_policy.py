from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
import unicodedata

AI_METADATA_ENVELOPE_VERSION = "lotus-idea.ai-metadata-envelope.v1"
AI_METADATA_MAX_FIELDS = 2
AI_METADATA_MAX_KEY_LENGTH = 32
AI_METADATA_MAX_VALUE_LENGTH = 64

_ALL_PURPOSES = frozenset(
    {
        "missing_evidence_check",
        "unsupported_claim_verification",
        "advisor_rationale_draft",
        "meeting_preparation_draft",
    }
)
_DRAFTING_PURPOSES = frozenset({"advisor_rationale_draft", "meeting_preparation_draft"})
_FIELD_POLICY = {
    "channel": (_ALL_PURPOSES, frozenset({"advisor-workbench"})),
    "audience": (_DRAFTING_PURPOSES, frozenset({"internal_advisor_review"})),
}


class InvalidAIMetadataEnvelope(ValueError):
    """Raised when provider-bound AI metadata is outside the approved envelope."""


def validate_ai_metadata_envelope(
    metadata: Mapping[str, str],
    *,
    purpose: str,
) -> Mapping[str, str]:
    if len(metadata) > AI_METADATA_MAX_FIELDS:
        raise InvalidAIMetadataEnvelope("AI metadata envelope contains too many fields")
    approved: dict[str, str] = {}
    for key, value in metadata.items():
        _validate_text_shape(key, field="key", max_length=AI_METADATA_MAX_KEY_LENGTH)
        _validate_text_shape(value, field="value", max_length=AI_METADATA_MAX_VALUE_LENGTH)
        policy = _FIELD_POLICY.get(key)
        if policy is None:
            raise InvalidAIMetadataEnvelope("AI metadata envelope contains unsupported fields")
        allowed_purposes, allowed_values = policy
        if purpose not in allowed_purposes:
            raise InvalidAIMetadataEnvelope("AI metadata field is not allowed for this purpose")
        if value not in allowed_values:
            raise InvalidAIMetadataEnvelope("AI metadata value is not approved")
        approved[key] = value
    return MappingProxyType(approved)


def _validate_text_shape(value: str, *, field: str, max_length: int) -> None:
    if not value or value != value.strip():
        raise InvalidAIMetadataEnvelope(f"AI metadata {field} must be non-blank and trimmed")
    if len(value) > max_length:
        raise InvalidAIMetadataEnvelope(f"AI metadata {field} exceeds the length budget")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise InvalidAIMetadataEnvelope(f"AI metadata {field} contains control characters")
