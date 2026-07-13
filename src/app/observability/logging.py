from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import json
import logging
from types import MappingProxyType
from typing import Literal

from prometheus_client import Counter

from app.domain import SourceSystem
from app.observability.correlation_context import require_product_safe_context_id

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

SERVICE_NAME = "lotus-idea"
AGGREGATE_SOURCE_AUTHORITY = "source-owned"
OPERATION_EVENT_SOURCE_AUTHORITIES = tuple(
    sorted({SERVICE_NAME, AGGREGATE_SOURCE_AUTHORITY, *(source.value for source in SourceSystem)})
)
REQUEST_DIAGNOSTIC_EVENTS = frozenset(
    {
        "request.validation_failed",
        "request.http_error",
        "request.unhandled_error",
    }
)

FORBIDDEN_OPERATION_FIELD_KEYS = frozenset(
    {
        "account_id",
        "client_id",
        "client_name",
        "correlation_id",
        "holding_id",
        "portfolio_id",
        "raw_entitlement_failure",
        "request_body",
        "response_body",
        "trace_id",
        "transaction_id",
        "tenant_id",
        "tenant_ids",
    }
)
REQUEST_CORRELATION_LOG_FIELD_KEYS = frozenset({"correlation_id", "trace_id"})
SENSITIVE_OPERATION_LOG_FIELD_KEYS = (
    FORBIDDEN_OPERATION_FIELD_KEYS - REQUEST_CORRELATION_LOG_FIELD_KEYS
)

OPERATION_METRIC_LABELS = (
    "operation",
    "outcome",
    "supportability_status",
    "source_authority",
    "durable_storage_backed",
    "supported_feature_promoted",
)


class IdeaOperation(StrEnum):
    AI_EXPLANATION = "ai_explanation"
    AI_EXPLANATION_READINESS_READ = "ai_explanation_readiness_read"
    SIGNAL_EVALUATION = "signal_evaluation"
    CANDIDATE_PERSISTENCE = "candidate_persistence"
    CANDIDATE_DETAIL_READ = "candidate_detail_read"
    CANDIDATE_EVIDENCE_REPLAY = "candidate_evidence_replay"
    LIFECYCLE_TRANSITION = "lifecycle_transition"
    REVIEW_QUEUE_READ = "review_queue_read"
    REVIEW_QUEUE_EXCEPTION_READ = "review_queue_exception_read"
    REVIEW_QUEUE_READINESS_READ = "review_queue_readiness_read"
    REVIEW_ACTION = "review_action"
    FEEDBACK_RECORD = "feedback_record"
    CONVERSION_INTENT = "conversion_intent"
    CONVERSION_OUTCOME = "conversion_outcome"
    REPORT_EVIDENCE_PACK = "report_evidence_pack"
    DOWNSTREAM_REALIZATION_SUBMISSION = "downstream_realization_submission"
    DOWNSTREAM_RECONCILIATION_READ = "downstream_reconciliation_read"
    DOWNSTREAM_RECONCILIATION_RESOLVE = "downstream_reconciliation_resolve"
    DATA_LIFECYCLE_ACTION = "data_lifecycle_action"
    OUTBOX_DELIVERY_RUN_ONCE = "outbox_delivery_run_once"
    OUTBOX_DELIVERY_READINESS_READ = "outbox_delivery_readiness_read"
    OUTBOX_DEAD_LETTER_READ = "outbox_dead_letter_read"
    OUTBOX_DEAD_LETTER_REDRIVE = "outbox_dead_letter_redrive"
    DOWNSTREAM_REALIZATION_READINESS_READ = "downstream_realization_readiness_read"
    MESH_READINESS_READ = "mesh_readiness_read"
    MESH_TRUST_TELEMETRY_PREVIEW_READ = "mesh_trust_telemetry_preview_read"
    MESH_TRUST_TELEMETRY_SNAPSHOT_READ = "mesh_trust_telemetry_snapshot_read"
    SOURCE_INGESTION_RUN_ONCE = "source_ingestion_run_once"
    SOURCE_INGESTION_READINESS_READ = "source_ingestion_readiness_read"
    IMPLEMENTATION_PROOF_READINESS_READ = "implementation_proof_readiness_read"


class OperationOutcome(StrEnum):
    ACCEPTED = "accepted"
    FALLBACK = "fallback"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    DUPLICATE = "duplicate"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    BLOCKED = "blocked"
    SUPPRESSED = "suppressed"
    NOT_ELIGIBLE = "not_eligible"


