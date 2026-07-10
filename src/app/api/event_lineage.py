from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from app.domain import EventLineageContext, EventLineageOrigin


CAUSATION_ID_HEADER = "X-Causation-Id"

EventCausationHeader = Annotated[
    str | None,
    Header(
        alias=CAUSATION_ID_HEADER,
        description=(
            "Optional product-safe parent event or workflow identifier. Supply only when "
            "this mutation was caused by a distinct governed parent event."
        ),
    ),
]


def event_lineage_from_request(
    request: Request,
    *,
    causation_id: str | None = None,
) -> EventLineageContext:
    correlation_id = _request_context_id(request, "correlation_id")
    trace_id = _request_context_id(request, "trace_id")
    return EventLineageContext(
        correlation_id=correlation_id,
        trace_id=trace_id,
        causation_id=causation_id,
        origin=(
            EventLineageOrigin.PARENT_EVENT
            if causation_id is not None
            else EventLineageOrigin.REQUEST
        ),
    )


def _request_context_id(request: Request, field_name: str) -> str:
    value = getattr(request.state, field_name, None)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} is required on request state")
    return value
