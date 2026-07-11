from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.resource_probe import ProcessResourceSnapshot, ResourceProbeError


ROOT = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "run_service_resource_baseline.py"
    spec = importlib.util.spec_from_file_location("run_service_resource_baseline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(output: Path) -> list[str]:
    return [
        "--metrics-url",
        "https://sensitive.example/metrics",
        "--environment-profile",
        "test",
        "--sample-count",
        "2",
        "--sample-interval-seconds",
        "0.1",
        "--commit-sha",
        "abc123",
        "--branch",
        "feature/capacity",
        "--run-id",
        "resource-1",
        "--output",
        str(output),
    ]


def test_cli_collects_atomic_source_safe_resource_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    output = tmp_path / "resource.json"
    start = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)

    class FakeProbe:
        instance: "FakeProbe"

        def __init__(self, **kwargs: object) -> None:
            self.snapshots = iter(
                [
                    ProcessResourceSnapshot(start, 1.0, 100),
                    ProcessResourceSnapshot(start + timedelta(seconds=1), 1.5, 200),
                ]
            )
            self.closed = False
            FakeProbe.instance = self

        def execute(self) -> ProcessResourceSnapshot:
            return next(self.snapshots)

        def close(self) -> None:
            self.closed = True

    sleeps: list[float] = []
    monkeypatch.setattr(module, "PrometheusResourceProbe", FakeProbe)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    assert module.main(_args(output)) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["sampleCount"] == 2
    assert artifact["cpuCoreSecondsPerSecondAverage"] == 0.5
    assert artifact["costAttributionVerified"] is False
    assert "sensitive.example" not in output.read_text(encoding="utf-8")
    assert sleeps == [0.1]
    assert FakeProbe.instance.closed is True


@pytest.mark.parametrize(
    ("sample_count", "interval", "message"),
    [
        (1, 1.0, "between 2 and 3600"),
        (3_601, 1.0, "between 2 and 3600"),
        (2, 0.0, "must be positive"),
        (3_600, 2.0, "must not exceed 3600"),
    ],
)
def test_window_guard_rejects_unsafe_collection(
    sample_count: int, interval: float, message: str
) -> None:
    module = _load_script()
    with pytest.raises(ValueError, match=message):
        module._validate_window(sample_count, interval)


def test_cli_fails_closed_and_closes_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script()

    class FailingProbe:
        instance: "FailingProbe"

        def __init__(self, **kwargs: object) -> None:
            self.closed = False
            FailingProbe.instance = self

        def execute(self) -> ProcessResourceSnapshot:
            raise ResourceProbeError("bounded failure")

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "PrometheusResourceProbe", FailingProbe)

    assert module.main(_args(tmp_path / "resource.json")) == 2
    assert FailingProbe.instance.closed is True
