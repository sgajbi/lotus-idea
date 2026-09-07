from __future__ import annotations

from collections.abc import Mapping

from fastapi import Request

from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


def request_context_id(request: Request, attribute: str) -> str | None:
    value = getattr(request.state, attribute, None)
    return str(value) if value else None


def emit_api_foundation_operation_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
    attributes: Mapping[str, str] | None = None,
) -> None:
    emit_foundation_operation_event(
        operation,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
        attributes=attributes,
    )
