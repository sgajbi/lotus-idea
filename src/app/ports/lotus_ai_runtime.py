from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class LotusAIWorkflowRuntime(Protocol):
    """Executes one governed Lotus AI workflow-pack request."""

    def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]: ...


__all__ = ["LotusAIWorkflowRuntime"]
