from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.source_ingestion_scheduler import (
    DOCKER_COMPOSE_WORKER_SERVICE,
    RUN_ONCE_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_SCHEMA_VERSION,
    build_scheduled_worker_check_summary,
    scheduled_worker_check_summary_is_valid,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)


ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_scheduled_worker_check_summary() -> None:
    plan = source_ingestion_worker_plan_from_manifest(_manifest())
    schedule = source_ingestion_schedule_config_from_values(
        interval_seconds="300",
        max_runs="1",
    )

    summary = build_scheduled_worker_check_summary(plan=plan, schedule=schedule)

    assert summary["schemaVersion"] == SCHEDULED_WORKER_SCHEMA_VERSION
    assert summary["mode"] == "check_only"
    assert summary["sourceAuthority"] == "lotus-core"
    assert summary["opportunityFamily"] == "high_cash"
    assert summary["runOnceManifestSchemaVersion"] == MANIFEST_SCHEMA_VERSION
    assert summary["schedulerEntrypoint"] == SCHEDULED_WORKER_ENTRYPOINT
    assert summary["runOnceWorkerEntrypoint"] == RUN_ONCE_WORKER_ENTRYPOINT
    assert summary["dockerComposeService"] == DOCKER_COMPOSE_WORKER_SERVICE
    assert summary["schedulePolicy"] == {
        "intervalSeconds": 300,
        "maxRuns": 1,
        "runOnStart": True,
        "runForever": False,
    }
    assert summary["supportedFeaturePromoted"] is False
    serialized = json.dumps(summary)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "idempotencyKey" not in serialized


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("schemaVersion",), "wrong"),
        (("mode",), "run"),
        (("sourceAuthority",), "lotus-idea"),
        (("opportunityFamily",), "underperformance"),
        (("runOnceManifestSchemaVersion",), "wrong"),
        (("schedulerEntrypoint",), "scripts/wrong.py"),
        (("runOnceWorkerEntrypoint",), "scripts/wrong.py"),
        (("dockerComposeService",), "wrong"),
        (("supportedFeaturePromoted",), True),
        (("schedulePolicy",), []),
        (("schedulePolicy", "intervalSeconds"), 0),
        (("schedulePolicy", "maxRuns"), True),
        (("schedulePolicy", "runOnStart"), False),
        (("schedulePolicy", "runForever"), "false"),
        (("runOnceManifest",), []),
        (("runOnceManifest", "schemaVersion"), "wrong"),
    ),
)
def test_scheduled_worker_check_summary_rejects_contract_drift(
    path: tuple[str, ...],
    value: object,
) -> None:
    summary = _check_summary()
    _set(summary, path, value)

    assert not scheduled_worker_check_summary_is_valid(summary)


def test_scheduled_worker_check_summary_rejects_non_mapping_and_unknown_keys() -> None:
    assert not scheduled_worker_check_summary_is_valid([])

    summary = _check_summary()
    summary["deploymentObserved"] = True

    assert not scheduled_worker_check_summary_is_valid(summary)


def test_scheduled_worker_check_summary_rejects_schedule_policy_unknown_keys() -> None:
    summary = _check_summary()
    schedule_policy = summary["schedulePolicy"]
    assert isinstance(schedule_policy, dict)
    schedule_policy["cron"] = "* * * * *"

    assert not scheduled_worker_check_summary_is_valid(summary)


def test_schedule_config_defaults_none_values() -> None:
    schedule = source_ingestion_schedule_config_from_values(
        interval_seconds=None,
        max_runs=None,
    )

    assert schedule.interval_seconds == 300
    assert schedule.max_runs == 1
    assert schedule.run_forever is False


def test_schedule_config_accepts_explicit_daemon_mode() -> None:
    schedule = source_ingestion_schedule_config_from_values(
        interval_seconds="300",
        max_runs="1",
        run_forever="true",
    )

    assert schedule.run_forever is True


@pytest.mark.parametrize("value", ("false", "False", "0", "", None))
def test_schedule_config_accepts_explicit_non_daemon_values(value: object) -> None:
    schedule = source_ingestion_schedule_config_from_values(
        interval_seconds="300",
        max_runs="1",
        run_forever=value,
    )

    assert schedule.run_forever is False


def test_schedule_config_rejects_invalid_boolean() -> None:
    with pytest.raises(ValueError, match="runForever must be a boolean"):
        source_ingestion_schedule_config_from_values(
            interval_seconds="300",
            max_runs="1",
            run_forever="yes",
        )


