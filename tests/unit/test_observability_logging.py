import json
import logging

import pytest

from app.observability import (
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_METRIC_LABELS,
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    configure_logging,
    emit_operation_event,
    log_event,
)


def test_configure_logging_sets_product_safe_message_format() -> None:
    configure_logging()
    assert logging.getLogger().level in {logging.INFO, logging.WARNING}


def test_log_event_emits_structured_json(caplog) -> None:  # type: ignore[no-untyped-def]
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        log_event("idea.test", service="lotus-idea", status="ok")

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "idea.test",
        "service": "lotus-idea",
        "status": "ok",
    }


def test_operation_event_metric_labels_are_bounded_and_product_safe() -> None:
    event = OperationEvent(
        operation=IdeaOperation.REPORT_EVIDENCE_PACK,
        outcome=OperationOutcome.ACCEPTED,
        source_authority="lotus-report",
        supportability_status=OperationSupportability.FOUNDATION_ONLY,
    )

    labels = event.metric_labels()

    assert tuple(labels) == OPERATION_METRIC_LABELS
    assert labels == {
        "operation": "report_evidence_pack",
        "outcome": "accepted",
        "supportability_status": "foundation_only",
        "source_authority": "lotus-report",
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


def test_emit_operation_event_logs_without_sensitive_labels(caplog) -> None:  # type: ignore[no-untyped-def]
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
