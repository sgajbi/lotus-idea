import json
import logging

import pytest
from _pytest.logging import LogCaptureFixture

from app.observability import (
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_METRIC_LABELS,
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    configure_logging,
    emit_foundation_operation_event,
    emit_operation_event,
    emit_request_diagnostic_event,
)
from app.observability.logging import log_event


def test_configure_logging_sets_product_safe_message_format() -> None:
    configure_logging()
    assert logging.getLogger().level in {logging.INFO, logging.WARNING}


def test_log_event_emits_structured_json(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        log_event("idea.test", service="lotus-idea", status="ok")

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "idea.test",
        "service": "lotus-idea",
        "status": "ok",
    }


def test_request_diagnostic_event_logs_route_template_only(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        emit_request_diagnostic_event(
            "request.http_error",
            route="/api/v1/idea-candidates/{candidateId}",
            method="GET",
            status_code=404,
        )

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "request.http_error",
        "method": "GET",
        "route": "/api/v1/idea-candidates/{candidateId}",
        "service": "lotus-idea",
        "status_code": 404,
    }


def test_request_diagnostic_event_rejects_raw_or_unknown_diagnostics() -> None:
    with pytest.raises(ValueError, match="unsupported request diagnostic event"):
        emit_request_diagnostic_event("request.raw", route="/health", method="GET")
    with pytest.raises(ValueError, match="route must be a route template"):
        emit_request_diagnostic_event(
            "request.http_error",
            route="/api/v1/idea-candidates/abc?debug=true",
            method="GET",
        )


def test_operation_event_metric_labels_are_bounded_and_product_safe() -> None:
    event = OperationEvent(
        operation=IdeaOperation.SOURCE_INGESTION_READINESS_READ,
        outcome=OperationOutcome.BLOCKED,
        source_authority="lotus-core",
        supportability_status=OperationSupportability.NOT_CERTIFIED,
    )

    labels = event.metric_labels()

    assert tuple(labels) == OPERATION_METRIC_LABELS
    assert labels == {
        "operation": "source_ingestion_readiness_read",
        "outcome": "blocked",
        "supportability_status": "not_certified",
        "source_authority": "lotus-core",
        "durable_storage_backed": "false",
        "supported_feature_promoted": "false",
    }
    assert FORBIDDEN_OPERATION_FIELD_KEYS.isdisjoint(labels)


def test_operation_event_rejects_sensitive_attributes() -> None:
    with pytest.raises(ValueError, match="sensitive keys"):
        OperationEvent(
            operation=IdeaOperation.CONVERSION_INTENT,
            outcome=OperationOutcome.PERMISSION_DENIED,
            attributes={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )


def test_emit_operation_event_logs_without_sensitive_labels(
    caplog: LogCaptureFixture,
) -> None:
    event = OperationEvent(
        operation=IdeaOperation.CONVERSION_OUTCOME,
        outcome=OperationOutcome.NOT_FOUND,
        source_authority="lotus-idea",
        error_code="conversion_resource_not_found",
    )

    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        emit_operation_event(event)

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "durable_storage_backed": False,
        "error_code": "conversion_resource_not_found",
        "event": "idea.operation.conversion_outcome",
        "operation": "conversion_outcome",
        "outcome": "not_found",
        "service": "lotus-idea",
        "source_authority": "lotus-idea",
        "supportability_status": "foundation_only",
        "supported_feature_promoted": False,
    }
    assert FORBIDDEN_OPERATION_FIELD_KEYS.isdisjoint(payload)


def test_emit_foundation_operation_event_defaults_to_unpromoted_foundation(
    caplog: LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        emit_foundation_operation_event(
            IdeaOperation.REVIEW_QUEUE_READ,
            OperationOutcome.ACCEPTED,
        )

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "durable_storage_backed": False,
        "event": "idea.operation.review_queue_read",
        "operation": "review_queue_read",
        "outcome": "accepted",
        "service": "lotus-idea",
        "source_authority": "lotus-idea",
        "supportability_status": "foundation_only",
        "supported_feature_promoted": False,
    }
    assert FORBIDDEN_OPERATION_FIELD_KEYS.isdisjoint(payload)
