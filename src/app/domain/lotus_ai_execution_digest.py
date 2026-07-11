from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True)
class LotusAIExecutionInputEvidence:
    task_id: str
    context_summary: str
    context_payload: Mapping[str, object]
    source_refs: tuple[str, ...]
    expected_output_label: str | None

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("lotus-ai task_id is required")
        if not self.context_summary.strip():
            raise ValueError("lotus-ai context summary is required")
        if any(not source_ref.strip() for source_ref in self.source_refs):
            raise ValueError("lotus-ai source refs cannot contain blanks")


@dataclass(frozen=True)
class LotusAIExecutionOutputContent:
    status: str
    output_label: str
    message: str
    structured_output: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.status.strip():
            raise ValueError("lotus-ai execution status is required")
        if not self.output_label.strip():
            raise ValueError("lotus-ai output label is required")
        if not self.message.strip():
            raise ValueError("lotus-ai output message is required")


def lotus_ai_input_evidence_sha256(evidence: LotusAIExecutionInputEvidence) -> str:
    return _sha256(
        {
            "task_id": evidence.task_id,
            "context": {
                "summary": evidence.context_summary,
                "payload": dict(evidence.context_payload),
                "source_refs": list(evidence.source_refs),
            },
            "expected_output_label": evidence.expected_output_label,
        }
    )


def lotus_ai_output_content_sha256(content: LotusAIExecutionOutputContent) -> str:
    return _sha256(
        {
            "status": content.status,
            "output_label": content.output_label,
            "message": content.message,
            "structured_output": dict(content.structured_output),
        }
    )


def _sha256(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()
