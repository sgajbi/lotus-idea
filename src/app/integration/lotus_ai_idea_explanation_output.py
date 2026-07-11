from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.lotus_ai_execution_digest import LotusAIExecutionOutputContent


class LotusAIExecutionOutputEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    output_label: str
    message: str
    structured_output: dict[str, Any]

    def to_domain(self) -> LotusAIExecutionOutputContent:
        return LotusAIExecutionOutputContent(
            status=self.status,
            output_label=self.output_label,
            message=self.message,
            structured_output=self.structured_output,
        )
