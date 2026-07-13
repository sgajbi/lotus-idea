from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from scripts.outbox._bootstrap import ROOT
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from _bootstrap import ROOT  # type: ignore[import-not-found,no-redef]

from app.application.outbox.supportability_alerts import (  # noqa: E402
    OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS,
    OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD,
    OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD,
)
from app.observability.outbox.supportability import (  # noqa: E402
    OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC,
    OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC,
    OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC,
    OUTBOX_DELIVERY_STATE_METRIC,
    OUTBOX_DELIVERY_STATES,
)

CONTRACT_PATH = Path("contracts/observability/lotus-idea-outbox-supportability.v1.json")
EXPECTED_METRICS = {
    OUTBOX_DELIVERY_STATE_METRIC: ("repository", "state"),
    OUTBOX_DELIVERY_OLDEST_READY_AGE_METRIC: ("repository",),
    OUTBOX_DELIVERY_CONFIGURATION_READY_METRIC: ("repository",),
    OUTBOX_DELIVERY_COLLECTION_SUCCESS_METRIC: ("repository",),
}
EXPECTED_THRESHOLDS = {
    "delivery_ready_count": OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD,
    "oldest_delivery_ready_age_seconds": OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS,
    "retry_deferred_count": OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD,
    "dead_letter_count": 0,
    "expired_lease_count": 0,
}
EXPECTED_ALERTS = {
    "outbox-delivery-collection-failed": ("P2", "5m"),
    "outbox-delivery-dead-letter-present": ("P2", "15m"),
    "outbox-delivery-expired-lease-present": ("P2", "10m"),
    "outbox-delivery-backlog-stalled": ("P2", "15m"),
    "outbox-delivery-retry-pressure": ("P3", "30m"),
}
FORBIDDEN_LABELS = {
    "aggregate_id",
    "candidate_id",
    "client_id",
    "correlation_id",
    "event_id",
    "idempotency_key",
    "payload",
    "portfolio_id",
    "trace_id",
}


def validate_outbox_supportability_contract(
    *, repository_root: Path = ROOT, contract_path: Path = CONTRACT_PATH
) -> list[str]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return ["outbox supportability contract must be an object"]
    errors = _validate_header(payload)
    errors.extend(_validate_sources(payload, repository_root))
    errors.extend(_validate_metrics(payload))
    errors.extend(_validate_thresholds_and_alerts(payload))
    return sorted(errors)


def _validate_header(payload: dict[str, Any]) -> list[str]:
    expected = {
        "contract_id": "lotus-idea-outbox-supportability",
        "contract_version": "1.0.0",
        "repository": "lotus-idea",
        "supportability_status": "not_certified",
        "supported_feature_promoted": False,
    }
    return [
        f"outbox supportability contract {key} must be {value!r}"
        for key, value in expected.items()
        if payload.get(key) != value
    ]


def _validate_sources(payload: dict[str, Any], repository_root: Path) -> list[str]:
    sources = payload.get("source_of_truth")
    if not isinstance(sources, dict):
        return ["outbox supportability source_of_truth must be an object"]
    errors: list[str] = []
    for key, value in sources.items():
        if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
            errors.append(f"outbox supportability source {key} must be a safe relative path")
        elif not (repository_root / value).exists():
            errors.append(f"outbox supportability source {key} is missing")
    return errors


def _validate_metrics(payload: dict[str, Any]) -> list[str]:
    metrics = payload.get("metric_families")
    if not isinstance(metrics, list):
        return ["outbox supportability metric_families must be a list"]
    errors: list[str] = []
    observed: set[str] = set()
    for metric in metrics:
        if not isinstance(metric, dict) or not isinstance(metric.get("name"), str):
            errors.append("outbox supportability metric entry must have a name")
            continue
        name = metric["name"]
        observed.add(name)
        labels = tuple(metric.get("labels") or ())
        if name not in EXPECTED_METRICS:
            errors.append(f"unsupported outbox supportability metric: {name}")
        elif labels != EXPECTED_METRICS[name]:
            errors.append(f"{name} labels must match code-owned labels")
        if metric.get("type") != "gauge":
            errors.append(f"{name} must be a gauge")
        forbidden = FORBIDDEN_LABELS.intersection(labels)
        if forbidden:
            errors.append(f"{name} contains forbidden labels: {', '.join(sorted(forbidden))}")
        if name == OUTBOX_DELIVERY_STATE_METRIC and tuple(metric.get("states") or ()) != (
            OUTBOX_DELIVERY_STATES
        ):
            errors.append("outbox delivery states must match code-owned states")
    if observed != set(EXPECTED_METRICS):
        errors.append("outbox supportability metric family inventory drifted")
    return errors


def _validate_thresholds_and_alerts(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("thresholds") != EXPECTED_THRESHOLDS:
        errors.append("outbox supportability thresholds must match code-owned policy")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return errors + ["outbox supportability alerts must be a list"]
    observed = {
        alert.get("alert_id"): (alert.get("severity"), alert.get("for"))
        for alert in alerts
        if isinstance(alert, dict)
    }
    if observed != EXPECTED_ALERTS:
        errors.append("outbox supportability alert inventory drifted")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate outbox supportability contract")
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    errors = validate_outbox_supportability_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox supportability contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
