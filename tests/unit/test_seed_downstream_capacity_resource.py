from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "seed_downstream_capacity_resource.py"
    spec = importlib.util.spec_from_file_location("seed_downstream_capacity_resource", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(output: Path) -> list[str]:
    return [
        "--base-url",
        "https://idea.example",
        "--as-of-date",
        "2026-07-11",
        "--seeded-at-utc",
        "2026-07-11T08:00:00Z",
        "--commit-sha",
        "a" * 40,
        "--branch",
        "main",
        "--run-id",
        "capacity-run-1",
        "--confirmation",
        "SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE",
        "--output",
        str(output),
    ]


def test_cli_writes_atomic_source_safe_seed_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    output = tmp_path / "nested" / "seed.json"
    instances: list[Any] = []

    class FakeAdapter:
        closed = False

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            instances.append(self)

        def persist_candidate(self, **kwargs: object) -> str:
            return "candidate-synthetic-001"

        def transition_candidate(self, **kwargs: object) -> None:
            pass

        def approve_candidate(self, **kwargs: object) -> None:
            pass

        def record_conversion_intent(self, **kwargs: object) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    monkeypatch.setenv("LOTUS_IDEA_CAPACITY_AUTHORIZATION", "Bearer transient")
    monkeypatch.setattr(module, "HttpDownstreamCapacitySeed", FakeAdapter)

    assert module.main(_args(output)) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    adapter = instances[0]
    assert artifact["syntheticResource"] is True
    assert artifact["claimPosture"] == "seed_only_not_capacity_evidence"
    assert artifact["downstreamSubmissionPath"].startswith(
        "/api/v1/conversion-intents/capacity-conversion-"
    )
    assert adapter.kwargs["base_headers"] == {"Authorization": "Bearer transient"}
    assert adapter.closed is True
    assert not output.with_suffix(".json.tmp").exists()


def test_cli_rejects_missing_confirmation_without_constructing_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    output = tmp_path / "seed.json"

    class ForbiddenAdapter:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("adapter must not be constructed")

    monkeypatch.setattr(module, "HttpDownstreamCapacitySeed", ForbiddenAdapter)
    args = _args(output)
    args[args.index("SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE")] = "wrong"

    assert module.main(args) == 2
    assert not output.exists()


def test_cli_closes_adapter_and_avoids_partial_output_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script()
    output = tmp_path / "seed.json"
    instances: list[Any] = []

    class FailingAdapter:
        closed = False

        def __init__(self, **kwargs: object) -> None:
            instances.append(self)

        def persist_candidate(self, **kwargs: object) -> str:
            raise ValueError("source-safe synthetic failure")

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "HttpDownstreamCapacitySeed", FailingAdapter)

    assert module.main(_args(output)) == 2
    assert instances[0].closed is True
    assert not output.exists()