class OperationSupportability(StrEnum):
    FOUNDATION_ONLY = "foundation_only"
    NOT_CERTIFIED = "not_certified"
    SUPPORTED = "supported"


_OPERATION_EVENTS = Counter(
    "lotus_idea_operation_events_total",
    "Count of bounded lotus-idea business operation events.",
    OPERATION_METRIC_LABELS,
)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_event(event_name: str, service: str, level: LogLevel = "INFO", **fields: object) -> None:
    payload = {
        "event": event_name,
        "service": service,
        **fields,
    }
    logging.getLogger(service).log(
        getattr(logging, level),
        json.dumps(payload, sort_keys=True, default=str),
    )


def emit_request_diagnostic_event(
    event_name: str,
    *,
    route: str,
    method: str,
    level: LogLevel = "INFO",
    status_code: int | None = None,
    error_category: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    if event_name not in REQUEST_DIAGNOSTIC_EVENTS:
        raise ValueError(f"unsupported request diagnostic event: {event_name}")
    if not route.startswith("/") or "?" in route:
        raise ValueError("route must be a route template without query string")
    if not method.strip():
        raise ValueError("method is required")
    fields: dict[str, object] = {
        "route": route,
        "method": method,
    }
    if status_code is not None:
        fields["status_code"] = status_code
    if error_category is not None:
        fields["error_category"] = error_category
    if correlation_id is not None:
        fields["correlation_id"] = _safe_log_context_value(correlation_id, "correlation_id")
    if trace_id is not None:
        fields["trace_id"] = _safe_log_context_value(trace_id, "trace_id")
    log_event(event_name, SERVICE_NAME, level, **fields)


@dataclass(frozen=True)
class OperationEvent:
    operation: IdeaOperation
    outcome: OperationOutcome
    source_authority: str = SERVICE_NAME
    supportability_status: OperationSupportability = OperationSupportability.FOUNDATION_ONLY
    durable_storage_backed: bool = False
    supported_feature_promoted: bool = False
    error_code: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_operation_source_authority(self.source_authority)
        if self.error_code is not None and not self.error_code.strip():
            raise ValueError("error_code cannot be blank")
        if self.correlation_id is not None:
            _safe_log_context_value(self.correlation_id, "correlation_id")
        if self.trace_id is not None:
            _safe_log_context_value(self.trace_id, "trace_id")
        leaked = FORBIDDEN_OPERATION_FIELD_KEYS.intersection(self.attributes)
        if leaked:
            raise ValueError(
                f"Operation event attributes contain sensitive keys: {', '.join(sorted(leaked))}"
            )
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def log_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {
            "operation": self.operation.value,
            "outcome": self.outcome.value,
            "source_authority": self.source_authority,
            "supportability_status": self.supportability_status.value,
            "durable_storage_backed": self.durable_storage_backed,
            "supported_feature_promoted": self.supported_feature_promoted,
        }
        if self.error_code is not None:
            fields["error_code"] = self.error_code
        if self.correlation_id is not None:
            fields["correlation_id"] = self.correlation_id
        if self.trace_id is not None:
            fields["trace_id"] = self.trace_id
        fields.update(self.attributes)
        return fields

    def metric_labels(self) -> dict[str, str]:
        return {
            "operation": self.operation.value,
            "outcome": self.outcome.value,
            "supportability_status": self.supportability_status.value,
            "source_authority": self.source_authority,
            "durable_storage_backed": str(self.durable_storage_backed).lower(),
            "supported_feature_promoted": str(self.supported_feature_promoted).lower(),
        }


def emit_operation_event(event: OperationEvent) -> None:
    log_event(
        f"idea.operation.{event.operation.value}",
        SERVICE_NAME,
        "INFO",
        **event.log_fields(),
    )
    _OPERATION_EVENTS.labels(**event.metric_labels()).inc()


def emit_foundation_operation_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    *,
    source_authority: str = SERVICE_NAME,
    durable_storage_backed: bool = False,
    error_code: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    attributes: Mapping[str, str] | None = None,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=operation,
            outcome=outcome,
            source_authority=source_authority,
            error_code=error_code,
            correlation_id=correlation_id,
            trace_id=trace_id,
            attributes=attributes or {},
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
        )
    )


def validate_operation_source_authority(source_authority: str) -> str:
    if not source_authority.strip():
        raise ValueError("source_authority is required")
    if source_authority not in OPERATION_EVENT_SOURCE_AUTHORITIES:
        raise ValueError("source_authority is not a governed operation metric label")
    return source_authority


def _safe_log_context_value(value: str, field_name: str) -> str:
    return require_product_safe_context_id(value, field_name)
