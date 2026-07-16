from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


DEFAULT_ATTEMPTS = 5
DEFAULT_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


def fetch_run_jobs(
    *,
    repository: str,
    run_id: str,
    output: Path,
    attempts: int = DEFAULT_ATTEMPTS,
    initial_delay_seconds: float = DEFAULT_INITIAL_DELAY_SECONDS,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not repository.strip():
        raise ValueError("repository must not be blank")
    if not run_id.isdigit():
        raise ValueError("run_id must contain digits only")
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if initial_delay_seconds < 0:
        raise ValueError("initial_delay_seconds must not be negative")
    if request_timeout_seconds <= 0:
        raise ValueError("request_timeout_seconds must be positive")

    endpoint = f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    failures: list[str] = []

    for attempt in range(1, attempts + 1):
        try:
            completed = command_runner(
                ["gh", "api", endpoint],
                capture_output=True,
                check=False,
                text=True,
                timeout=request_timeout_seconds,
            )
            payload = _validated_payload(completed)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            failures.append(f"attempt {attempt}: {_bounded_detail(str(exc))}")
        else:
            _write_json_atomically(output, payload)
            return payload

        if attempt < attempts:
            sleep(initial_delay_seconds * (2 ** (attempt - 1)))

    raise RuntimeError(
        f"GitHub Actions jobs metadata remained unavailable after {attempts} attempts: "
        + "; ".join(failures)
    )


def _validated_payload(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown gh api failure"
        raise ValueError(f"gh api exited {completed.returncode}: {detail}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("gh api returned invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("gh api response must be an object containing a jobs array")
    return payload


def _write_json_atomically(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def _bounded_detail(detail: str, *, limit: int = 500) -> str:
    normalized = " ".join(detail.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch GitHub Actions job metadata with bounded retries."
    )
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument(
        "--initial-delay-seconds",
        type=float,
        default=DEFAULT_INITIAL_DELAY_SECONDS,
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    fetch_run_jobs(
        repository=args.repository,
        run_id=args.run_id,
        output=args.output,
        attempts=args.attempts,
        initial_delay_seconds=args.initial_delay_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
