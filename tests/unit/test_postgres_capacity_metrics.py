from __future__ import annotations

from typing import NoReturn

from prometheus_client import CollectorRegistry, generate_latest

from app.domain.capacity_posture import evaluate_postgres_capacity_posture
from app.observability.postgres_capacity import PostgresCapacityCollector


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
