from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.domain import OutboxEventRecord, build_candidate_outbox_event
from app.infrastructure.downstream_client import DownstreamClientConfig, DownstreamJsonClient
from app.infrastructure.outbox_publisher import (
    HttpOutboxEventPublisher,
    OutboxBrokerPublisherConfig,
    OutboxPublisherConfigurationError,
)
from app.runtime.outbox_publisher_state import (
    OUTBOX_BROKER_MAX_CONNECTIONS_ENV,
    OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS_ENV,
    OUTBOX_BROKER_POOL_TIMEOUT_SECONDS_ENV,
    build_outbox_publisher_from_environment,
)
from app.application.outbox_delivery_readiness import OUTBOX_BROKER_URL_ENV


EVENT_TIME = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_http_outbox_event_publisher_posts_source_safe_event_envelope() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["correlation_id"] = request.headers["X-Correlation-Id"]
        captured["trace_id"] = request.headers["X-Trace-Id"]
        captured["payload"] = request.read()
        return httpx.Response(202, json={"accepted": True})

    event = outbox_event()
    publisher = publisher_with_transport(httpx.MockTransport(handler))

    outcome = publisher.publish(event)

    assert outcome.accepted is True
    assert captured["path"] == "/events/lotus-idea/outbox"
    assert captured["correlation_id"] == "corr-outbox"
    assert captured["trace_id"] == "cause-outbox"
    payload = httpx.Response(200, content=captured["payload"]).json()
    assert payload == {
        "eventId": event.event_id,
        "eventType": "idea.candidate.persisted.v1",
        "aggregateType": "idea_candidate",
        "aggregateId": "idea_high_cash_001",
        "schemaVersion": "v1",
        "occurredAtUtc": EVENT_TIME.isoformat(),
        "payload": {"candidate_family": "high_cash"},
        "idempotencyFingerprint": event.idempotency_fingerprint,
        "correlationId": "corr-outbox",
        "causationId": "cause-outbox",
        "producer": "lotus-idea",
        "sourceAuthority": "lotus-idea",
        "supportabilityStatus": "not_certified",
    }
    rendered = str(payload)
    assert "portfolio_id" not in rendered
    assert "client_id" not in rendered
    assert "request_body" not in rendered
    assert "response_body" not in rendered
    assert "retry_count" not in rendered
    assert "failure_reason" not in rendered


@pytest.mark.parametrize(
    ("status_code", "failure_reason"),
    [
        (400, "publisher_rejected"),
        (403, "publisher_permission_denied"),
        (500, "publisher_unavailable"),
    ],
)
def test_http_outbox_event_publisher_maps_broker_failures_to_bounded_reasons(
    status_code: int,
    failure_reason: str,
) -> None:
    publisher = publisher_with_transport(
        httpx.MockTransport(lambda _request: httpx.Response(status_code, json={}))
    )

    outcome = publisher.publish(outbox_event())

    assert outcome.accepted is False
    assert outcome.failure_reason == failure_reason


def test_http_outbox_event_publisher_maps_transport_error_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("raw broker host must not leak", request=request)

    publisher = publisher_with_transport(httpx.MockTransport(handler))

    outcome = publisher.publish(outbox_event())

    assert outcome.accepted is False
    assert outcome.failure_reason == "publisher_unavailable"


@pytest.mark.parametrize(
    ("config_kwargs", "message"),
    [
        ({"base_url": "not-a-url"}, "absolute HTTP"),
        ({"base_url": "https://broker.example", "publish_path": "events"}, "start with '/'"),
        (
            {"base_url": "https://broker.example", "publish_path": "/events?tenant=private"},
            "query string",
        ),
        ({"base_url": "https://broker.example", "timeout_seconds": 0}, "positive"),
        ({"base_url": "https://broker.example", "max_connections": 0}, "positive"),
        ({"base_url": "https://broker.example", "max_keepalive_connections": 0}, "positive"),
        (
            {
                "base_url": "https://broker.example",
                "max_connections": 2,
                "max_keepalive_connections": 3,
            },
            "must not exceed",
        ),
        ({"base_url": "https://broker.example", "pool_timeout_seconds": 0}, "positive"),
    ],
)
def test_outbox_broker_publisher_config_rejects_invalid_configuration(
    config_kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(OutboxPublisherConfigurationError, match=message):
        OutboxBrokerPublisherConfig(**config_kwargs)


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        (OUTBOX_BROKER_MAX_CONNECTIONS_ENV, "0"),
        (OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS_ENV, "0"),
        (OUTBOX_BROKER_POOL_TIMEOUT_SECONDS_ENV, "0"),
    ],
)
def test_outbox_publisher_state_rejects_invalid_resource_settings(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
) -> None:
    monkeypatch.setenv(OUTBOX_BROKER_URL_ENV, "https://broker.example")
    monkeypatch.setenv(env_name, env_value)

    result = build_outbox_publisher_from_environment()

    assert result == "outbox_broker_configuration_invalid"


def test_http_outbox_event_publisher_close_releases_owned_client() -> None:
    class CloseAwareDownstreamClient:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    client = CloseAwareDownstreamClient()
    publisher = HttpOutboxEventPublisher(
        OutboxBrokerPublisherConfig(base_url="https://broker.example"),
        client=client,  # type: ignore[arg-type]
    )

    publisher.close()

    assert client.closed is True


def publisher_with_transport(transport: httpx.MockTransport) -> HttpOutboxEventPublisher:
    return HttpOutboxEventPublisher(
        OutboxBrokerPublisherConfig(base_url="https://broker.example"),
        client=DownstreamJsonClient(
            DownstreamClientConfig(base_url="https://broker.example", timeout_seconds=0.5),
            client=httpx.Client(base_url="https://broker.example", transport=transport),
        ),
    )


def outbox_event() -> OutboxEventRecord:
    return build_candidate_outbox_event(
        event_type="idea.candidate.persisted.v1",
        aggregate_id="idea_high_cash_001",
        occurred_at_utc=EVENT_TIME,
        payload={"candidate_family": "high_cash"},
        idempotency_key="idea.candidate.persisted.v1:idempotency",
        correlation_id="corr-outbox",
        causation_id="cause-outbox",
    )
