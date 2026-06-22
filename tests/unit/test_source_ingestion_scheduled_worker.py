from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

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
    assert "--core-base-url" in captured.err
    assert "None" not in captured.err


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