@pytest.mark.parametrize(
    ("interval_seconds", "max_runs"),
    [
        ("abc", "1"),
        ("", "1"),
        (0, "1"),
        (True, "1"),
        ("300", "abc"),
        ("300", 0),
    ],
)
def test_schedule_config_rejects_invalid_positive_integers(
    interval_seconds: object,
    max_runs: object,
) -> None:
    with pytest.raises(ValueError, match="must be a positive integer"):
        source_ingestion_schedule_config_from_values(
            interval_seconds=interval_seconds,
            max_runs=max_runs,
        )


def test_scheduled_worker_cli_check_only_is_source_safe(capsys: Any) -> None:
    module = _load_scheduler_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--check-only",
                "--interval-seconds",
                "60",
                "--max-runs",
                "1",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schemaVersion"] == SCHEDULED_WORKER_SCHEMA_VERSION
    assert payload["schedulePolicy"]["intervalSeconds"] == 60
    assert payload["schedulePolicy"]["maxRuns"] == 1
    assert payload["schedulePolicy"]["runForever"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in captured.out
    assert "portfolioId" not in captured.out


def test_scheduled_worker_cli_requires_core_base_url_for_run_mode(capsys: Any) -> None:
    module = _load_scheduler_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--interval-seconds",
                "60",
                "--max-runs",
                "1",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert "--core-query-base-url" in captured.err
    assert "--core-query-control-plane-base-url" in captured.err
    assert "--core-base-url" in captured.err
    assert "None" not in captured.err


def test_scheduled_worker_cli_forwards_split_core_source_urls(
    capsys: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_scheduler_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )
    forwarded_args: list[list[str]] = []

    def capture_run_once(args: list[str]) -> int:
        forwarded_args.append(args)
        return 0

    monkeypatch.setattr(module, "run_once_worker_main", capture_run_once)

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--core-query-base-url",
                "http://localhost:8201",
                "--core-query-control-plane-base-url",
                "http://localhost:8202",
                "--interval-seconds",
                "60",
                "--max-runs",
                "1",
            ]
        )
        == 0
    )

    assert len(forwarded_args) == 1
    assert "--core-query-base-url" in forwarded_args[0]
    assert "http://localhost:8201" in forwarded_args[0]
    assert "--core-query-control-plane-base-url" in forwarded_args[0]
    assert "http://localhost:8202" in forwarded_args[0]
    captured = capsys.readouterr()
    assert "scheduled_iteration_started" in captured.out


def test_scheduled_worker_daemon_stops_cleanly_after_signal_request(
    capsys: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_scheduler_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )

    def stop_after_first_iteration(_args: list[str]) -> int:
        setattr(module, "_stop_requested", True)
        return 0

    monkeypatch.setattr(module, "run_once_worker_main", stop_after_first_iteration)

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--core-query-base-url",
                "http://localhost:8201",
                "--core-query-control-plane-base-url",
                "http://localhost:8202",
                "--run-forever",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out.count("scheduled_iteration_started") == 1
    assert "scheduled_iteration_completed" in captured.out


def test_scheduled_worker_propagates_blocked_iteration_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_scheduler_script()
    manifest_path = (
        ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
    )
    monkeypatch.setattr(module, "run_once_worker_main", lambda _args: 3)

    assert (
        module.main(
            [
                "--manifest",
                str(manifest_path),
                "--core-query-base-url",
                "http://localhost:8201",
                "--core-query-control-plane-base-url",
                "http://localhost:8202",
                "--max-runs",
                "2",
            ]
        )
        == 3
    )


def _manifest() -> dict[str, Any]:
    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "tenantId": "default",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workItems": [
            {
                "portfolioId": "PB_SG_GLOBAL_BAL_001",
                "asOfDate": "2026-06-21",
                "idempotencyKey": "signal-ingestion:high-cash:lotus-core:explicit",
            }
        ],
    }


def _check_summary() -> dict[str, Any]:
    return build_scheduled_worker_check_summary(
        plan=source_ingestion_worker_plan_from_manifest(_manifest()),
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds="300",
            max_runs="1",
        ),
    )


def _set(payload: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    target = payload
    for part in path[:-1]:
        nested = target[part]
        assert isinstance(nested, dict)
        target = nested
    target[path[-1]] = value


def _load_scheduler_script() -> ModuleType:
    script_path = ROOT / "scripts" / "run_scheduled_source_ingestion_worker.py"
    spec = importlib.util.spec_from_file_location(
        "run_scheduled_source_ingestion_worker", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
