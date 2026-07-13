from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain import OutboxEventRecord
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.ports.outbox.publisher import OutboxPublishOutcome


class OutboxPublisherConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class OutboxBrokerPublisherConfig:
    base_url: str
    publish_path: str = "/events/lotus-idea/outbox"
    timeout_seconds: float = 2.0
    max_connections: int = 20
    max_keepalive_connections: int = 10
    pool_timeout_seconds: float = 2.0
    retry_max_attempts: int = 1
    retry_initial_backoff_seconds: float = 0.05
    retry_max_backoff_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not self.publish_path.startswith("/"):
            raise OutboxPublisherConfigurationError("publish_path must start with '/'.")
        if "?" in self.publish_path or "#" in self.publish_path:
            raise OutboxPublisherConfigurationError(
                "publish_path must not include query string or fragment."
            )
        try:
            DownstreamClientConfig(
                base_url=self.base_url,
                dependency="lotus-platform-broker",
                timeout_seconds=self.timeout_seconds,
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
                pool_timeout_seconds=self.pool_timeout_seconds,
                retry_max_attempts=self.retry_max_attempts,
                retry_initial_backoff_seconds=self.retry_initial_backoff_seconds,
                retry_max_backoff_seconds=self.retry_max_backoff_seconds,
            )
        except ValueError as exc:
            raise OutboxPublisherConfigurationError(str(exc)) from exc


class HttpOutboxEventPublisher:
    def __init__(
        self,
        config: OutboxBrokerPublisherConfig,
        client: DownstreamJsonClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or DownstreamJsonClient(
            DownstreamClientConfig(
                base_url=config.base_url,
                dependency="lotus-platform-broker",
                timeout_seconds=config.timeout_seconds,
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
                pool_timeout_seconds=config.pool_timeout_seconds,
                retry_max_attempts=config.retry_max_attempts,
                retry_initial_backoff_seconds=config.retry_initial_backoff_seconds,
                retry_max_backoff_seconds=config.retry_max_backoff_seconds,
            )
        )

    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome:
        try:
            self._client.post_json(
                self._config.publish_path,
                json_payload=_event_envelope(event),
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                idempotency_key=event.idempotency_fingerprint,
            )
        except DownstreamServiceError as exc:
            return OutboxPublishOutcome.rejected_by_publisher(_failure_reason(exc))
        return OutboxPublishOutcome.accepted_by_publisher()

    def close(self) -> None:
        self._client.close()


def _event_envelope(event: OutboxEventRecord) -> dict[str, Any]:
    return {
        "eventId": event.event_id,
        "eventType": event.event_type,
        "aggregateType": event.aggregate_type,
        "aggregateId": event.aggregate_id,
        "schemaVersion": event.schema_version,
        "occurredAtUtc": event.occurred_at_utc.isoformat(),
        "payload": dict(event.payload),
        "idempotencyFingerprint": event.idempotency_fingerprint,
        "correlationId": event.correlation_id,
        "traceId": event.trace_id,
        "causationId": event.causation_id,
        "lineageOrigin": event.lineage_origin.value,
        "producer": "lotus-idea",
        "sourceAuthority": "lotus-idea",
        "supportabilityStatus": "not_certified",
    }


def _failure_reason(exc: DownstreamServiceError) -> str:
    if exc.status_code in {401, 403}:
        return "publisher_permission_denied"
    if exc.status_code is not None and 400 <= exc.status_code < 500:
        return "publisher_rejected"
    if exc.code == "upstream_timeout":
        return "publisher_timeout"
    if exc.code == "upstream_malformed_response":
        return "publisher_malformed_response"
    return "publisher_unavailable"
