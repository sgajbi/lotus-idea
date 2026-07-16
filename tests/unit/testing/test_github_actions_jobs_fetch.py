from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _load_module() -> ModuleType:
    script_path = ROOT / "scripts" / "ci" / "fetch_github_actions_jobs.py"
    spec = importlib.util.spec_from_file_location("fetch_github_actions_jobs", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _completed(returncode: int, *, stdout: str = "", stderr: str = "") -> Any:
    return subprocess.CompletedProcess(
        args=["gh", "api", "endpoint"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_fetch_run_jobs_retries_transient_failure_and_writes_valid_payload(
    tmp_path: Path,
) -> None:
    module = _load_module()
    results = iter(
        [
            _completed(1, stderr="HTTP 503: Service Unavailable"),
            _completed(0, stdout=json.dumps({"jobs": [{"id": 7}]})),
        ]
    )
    delays: list[float] = []
    output = tmp_path / "ci-jobs.json"

    payload = module.fetch_run_jobs(
        repository="sgajbi/lotus-idea",
        run_id="123",
        output=output,
        command_runner=lambda *args, **kwargs: next(results),
        sleep=delays.append,
    )

    assert payload == {"jobs": [{"id": 7}]}
    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert delays == [2.0]


def test_fetch_run_jobs_retries_invalid_payload_then_fails_without_partial_output(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "ci-jobs.json"
    output.write_text('{"jobs": [{"id": "previous"}]}\n', encoding="utf-8")
    results = iter(
        [
            _completed(0, stdout="not-json"),
            _completed(0, stdout=json.dumps({"unexpected": []})),
            _completed(1, stderr="HTTP 503"),
        ]
    )
    delays: list[float] = []

    with pytest.raises(RuntimeError, match="after 3 attempts") as exc_info:
        module.fetch_run_jobs(
            repository="sgajbi/lotus-idea",
            run_id="456",
            output=output,
            attempts=3,
            initial_delay_seconds=0.5,
            command_runner=lambda *args, **kwargs: next(results),
            sleep=delays.append,
        )

    assert "invalid JSON" in str(exc_info.value)
    assert "jobs array" in str(exc_info.value)
    assert "HTTP 503" in str(exc_info.value)
    assert delays == [0.5, 1.0]
    assert json.loads(output.read_text(encoding="utf-8")) == {"jobs": [{"id": "previous"}]}
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize(
    ("repository", "run_id", "attempts", "message"),
    [
        ("", "123", 1, "repository must not be blank"),
        ("sgajbi/lotus-idea", "not-a-run", 1, "digits only"),
        ("sgajbi/lotus-idea", "123", 0, "at least 1"),
    ],
)
def test_fetch_run_jobs_rejects_invalid_identity_or_retry_policy(
    tmp_path: Path,
    repository: str,
    run_id: str,
    attempts: int,
    message: str,
) -> None:
    module = _load_module()

    with pytest.raises(ValueError, match=message):
        module.fetch_run_jobs(
            repository=repository,
            run_id=run_id,
            output=tmp_path / "ci-jobs.json",
            attempts=attempts,
        )
