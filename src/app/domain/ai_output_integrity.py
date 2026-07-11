from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence
import unicodedata

AI_OUTPUT_INTEGRITY_VERSION = "lotus-idea.ai-output-integrity.v1"
AI_OUTPUT_INTEGRITY_PRE_V1_UNVERIFIABLE = "lotus-idea.ai-output-integrity.pre-v1-unverifiable"


@dataclass(frozen=True)
class AIOutputIntegrity:
    version: str
    digest: str

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("output integrity version is required")
        if not self.digest.startswith("sha256:") or len(self.digest) != 71:
            raise ValueError("output integrity digest must be a sha256 digest")


def build_ai_output_integrity(
    *,
    explanation_text: str,
    claims: Sequence[Mapping[str, Any]],
    proposed_actions: Sequence[Mapping[str, Any]],
    workflow_pack_id: str,
    workflow_pack_version: str,
    evaluation_ref: str,
    action_policy_version: str,
    output_kind: str,
    policy_metadata: Mapping[str, Any] | None = None,
) -> AIOutputIntegrity:
    payload = {
        "action_policy_version": action_policy_version,
        "claims": [_canonical_mapping(claim) for claim in claims],
        "evaluation_ref": _canonical_text(evaluation_ref),
        "explanation_text": _canonical_text(explanation_text),
        "integrity_version": AI_OUTPUT_INTEGRITY_VERSION,
        "output_kind": _canonical_text(output_kind),
        "policy_metadata": _canonical_mapping(policy_metadata or {}),
        "proposed_actions": [_canonical_mapping(action) for action in proposed_actions],
        "workflow_pack_id": _canonical_text(workflow_pack_id),
        "workflow_pack_version": _canonical_text(workflow_pack_version),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return AIOutputIntegrity(
        version=AI_OUTPUT_INTEGRITY_VERSION,
        digest=f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}",
    )


def _canonical_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _canonical_value(item) for key, item in sorted(value.items())}


def _canonical_value(value: Any) -> Any:
    if isinstance(value, str):
        return _canonical_text(value)
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _canonical_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
