from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.event_lineage import event_lineage_from_request
from app.domain import EventLineageOrigin


def test_request_lineage_preserves_correlation_and_trace_as_distinct_identifiers() -> None:
    request = _request_with_lineage("corr-request-001", "trace-request-001")

    lineage = event_lineage_from_request(request)

    assert lineage.correlation_id == "corr-request-001"
    assert lineage.trace_id == "trace-request-001"
    assert lineage.causation_id is None
    assert lineage.origin is EventLineageOrigin.REQUEST


def test_request_lineage_records_explicit_parent_event_as_causation() -> None:
    request = _request_with_lineage("corr-workflow-001", "trace-request-002")

    lineage = event_lineage_from_request(request, causation_id="event-parent-001")

    assert lineage.correlation_id == "corr-workflow-001"
    assert lineage.trace_id == "trace-request-002"
    assert lineage.causation_id == "event-parent-001"
    assert lineage.origin is EventLineageOrigin.PARENT_EVENT


@pytest.mark.parametrize("missing_attribute", ["correlation_id", "trace_id"])
def test_request_lineage_fails_closed_without_middleware_context(missing_attribute: str) -> None:
    request = _request_with_lineage("corr-request-001", "trace-request-001")
    delattr(request.state, missing_attribute)

    with pytest.raises(ValueError, match=missing_attribute):
        event_lineage_from_request(request)


def test_request_lineage_rejects_sensitive_parent_identifier() -> None:
    request = _request_with_lineage("corr-request-001", "trace-request-001")

    with pytest.raises(ValueError, match="causation_id"):
        event_lineage_from_request(request, causation_id="bearer-secret-token")


def _request_with_lineage(correlation_id: str, trace_id: str) -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.correlation_id = correlation_id
    request.state.trace_id = trace_id
    return request
