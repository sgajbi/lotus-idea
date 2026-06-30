from __future__ import annotations

import io
import subprocess
from email.message import Message
from urllib import error

from scripts.container_runtime_smoke import (
    ProbeExpectation,
    SmokeConfig,
    probe_endpoint,
    run_container_smoke,
)


def test_probe_endpoint_accepts_default_degraded_readiness() -> None:
    def urlopen(_url: str, *, timeout: int) -> object:
        assert timeout == 5
        headers = Message()
        raise error.HTTPError(
            url="http://127.0.0.1:18330/health/ready",
            code=503,
            msg="Service Unavailable",
            hdrs=headers,
            fp=io.BytesIO(b'{"status":"degraded"}'),
        )

    result = probe_endpoint(
        "http://127.0.0.1:18330",
        ProbeExpectation("/health/ready", (200, 503)),
        urlopen=urlopen,
    )

    assert result == {
        "path": "/health/ready",
        "statusCode": 503,
        "payload": {"status": "degraded"},
    }


def test_container_runtime_smoke_removes_container_after_startup_failure() -> None:
    commands: list[list[str]] = []

    def run_command(
        args: list[str],
        *,
        check: bool,
        text: bool,
        capture_output: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert text is True
        assert capture_output is True
        commands.append(args)
        if args[:2] == ["docker", "logs"]:
            return subprocess.CompletedProcess(args, 0, stdout="startup log", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    attempts = {"count": 0}

    def probe(_base_url: str, _expectation: ProbeExpectation) -> dict[str, object]:
        attempts["count"] += 1
        raise RuntimeError("not reachable")

    clock_values = iter((0.0, 0.0, 2.0))

    try:
        run_container_smoke(
            SmokeConfig(
                image_name="backend-service:ci-test",
                container_name="lotus-idea-runtime-smoke-test",
                host="127.0.0.1",
                host_port=18330,
                container_port=8330,
                startup_timeout_seconds=1.0,
                probe_interval_seconds=0.0,
            ),
            run_command=run_command,
            sleep=lambda _seconds: None,
            monotonic=lambda: next(clock_values),
            probe=probe,
        )
    except RuntimeError as exc:
        assert "Container runtime smoke failed" in str(exc)
        assert "startup log" in str(exc)
    else:  # pragma: no cover - defensive assertion for readability.
        raise AssertionError("expected smoke failure")

    assert attempts["count"] == 1
    assert commands[0] == ["docker", "rm", "--force", "lotus-idea-runtime-smoke-test"]
    assert commands[1][:2] == ["docker", "run"]
    assert "127.0.0.1:18330:8330" in commands[1]
    assert commands[-1] == ["docker", "rm", "--force", "lotus-idea-runtime-smoke-test"]
