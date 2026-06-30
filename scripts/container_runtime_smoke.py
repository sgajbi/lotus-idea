from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class SmokeConfig:
    image_name: str
    container_name: str
    host: str
    host_port: int
    container_port: int
    startup_timeout_seconds: float
    probe_interval_seconds: float

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.host_port}"


@dataclass(frozen=True)
class ProbeExpectation:
    path: str
    accepted_statuses: tuple[int, ...]


PROBES: tuple[ProbeExpectation, ...] = (
    ProbeExpectation("/health", (200,)),
    ProbeExpectation("/health/live", (200,)),
    ProbeExpectation("/health/ready", (200, 503)),
)


def probe_endpoint(
    base_url: str,
    expectation: ProbeExpectation,
    *,
    urlopen: Callable[..., Any] = request.urlopen,
) -> dict[str, object]:
    url = f"{base_url}{expectation.path}"
    try:
        with urlopen(url, timeout=5) as response:
            status_code = int(response.status)
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        status_code = int(exc.code)
        body = exc.read().decode("utf-8")
    if status_code not in expectation.accepted_statuses:
        raise RuntimeError(
            f"{expectation.path} returned HTTP {status_code}; "
            f"expected one of {expectation.accepted_statuses}: {body[:500]}"
        )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{expectation.path} did not return JSON: {body[:500]}") from exc
    return {
        "path": expectation.path,
        "statusCode": status_code,
        "payload": payload,
    }


def run_container_smoke(
    config: SmokeConfig,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    probe: Callable[[str, ProbeExpectation], dict[str, object]] = probe_endpoint,
) -> list[dict[str, object]]:
    start_args = [
        "docker",
        "run",
        "--detach",
        "--rm",
        "--name",
        config.container_name,
        "--publish",
        f"{config.host}:{config.host_port}:{config.container_port}",
        config.image_name,
    ]
    remove_args = ["docker", "rm", "--force", config.container_name]
    try:
        run_command(remove_args, check=False, text=True, capture_output=True)
        run_command(start_args, check=True, text=True, capture_output=True)
        deadline = monotonic() + config.startup_timeout_seconds
        last_error: Exception | None = None
        while monotonic() <= deadline:
            try:
                return [probe(config.base_url, expectation) for expectation in PROBES]
            except Exception as exc:  # noqa: BLE001 - collect last startup failure for diagnostics.
                last_error = exc
                sleep(config.probe_interval_seconds)
        logs = run_command(
            ["docker", "logs", config.container_name],
            check=False,
            text=True,
            capture_output=True,
        )
        raise RuntimeError(
            "Container runtime smoke failed before health endpoints became reachable. "
            f"Last error: {last_error}. Container logs:\n{logs.stdout}{logs.stderr}"
        )
    finally:
        run_command(
            remove_args,
            check=False,
            text=True,
            capture_output=True,
        )


def parse_args(argv: Sequence[str]) -> SmokeConfig:
    parser = argparse.ArgumentParser(description="Run the built lotus-idea container smoke proof.")
    parser.add_argument("--image-name", default="backend-service:ci-test")
    parser.add_argument("--container-name", default="lotus-idea-runtime-smoke")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--host-port", type=int, default=18330)
    parser.add_argument("--container-port", type=int, default=8330)
    parser.add_argument("--startup-timeout-seconds", type=float, default=45.0)
    parser.add_argument("--probe-interval-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)
    return SmokeConfig(
        image_name=args.image_name,
        container_name=args.container_name,
        host=args.host,
        host_port=args.host_port,
        container_port=args.container_port,
        startup_timeout_seconds=args.startup_timeout_seconds,
        probe_interval_seconds=args.probe_interval_seconds,
    )


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(sys.argv[1:] if argv is None else argv)
    results = run_container_smoke(config)
    print(json.dumps({"containerRuntimeSmoke": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
