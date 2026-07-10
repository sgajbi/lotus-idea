import json
import logging

import pytest
from _pytest.logging import LogCaptureFixture

from app.observability import (
    FORBIDDEN_OPERATION_FIELD_KEYS,
    OPERATION_EVENT_SOURCE_AUTHORITIES,
    OPERATION_METRIC_LABELS,
    SENSITIVE_OPERATION_LOG_FIELD_KEYS,
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    configure_logging,
    emit_foundation_operation_event,
    emit_operation_event,
    emit_request_diagnostic_event,
)
from app.domain import SourceSystem
from app.observability.correlation_context import (
    generated_correlation_id,
    generated_trace_id,
    is_product_safe_context_id,
    require_product_safe_context_id,
    sanitize_or_generate_context_id,
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
            correlation_id="corr-support-123",
            trace_id="trace-support-123",
        )

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "correlation_id": "corr-support-123",
        "event": "request.http_error",
        "method": "GET",
        "route": "/api/v1/idea-candidates/{candidateId}",
        "service": "lotus-idea",
        "status_code": 404,
        "trace_id": "trace-support-123",
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
    with pytest.raises(ValueError, match="correlation_id must be a product-safe"):
        emit_request_diagnostic_event(
            "request.http_error",
            route="/health",
            method="GET",
            correlation_id=" ",
        )
    with pytest.raises(ValueError, match="trace_id must be a product-safe"):
        emit_request_diagnostic_event(
            "request.http_error",
            route="/health",
            method="GET",
            trace_id="PB_SG_GLOBAL_BAL_001",
        )


def test_operation_event_metric_labels_are_bounded_and_product_safe() -> None:
    event = OperationEvent(
        operation=IdeaOperation.IMPLEMENTATION_PROOF_READINESS_READ,
        outcome=OperationOutcome.BLOCKED,
        source_authority="lotus-idea",
        supportability_status=OperationSupportability.NOT_CERTIFIED,
    )

    labels = event.metric_labels()

    assert tuple(labels) == OPERATION_METRIC_LABELS
    assert labels == {
        "operation": "implementation_proof_readiness_read",
        "outcome": "blocked",
        "supportability_status": "not_certified",
        "source_authority": "lotus-idea",
        "durable_storage_backed": "false",
        "supported_feature_promoted": "false",
    }
    assert FORBIDDEN_OPERATION_FIELD_KEYS.isdisjoint(labels)


def test_operation_source_authority_vocabulary_matches_domain_sources() -> None:
    assert OPERATION_EVENT_SOURCE_AUTHORITIES == (
        "lotus-advise",
        "lotus-ai",
        "lotus-archive",
        "lotus-core",
        "lotus-idea",
        "lotus-manage",
        "lotus-performance",
        "lotus-render",
        "lotus-report",
        "lotus-risk",
        "source-owned",
    )
    assert {source.value for source in SourceSystem}.issubset(OPERATION_EVENT_SOURCE_AUTHORITIES)


@pytest.mark.parametrize(
    "source_authority",
    [
        "lotus-risk",
        "lotus-performance",
        "lotus-advise",
        "lotus-manage",
        "source-owned",
    ],
)
def test_operation_event_allows_governed_source_authorities(source_authority: str) -> None:
    event = OperationEvent(
        operation=IdeaOperation.SIGNAL_EVALUATION,
        outcome=OperationOutcome.ACCEPTED,
        source_authority=source_authority,
    )

    assert event.metric_labels()["source_authority"] == source_authority


def test_operation_event_rejects_unknown_source_authority() -> None:
    with pytest.raises(ValueError, match="governed operation metric label"):
        OperationEvent(
            operation=IdeaOperation.SIGNAL_EVALUATION,
            outcome=OperationOutcome.ACCEPTED,
            source_authority="client-123",
        )


def test_operation_event_rejects_sensitive_attributes() -> None:
    with pytest.raises(ValueError, match="sensitive keys"):
        OperationEvent(
            operation=IdeaOperation.CONVERSION_INTENT,
            outcome=OperationOutcome.PERMISSION_DENIED,
            attributes={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )
    with pytest.raises(ValueError, match="sensitive keys"):
        OperationEvent(
            operation=IdeaOperation.CONVERSION_INTENT,
            outcome=OperationOutcome.PERMISSION_DENIED,
            attributes={"correlation_id": "corr-as-attribute"},
        )
    with pytest.raises(ValueError, match="sensitive keys"):
        OperationEvent(
            operation=IdeaOperation.SIGNAL_EVALUATION,
            outcome=OperationOutcome.ACCEPTED,
            attributes={"tenant_id": "tenant-private-bank-sg"},
        )
    with pytest.raises(ValueError, match="trace_id must be a product-safe"):
        OperationEvent(
            operation=IdeaOperation.CONVERSION_INTENT,
            outcome=OperationOutcome.PERMISSION_DENIED,
            trace_id=" ",
        )


def test_emit_operation_event_logs_without_sensitive_labels(
    caplog: LogCaptureFixture,
) -> None:
    event = OperationEvent(
        operation=IdeaOperation.CONVERSION_OUTCOME,
        outcome=OperationOutcome.NOT_FOUND,
        source_authority="lotus-idea",
        error_code="conversion_resource_not_found",
        correlation_id="corr-operation-123",
        trace_id="trace-operation-123",
    )

    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        emit_operation_event(event)

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "correlation_id": "corr-operation-123",
        "durable_storage_backed": False,
        "error_code": "conversion_resource_not_found",
        "event": "idea.operation.conversion_outcome",
        "operation": "conversion_outcome",
        "outcome": "not_found",
        "service": "lotus-idea",
        "source_authority": "lotus-idea",
        "supportability_status": "foundation_only",
        "supported_feature_promoted": False,
        "trace_id": "trace-operation-123",
    }
    assert SENSITIVE_OPERATION_LOG_FIELD_KEYS.isdisjoint(payload)
    assert FORBIDDEN_OPERATION_FIELD_KEYS.isdisjoint(event.metric_labels())


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


@pytest.mark.parametrize(
    "context_id",
    [
        "corr-support-123",
        "trace.support:abc-123",
        "4bf92f3577b34da6a3ce929d0e0e4736",
    ],
)
def test_context_id_policy_allows_bounded_support_identifiers(context_id: str) -> None:
    assert is_product_safe_context_id(context_id) is True
    assert sanitize_or_generate_context_id(context_id, generated_correlation_id) == context_id


@pytest.mark.parametrize(
    "context_id",
    [
        "",
        " ",
        "x" * 97,
        "PB_SG_GLOBAL_BAL_001",
        "client_secret:abc123",
        "Bearer-token-abc123",
        "corr with spaces",
        "corr/support/path",
        "corr_under_score",
    ],
)
def test_context_id_policy_replaces_unsafe_identifiers(context_id: str) -> None:
    sanitized = sanitize_or_generate_context_id(context_id, generated_correlation_id)

    assert is_product_safe_context_id(context_id) is False
    assert sanitized != context_id
    assert sanitized.startswith("corr-")
    assert is_product_safe_context_id(sanitized) is True


def test_trace_id_generation_uses_product_safe_prefix() -> None:
    generated = sanitize_or_generate_context_id(None, generated_trace_id)

    assert generated.startswith("trace-")
    assert is_product_safe_context_id(generated) is True


def test_strict_context_id_validation_rejects_missing_values() -> None:
    with pytest.raises(ValueError, match="trace_id must be a product-safe"):
        require_product_safe_context_id(None, "trace_id")
