from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from app.application.source_ingestion_scheduled_worker import (
    build_scheduled_worker_deploy_proof_payload,
)
from scripts.proof_source_safety import validate_forbidden_content
from scripts.source_ingestion_scheduled_worker_contract_gate import (
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
    WORKER_MANIFEST_IMAGE_PATH,
    validate_source_ingestion_scheduled_worker_contract,
)


ROOT = Path(__file__).resolve().parents[2]


def test_scheduled_worker_contract_gate_passes_current_contract() -> None:
    assert validate_source_ingestion_scheduled_worker_contract() == []


def test_scheduled_worker_contract_gate_detects_source_sensitive_content() -> None:
    errors: list[str] = []
    validate_forbidden_content(
        build_scheduled_worker_deploy_proof_payload(
            generated_at_utc=datetime.fromisoformat("2026-06-21T10:10:00+00:00"),
            check_summary={
                "schemaVersion": "lotus-idea.source-ingestion.scheduled-worker.v1",
                "mode": "check_only",
                "sourceAuthority": "lotus-core",
                "opportunityFamily": "high_cash",
                "runOnceManifestSchemaVersion": (
                    "lotus-idea.source-ingestion.high-cash.run-once.v1"
                ),
                "schedulerEntrypoint": "scripts/run_scheduled_source_ingestion_worker.py",
                "runOnceWorkerEntrypoint": "scripts/run_source_ingestion_worker.py",
                "dockerComposeService": "lotus-idea-source-ingestion-worker",
                "schedulePolicy": {"intervalSeconds": 300, "maxRuns": 1, "runOnStart": True},
                "runOnceManifest": {"portfolioId": "PB_SG_GLOBAL_BAL_001"},
                "supportedFeaturePromoted": False,
            },
            scheduler_entrypoint_present=True,
            run_once_worker_entrypoint_present=True,
            docker_compose_service_present=True,
        ),
        errors,
        FORBIDDEN_KEYS,
        FORBIDDEN_TEXT_FRAGMENTS,
    )

    assert any("portfolioId" in error for error in errors)
    assert any("PB_SG_GLOBAL_BAL_001" in error for error in errors)


def test_canonical_worker_manifest_and_compose_source_runtime_wiring_are_explicit() -> None:
    manifest_path = (
        ROOT
        / "docs"
        / "examples"
        / "source-ingestion"
        / ("canonical-high-cash-worker.manifest.json")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert manifest["schemaVersion"] == "lotus-idea.source-ingestion.high-cash.run-once.v1"
    assert manifest["workItems"][0]["portfolioId"] == "PB_SG_GLOBAL_BAL_001"
    assert manifest["workItems"][0]["asOfDate"] == "2026-04-10"
    assert "LOTUS_CORE_QUERY_BASE_URL" in compose_text
    assert "LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL" in compose_text
    assert "LOTUS_RISK_BASE_URL" in compose_text
    assert "LOTUS_PERFORMANCE_BASE_URL" in compose_text
    assert "LOTUS_IDEA_SOURCE_INGESTION_MANIFEST" in compose_text
    dockerfile_text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f"COPY {WORKER_MANIFEST_IMAGE_PATH} ./{WORKER_MANIFEST_IMAGE_PATH}" in dockerfile_text
