from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    build_source_ingestion_readiness_snapshot,
)
from app.repository_state import DATABASE_URL_ENV


def test_source_ingestion_readiness_reports_blocked_default_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.repository == "lotus-idea"
    assert snapshot.source_authority == "lotus-core"
    assert snapshot.opportunity_family == "high_cash"
    assert snapshot.example_manifest_available is True
    assert snapshot.configured_manifest_available is False
    assert snapshot.configured_live_proof_available is False
    assert snapshot.live_core_source_proof_valid is False
    assert snapshot.core_base_url_configured is False
    assert snapshot.durable_repository_configured is False
    assert snapshot.run_once_configuration_status == "blocked"
    assert snapshot.run_once_configured is False
    assert snapshot.certification_status == "not_certified"
    assert snapshot.live_source_certified is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.configuration_blockers == (
        "source_ingestion_manifest_not_configured",
        "lotus_core_base_url_not_configured",
        "durable_repository_not_configured",
    )
    assert snapshot.certification_blockers == (
        "live_core_source_proof_missing",
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    )


def test_source_ingestion_readiness_reports_configured_run_once_posture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_manifest_available is True
    assert snapshot.configured_live_proof_available is False
    assert snapshot.live_core_source_proof_valid is False
    assert snapshot.core_base_url_configured is True
    assert snapshot.durable_repository_configured is True
    assert snapshot.run_once_configuration_status == "configured"
    assert snapshot.run_once_configured is True
    assert snapshot.certification_status == "not_certified"
    assert snapshot.certification_blockers


def test_source_ingestion_readiness_clears_only_live_core_blocker_with_valid_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    proof = tmp_path / "live-proof.json"
    proof.write_text(
        json.dumps(
            build_source_ingestion_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                live_core_source_attempted=True,
                worker_summary={
                    "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
                    "mode": "run_once",
                    "sourceAuthority": "lotus-core",
                    "durableStorageBacked": True,
                    "totalCount": 1,
                    "decisionCounts": {"accepted": 1, "replayed": 0},
                },
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(LIVE_PROOF_ENV, str(proof))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_live_proof_available is True
    assert snapshot.live_core_source_proof_valid is True
    assert "live_core_source_proof_missing" not in snapshot.certification_blockers
    assert snapshot.certification_blockers == (
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    )
    assert snapshot.certification_status == "not_certified"


def test_source_ingestion_readiness_keeps_live_core_blocker_for_invalid_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    proof = tmp_path / "live-proof.json"
    proof.write_text('{"schemaVersion": "wrong"}', encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(LIVE_PROOF_ENV, str(proof))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_live_proof_available is True
    assert snapshot.live_core_source_proof_valid is False
    assert "live_core_source_proof_missing" in snapshot.certification_blockers


def test_source_ingestion_readiness_resolves_relative_manifest_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    example_manifest = tmp_path / "docs" / "examples" / "source-ingestion"
    example_manifest.mkdir(parents=True)
    (example_manifest / "high-cash-worker-manifest.example.json").write_text(
        "{}",
        encoding="utf-8",
    )
    manifest = tmp_path / "ops" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, "ops/manifest.json")
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot(repository_root=tmp_path)

    assert snapshot.example_manifest_available is True
    assert snapshot.configured_manifest_available is True
    assert snapshot.run_once_configured is True


def test_source_ingestion_readiness_blocks_unreadable_configured_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_manifest = tmp_path / "missing.json"
    monkeypatch.setenv(MANIFEST_ENV, str(missing_manifest))
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_manifest_available is False
    assert snapshot.run_once_configured is False
    assert snapshot.configuration_blockers == ("source_ingestion_manifest_unreadable",)
