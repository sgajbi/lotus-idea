from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class LotusAIWorkflowRuntimeUnavailable(RuntimeError):
    """Raised when the governed Lotus AI workflow runtime cannot be reached."""


class InvalidLotusAIWorkflowRuntimeResponse(RuntimeError):
    """Raised when Lotus AI returns a non-object or unsuccessful response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LotusAIWorkflowRuntime(Protocol):
    """Executes one governed Lotus AI workflow-pack request."""

    async def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]: ...

    async def get_run_attestation(self, run_id: str) -> Mapping[str, object]: ...


__all__ = [
    "InvalidLotusAIWorkflowRuntimeResponse",
    "LotusAIWorkflowRuntime",
    "LotusAIWorkflowRuntimeUnavailable",
]
