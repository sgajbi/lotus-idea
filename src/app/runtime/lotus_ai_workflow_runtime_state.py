from __future__ import annotations

import os

from app.infrastructure.lotus_ai import HttpLotusAIWorkflowRuntime
from app.runtime.lotus_ai_attestation_state import LOTUS_AI_BASE_URL_ENV


LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_LOTUS_AI_RUNTIME_TIMEOUT_SECONDS"

_WORKFLOW_RUNTIME: HttpLotusAIWorkflowRuntime | None = None


def get_lotus_ai_workflow_runtime() -> HttpLotusAIWorkflowRuntime:
    global _WORKFLOW_RUNTIME
    if _WORKFLOW_RUNTIME is None:
        base_url = os.getenv(LOTUS_AI_BASE_URL_ENV, "").strip()
        if not base_url:
            raise RuntimeError(
                f"{LOTUS_AI_BASE_URL_ENV} is required for governed AI workflow execution"
            )
        _WORKFLOW_RUNTIME = HttpLotusAIWorkflowRuntime(
            base_url=base_url,
            timeout_seconds=_timeout_seconds(),
        )
    return _WORKFLOW_RUNTIME


def close_lotus_ai_workflow_runtime() -> None:
    global _WORKFLOW_RUNTIME
    if _WORKFLOW_RUNTIME is not None:
        _WORKFLOW_RUNTIME.close()
        _WORKFLOW_RUNTIME = None


def reset_lotus_ai_workflow_runtime() -> None:
    close_lotus_ai_workflow_runtime()


def _timeout_seconds() -> float:
    raw = os.getenv(LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV, "10.0").strip()
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV} must be numeric") from exc
    if timeout <= 0 or timeout > 30:
        raise RuntimeError(
            f"{LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV} must be greater than 0 and at most 30"
        )
    return timeout
