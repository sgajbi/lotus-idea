from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.runtime_trust_telemetry_proof import (
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.source_ingestion_scheduled_worker import (
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deploy_proof_payload,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload
from app.domain import InMemoryIdeaRepository


def test_implementation_proof_readiness_payload_is_source_safe() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    payload = proof_report.implementation_proof_readiness_payload(snapshot)

    assert payload["repository"] == "lotus-idea"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert {capability["capabilityId"] for capability in payload["capabilities"]} == {
        "source-ingestion",
        "advisor-review-queue",
        "ai-explanation",
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
        "outbox-delivery",
        "workbench-product-proof",
        "downstream-realization",
        "supported-feature-promotion",
    }
    serialized = json.dumps(payload)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_generate_implementation_proof_readiness_writes_output_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["repository"] == "lotus-idea"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["readinessStatus"] == "blocked"


def test_generate_implementation_proof_readiness_uses_explicit_scheduled_worker_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(MANIFEST_ENV, "pre-existing-manifest.json")
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://pre-existing-core")
    monkeypatch.setenv(SCHEDULED_WORKER_PROOF_ENV, "pre-existing-proof.json")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "workItems": [{"portfolioId": "PB_SG_GLOBAL_BAL_001", "asOfDate": "2026-06-21"}],
            }
        ),
        encoding="utf-8",
    )
    scheduled_proof = tmp_path / "scheduled-worker-proof.json"
    scheduled_proof.write_text(json.dumps(_valid_scheduled_worker_proof()), encoding="utf-8")
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-ingestion-manifest",
            str(manifest),
            "--source-ingestion-scheduled-worker-proof",
            str(scheduled_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    source_ingestion = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "source-ingestion"
    )
    assert "scheduled_worker_deploy_proof_missing" not in source_ingestion["blockers"]
    assert "live_core_source_proof_missing" in source_ingestion["blockers"]
    assert "durable_repository_not_configured" in source_ingestion["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    assert os.environ[MANIFEST_ENV] == "pre-existing-manifest.json"
    assert os.environ[CORE_BASE_URL_ENV] == "http://pre-existing-core"
    assert os.environ[SCHEDULED_WORKER_PROOF_ENV] == "pre-existing-proof.json"


def test_generate_implementation_proof_readiness_uses_explicit_durable_repository_proof(
    tmp_path: Path,
) -> None:
    durable_proof = tmp_path / "durable-repository-proof.json"
    durable_proof.write_text(
        json.dumps(
            build_durable_repository_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--durable-repository-proof",
            str(durable_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "durable_repository_not_configured" not in payload["overallBlockers"]
    assert "live_core_source_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_runtime_trust_telemetry_proof(
    tmp_path: Path,
) -> None:
    telemetry_proof = tmp_path / "runtime-trust-telemetry-proof.json"
    telemetry_proof.write_text(
        json.dumps(
            build_runtime_trust_telemetry_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--runtime-trust-telemetry-proof",
            str(telemetry_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "runtime_candidate_snapshot_missing" not in payload["overallBlockers"]
    assert "platform_mesh_certification_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_workbench_read_path_proof(
    tmp_path: Path,
) -> None:
    workbench_proof = tmp_path / "workbench-read-path-proof.json"
    workbench_proof.write_text(
        json.dumps(
            build_workbench_read_path_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--workbench-read-path-proof",
            str(workbench_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "workbench_gateway_bff_consumption_proof_missing" not in payload["overallBlockers"]
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "canonical_demo_runtime_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_rejects_naive_timestamp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = proof_report.main(["--evaluated-at-utc", "2026-06-21T10:10:00"])

    assert result == 2
    assert "timezone-aware" in capsys.readouterr().err


def _valid_scheduled_worker_proof() -> dict[str, object]:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "workItems": [{"portfolioId": "PB_SG_GLOBAL_BAL_001", "asOfDate": "2026-06-21"}],
        }
    )
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
