from __future__ import annotations

import os

from app.application.outbox_delivery_readiness import OUTBOX_BROKER_URL_ENV
from app.infrastructure.outbox_publisher import (
    HttpOutboxEventPublisher,
    OutboxBrokerPublisherConfig,
    OutboxPublisherConfigurationError,
)
from app.ports.outbox_publisher import OutboxEventPublisher

OUTBOX_BROKER_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_TIMEOUT_SECONDS"
OUTBOX_BROKER_MAX_CONNECTIONS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_MAX_CONNECTIONS"
OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS"
OUTBOX_BROKER_POOL_TIMEOUT_SECONDS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_POOL_TIMEOUT_SECONDS"
OUTBOX_BROKER_RETRY_MAX_ATTEMPTS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_RETRY_MAX_ATTEMPTS"
OUTBOX_BROKER_RETRY_INITIAL_BACKOFF_SECONDS_ENV = (
    "LOTUS_IDEA_OUTBOX_BROKER_RETRY_INITIAL_BACKOFF_SECONDS"
)
OUTBOX_BROKER_RETRY_MAX_BACKOFF_SECONDS_ENV = "LOTUS_IDEA_OUTBOX_BROKER_RETRY_MAX_BACKOFF_SECONDS"


def build_outbox_publisher_from_environment() -> OutboxEventPublisher | str:
    broker_url = os.getenv(OUTBOX_BROKER_URL_ENV, "").strip()
    if not broker_url:
        return "outbox_broker_not_configured"
    try:
        return HttpOutboxEventPublisher(
            OutboxBrokerPublisherConfig(
                base_url=broker_url,
                timeout_seconds=_positive_float_env(OUTBOX_BROKER_TIMEOUT_SECONDS_ENV, default=2.0),
                max_connections=_positive_int_env(OUTBOX_BROKER_MAX_CONNECTIONS_ENV, default=20),
                max_keepalive_connections=_positive_int_env(
                    OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS_ENV, default=10
                ),
                pool_timeout_seconds=_positive_float_env(
                    OUTBOX_BROKER_POOL_TIMEOUT_SECONDS_ENV, default=2.0
                ),
                retry_max_attempts=_positive_int_env(
                    OUTBOX_BROKER_RETRY_MAX_ATTEMPTS_ENV, default=1
                ),
                retry_initial_backoff_seconds=_non_negative_float_env(
                    OUTBOX_BROKER_RETRY_INITIAL_BACKOFF_SECONDS_ENV, default=0.05
                ),
                retry_max_backoff_seconds=_non_negative_float_env(
                    OUTBOX_BROKER_RETRY_MAX_BACKOFF_SECONDS_ENV, default=0.5
                ),
            )
        )
    except OutboxPublisherConfigurationError:
        return "outbox_broker_configuration_invalid"


def _positive_float_env(name: str, *, default: float) -> float:
    raw_duration = os.getenv(name, str(default)).strip()
    try:
        duration_seconds = float(raw_duration)
    except ValueError as exc:
        raise OutboxPublisherConfigurationError(f"{name} must be numeric") from exc
    if duration_seconds <= 0:
        raise OutboxPublisherConfigurationError(f"{name} must be positive")
    return duration_seconds


def _non_negative_float_env(name: str, *, default: float) -> float:
    raw_duration = os.getenv(name, str(default)).strip()
    try:
        duration_seconds = float(raw_duration)
    except ValueError as exc:
        raise OutboxPublisherConfigurationError(f"{name} must be numeric") from exc
    if duration_seconds < 0:
        raise OutboxPublisherConfigurationError(f"{name} must not be negative")
    return duration_seconds


def _positive_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise OutboxPublisherConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise OutboxPublisherConfigurationError(f"{name} must be positive")
    return value
