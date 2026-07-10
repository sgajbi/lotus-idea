from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.source_ingestion_scheduled_worker import (
    DOCKER_COMPOSE_WORKER_SERVICE,
    RUN_ONCE_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_PROOF_SCHEMA_VERSION,
    SCHEDULED_WORKER_SCHEMA_VERSION,
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deploy_proof_payload,
    scheduled_worker_deploy_proof_is_valid,
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


def test_validates_scheduled_worker_deploy_proof_without_support_promotion() -> None:
    plan = source_ingestion_worker_plan_from_manifest(_manifest())
    summary = build_scheduled_worker_check_summary(
        plan=plan,
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        ),
    )

    proof = build_scheduled_worker_deploy_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=True,
    )

    assert proof["schemaVersion"] == SCHEDULED_WORKER_PROOF_SCHEMA_VERSION
    assert proof["scheduledWorkerDeployProofValid"] is True
    assert proof["proofClosed"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["remainingCertificationBlockers"] == (
        "live_core_source_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    )
    assert scheduled_worker_deploy_proof_is_valid(proof) is True


def test_rejects_scheduled_worker_deploy_proof_when_compose_service_missing() -> None:
    plan = source_ingestion_worker_plan_from_manifest(_manifest())
    summary = build_scheduled_worker_check_summary(
        plan=plan,
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        ),
    )

    proof = build_scheduled_worker_deploy_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=False,
    )

    assert proof["scheduledWorkerDeployProofValid"] is False
    assert scheduled_worker_deploy_proof_is_valid(proof) is False


def test_rejects_scheduled_worker_deploy_proof_with_naive_timestamp() -> None:
    plan = source_ingestion_worker_plan_from_manifest(_manifest())
    summary = build_scheduled_worker_check_summary(
        plan=plan,
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        ),
    )
    proof = build_scheduled_worker_deploy_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=True,
    )

    assert proof["scheduledWorkerDeployProofValid"] is False
    assert scheduled_worker_deploy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("sourceAuthority", "lotus-performance"),
        ("opportunityFamily", "cash"),
        ("generatedAtUtc", ""),
        ("generatedAtUtc", "not-a-datetime"),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("scheduledWorkerDeployProofValid", False),
    ],
)
def test_rejects_scheduled_worker_deploy_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_scheduled_worker_proof()
    proof[field_name] = bad_value

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schedulerEntrypoint", "wrong.py"),
        ("schedulerEntrypointPresent", False),
        ("runOnceWorkerEntrypoint", "wrong.py"),
        ("runOnceWorkerEntrypointPresent", False),
        ("dockerComposeService", "wrong-service"),
        ("dockerComposeServicePresent", False),
    ],
)
def test_rejects_scheduled_worker_deploy_proof_with_invalid_deployment_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_scheduled_worker_proof()
    deployment = proof["deployment"]
    assert isinstance(deployment, dict)
    deployment[field_name] = bad_value

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


def test_rejects_scheduled_worker_deploy_proof_with_non_mapping_deployment() -> None:
    proof = _valid_scheduled_worker_proof()
    proof["deployment"] = []

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("mode", "run"),
        ("sourceAuthority", "lotus-performance"),
        ("opportunityFamily", "cash"),
        ("runOnceManifestSchemaVersion", "wrong"),
        ("schedulerEntrypoint", "wrong.py"),
        ("runOnceWorkerEntrypoint", "wrong.py"),
        ("dockerComposeService", "wrong-service"),
        ("supportedFeaturePromoted", True),
    ],
)
def test_rejects_scheduled_worker_deploy_proof_with_invalid_summary_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_scheduled_worker_proof()
    summary = proof["checkSummary"]
    assert isinstance(summary, dict)
    summary[field_name] = bad_value

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "summary_mutation",
    [
        {"schedulePolicy": []},
        {"schedulePolicy": {"intervalSeconds": 0, "maxRuns": 1, "runOnStart": True}},
        {"schedulePolicy": {"intervalSeconds": 300, "maxRuns": 0, "runOnStart": True}},
        {"schedulePolicy": {"intervalSeconds": 300, "maxRuns": 1, "runOnStart": False}},
        {"runOnceManifest": []},
        {"runOnceManifest": {"schemaVersion": "wrong"}},
    ],
)
def test_rejects_scheduled_worker_deploy_proof_with_invalid_summary_shapes(
    summary_mutation: dict[str, object],
) -> None:
    proof = _valid_scheduled_worker_proof()
    summary = proof["checkSummary"]
    assert isinstance(summary, dict)
    summary.update(summary_mutation)

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


def test_rejects_scheduled_worker_deploy_proof_with_non_mapping_summary() -> None:
    proof = _valid_scheduled_worker_proof()
    proof["checkSummary"] = []

    assert scheduled_worker_deploy_proof_is_valid(proof) is False


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
        module._stop_requested = True
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
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "workItems": [
            {
                "portfolioId": "PB_SG_GLOBAL_BAL_001",
                "asOfDate": "2026-06-21",
                "idempotencyKey": "signal-ingestion:high-cash:lotus-core:explicit",
            }
        ],
    }


def _valid_scheduled_worker_proof() -> dict[str, Any]:
    plan = source_ingestion_worker_plan_from_manifest(_manifest())
    summary = build_scheduled_worker_check_summary(
        plan=plan,
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        ),
    )
    return build_scheduled_worker_deploy_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=True,
    )


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
