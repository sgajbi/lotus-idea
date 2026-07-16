from __future__ import annotations

from dataclasses import dataclass

from app.application.runtime_evidence import RuntimeEvidenceScope


@dataclass(frozen=True)
class AdvisePolicyRuntimeEvidenceScope(RuntimeEvidenceScope):
    book_id: str = ""
    client_id: str = ""
    evaluation_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.book_id.strip() or not self.client_id.strip() or not self.evaluation_id.strip():
            raise ValueError("book_id, client_id, and evaluation_id are required")
        if self.correlation_id is None or self.trace_id is None:
            raise ValueError("correlation_id and trace_id are required")
        if not self.trace_id.strip():
            raise ValueError("trace_id must not be blank")
