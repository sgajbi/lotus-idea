from __future__ import annotations

from datetime import datetime

from app.application.source_ingestion_scheduled_worker import (
    build_scheduled_worker_deploy_proof_payload,
)
from scripts.source_ingestion_scheduled_worker_contract_gate import (
    _validate_forbidden_content,
    validate_source_ingestion_scheduled_worker_contract,
)


def test_scheduled_worker_contract_gate_passes_current_contract() -> None:
    assert validate_source_ingestion_scheduled_worker_contract() == []


def test_scheduled_worker_contract_gate_detects_source_sensitive_content() -> None:
    errors: list[str] = []
    _validate_forbidden_content(
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
    )

    assert any("portfolioId" in error for error in errors)
    assert any("PB_SG_GLOBAL_BAL_001" in error for error in errors)
