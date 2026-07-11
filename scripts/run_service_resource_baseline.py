from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time

from app.application.service_resource_baseline import build_service_resource_baseline
from app.infrastructure.prometheus_resource_probe import PrometheusResourceProbe
from app.ports.resource_probe import ResourceProbeError


MAXIMUM_OBSERVED_WINDOW_SECONDS = 3_600.0
MAXIMUM_SAMPLE_COUNT = 3_600
DEFAULT_OUTPUT = Path("output/observability/service-resource-baseline.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect bounded source-safe Lotus Idea process resource evidence."
    )
    parser.add_argument("--metrics-url", required=True)
    parser.add_argument("--environment-profile", required=True, choices=("test",))
    parser.add_argument("--sample-count", type=int, default=5)
    parser.add_argument("--sample-interval-seconds", type=float, default=1.0)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    probe: PrometheusResourceProbe | None = None
    try:
        _validate_window(args.sample_count, args.sample_interval_seconds)
        probe = PrometheusResourceProbe(metrics_url=args.metrics_url)
        snapshots = []
        for sample_index in range(args.sample_count):
            snapshots.append(probe.execute())
            if sample_index + 1 < args.sample_count:
                time.sleep(args.sample_interval_seconds)
        artifact = build_service_resource_baseline(
            snapshots=snapshots,
            environment_profile=args.environment_profile,
            generated_at_utc=datetime.now(UTC),
            commit_sha=args.commit_sha,
            branch=args.branch,
            run_id=args.run_id,
        )
        _write_json_atomic(args.output, artifact)
        return 0
    except (OSError, ValueError, ResourceProbeError) as exc:
        print(f"service resource baseline failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if probe is not None:
            probe.close()


def _validate_window(sample_count: int, sample_interval_seconds: float) -> None:
    if not 2 <= sample_count <= MAXIMUM_SAMPLE_COUNT:
        raise ValueError("sample_count must be between 2 and 3600")
    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be positive")
    observed_window = (sample_count - 1) * sample_interval_seconds
    if observed_window > MAXIMUM_OBSERVED_WINDOW_SECONDS:
        raise ValueError("resource observation window must not exceed 3600 seconds")


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
