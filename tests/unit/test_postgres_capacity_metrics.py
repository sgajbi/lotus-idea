from __future__ import annotations

from typing import NoReturn

from prometheus_client import CollectorRegistry, generate_latest
import pytest

from app.domain.capacity_posture import evaluate_postgres_capacity_posture
from app.observability.postgres_capacity import PostgresCapacityCollector
import app.observability.postgres_capacity as capacity_metrics_module


def test_collector_exposes_bounded_utilization_and_one_hot_posture() -> None:
    registry = CollectorRegistry()
    registry.register(PostgresCapacityCollector(lambda: evaluate_postgres_capacity_posture(0.75)))

    metrics = generate_latest(registry).decode("utf-8")

    assert 'lotus_idea_postgres_capacity_collection_success{repository="lotus-idea"} 1.0' in metrics
    assert (
        'lotus_idea_postgres_connection_utilization_ratio{repository="lotus-idea"} 0.75' in metrics
    )
    assert (
        'lotus_idea_postgres_capacity_posture{posture="warning",repository="lotus-idea"} 1.0'
        in metrics
    )
    assert (
        'lotus_idea_postgres_capacity_posture{posture="shed",repository="lotus-idea"} 0.0'
        in metrics
    )
    for forbidden in ("tenant_id", "client_id", "portfolio_id", "database_url", "request_id"):
        assert forbidden not in metrics


def test_collector_fails_closed_without_breaking_scrape() -> None:
    def unavailable() -> NoReturn:
        raise RuntimeError("database host detail")

    registry = CollectorRegistry()
    registry.register(PostgresCapacityCollector(unavailable))

    metrics = generate_latest(registry).decode("utf-8")

    assert 'lotus_idea_postgres_capacity_collection_success{repository="lotus-idea"} 0.0' in metrics
    assert (
        'lotus_idea_postgres_capacity_posture{posture="unavailable",repository="lotus-idea"} 1.0'
        in metrics
    )
    assert "lotus_idea_postgres_connection_utilization_ratio" not in metrics
    assert "database host detail" not in metrics


def test_collector_provider_and_registration_are_reconfigurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = PostgresCapacityCollector()
    collector.set_provider(lambda: evaluate_postgres_capacity_posture(0.2))
    registry = CollectorRegistry()
    monkeypatch.setattr(capacity_metrics_module, "_POSTGRES_CAPACITY_COLLECTOR", collector)
    monkeypatch.setattr(capacity_metrics_module, "_POSTGRES_CAPACITY_REGISTERED", False)

    capacity_metrics_module.configure_postgres_capacity_metrics(
        lambda: evaluate_postgres_capacity_posture(0.3),
        registry=registry,
    )

    metrics = generate_latest(registry).decode("utf-8")
    assert (
        'lotus_idea_postgres_connection_utilization_ratio{repository="lotus-idea"} 0.3' in metrics
    )
