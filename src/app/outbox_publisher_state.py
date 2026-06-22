from __future__ import annotations

import os

from app.application.outbox_delivery_readiness import OUTBOX_BROKER_URL_ENV
from app.infrastructure.outbox_publisher import (
    HttpOutboxEventPublisher,
    OutboxBrokerPublisherConfig,
    OutboxPublisherConfigurationError,
)
from app.ports.outbox_publisher import OutboxEventPublisher


def build_outbox_publisher_from_environment() -> OutboxEventPublisher | str:
    broker_url = os.getenv(OUTBOX_BROKER_URL_ENV, "").strip()
    if not broker_url:
        return "outbox_broker_not_configured"
    try:
        return HttpOutboxEventPublisher(OutboxBrokerPublisherConfig(base_url=broker_url))
    except OutboxPublisherConfigurationError:
        return "outbox_broker_configuration_invalid"
