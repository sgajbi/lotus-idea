from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

from app.application.service_capacity_baseline import (
    CapacityMeasurement,
    build_service_capacity_baseline,
)


INPUT_KEYS = frozenset(
    {
        "branch",
        "commitSha",
        "costResourceMeasured",
        "environmentProfile",
        "generatedAtUtc",
        "measurements",
        "observedWindowSeconds",
        "postgresSaturationMeasured",
        "runId",
    }
)
MEASUREMENT_KEYS = frozenset(
    {
        "durationSeconds",
        "itemCount",
        "outcome",
        "queueAgeSeconds",
        "recovered",
        "retryCount",
        "scenario",
    }
)


def generate_service_capacity_baseline(input_payload: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(input_payload) - INPUT_KEYS)
    missing = sorted(INPUT_KEYS - set(input_payload))
    if unknown:
        raise ValueError(f"capacity input contains unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"capacity input is missing fields: {', '.join(missing)}")
    raw_measurements = input_payload["measurements"]
    if not isinstance(raw_measurements, list):
        raise ValueError("measurements must be a list")
    measurements = [
        _measurement(raw_measurement, index)
        for index, raw_measurement in enumerate(raw_measurements)
    ]
    return build_service_capacity_baseline(
        measurements=measurements,
        environment_profile=_required_text(input_payload, "environmentProfile"),
        generated_at_utc=_parse_datetime(input_payload["generatedAtUtc"]),
        commit_sha=_required_text(input_payload, "commitSha"),
        branch=_required_text(input_payload, "branch"),
        run_id=_required_text(input_payload, "runId"),
        observed_window_seconds=_number(input_payload, "observedWindowSeconds"),
        postgres_saturation_measured=_boolean(input_payload, "postgresSaturationMeasured"),
        cost_resource_measured=_boolean(input_payload, "costResourceMeasured"),
    )


def _measurement(payload: Any, index: int) -> CapacityMeasurement:
    if not isinstance(payload, dict):
        raise ValueError(f"measurements[{index}] must be an object")
    unknown = sorted(set(payload) - MEASUREMENT_KEYS)
    required = {"durationSeconds", "outcome", "scenario"}
    missing = sorted(required - set(payload))
    if unknown:
        raise ValueError(f"measurements[{index}] contains unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"measurements[{index}] is missing fields: {', '.join(missing)}")
    return CapacityMeasurement(
        scenario=_required_text(payload, "scenario"),
        duration_seconds=_number(payload, "durationSeconds"),
        outcome=_required_text(payload, "outcome"),
        item_count=_integer(payload, "itemCount", default=1),
        queue_age_seconds=_optional_number(payload, "queueAgeSeconds"),
        retry_count=_integer(payload, "retryCount", default=0),
        recovered=_optional_boolean(payload, "recovered"),
    )


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-blank string")
    return value.strip()


def _number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _optional_number(payload: dict[str, Any], key: str) -> float | None:
    return None if payload.get(key) is None else _number(payload, key)


def _integer(payload: dict[str, Any], key: str, *, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return int(value)


def _boolean(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _optional_boolean(payload: dict[str, Any], key: str) -> bool | None:
    return None if payload.get(key) is None else _boolean(payload, key)


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("generatedAtUtc must be a string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("generatedAtUtc must be an ISO datetime") from exc


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate source-safe Lotus Idea service capacity baseline evidence."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw_payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, dict):
            raise ValueError("capacity input must be a JSON object")
        _write_json_atomic(args.output, generate_service_capacity_baseline(raw_payload))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"service capacity baseline generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
