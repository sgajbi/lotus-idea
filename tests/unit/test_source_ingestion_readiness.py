from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    MANIFEST_ENV,
    build_source_ingestion_readiness_snapshot,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.runtime.repository_state import DATABASE_URL_ENV
from tests.support.source_ingestion_scheduler_evidence import (
    deployment_evidence,
    source_contract,
)
from tests.support.source_ingestion_runtime_evidence import runtime_execution


ROOT = Path(__file__).resolve().parents[2]
EVALUATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_source_ingestion_readiness_reports_blocked_default_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.repository == "lotus-idea"
    assert snapshot.source_authority == "lotus-core"
    assert snapshot.opportunity_family == "high_cash"
    assert snapshot.example_manifest_available is True
    assert snapshot.configured_manifest_available is False
    assert snapshot.configured_live_proof_available is False
    assert snapshot.live_core_source_proof_valid is False
    assert snapshot.configured_scheduled_worker_source_contract_available is False
    assert snapshot.scheduled_worker_source_contract_valid is False
    assert snapshot.configured_scheduled_worker_deployment_evidence_available is False
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert snapshot.core_base_url_configured is False
    assert snapshot.core_query_base_url_configured is False
    assert snapshot.core_query_control_plane_base_url_configured is False
    assert snapshot.durable_repository_configured is False
    assert snapshot.run_once_configuration_status == "blocked"
    assert snapshot.run_once_configured is False
    assert snapshot.certification_status == "not_certified"
    assert snapshot.live_source_certified is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.configuration_blockers == (
        "source_ingestion_manifest_not_configured",
        "lotus_core_query_base_url_not_configured",
        "lotus_core_query_control_plane_base_url_not_configured",
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
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_manifest_available is True
    assert snapshot.configured_live_proof_available is False
    assert snapshot.live_core_source_proof_valid is False
    assert snapshot.configured_scheduled_worker_source_contract_available is False
    assert snapshot.scheduled_worker_source_contract_valid is False
    assert snapshot.configured_scheduled_worker_deployment_evidence_available is False
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert snapshot.core_base_url_configured is True
    assert snapshot.core_query_base_url_configured is True
    assert snapshot.core_query_control_plane_base_url_configured is True
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
        json.dumps(_bound_runtime_execution(runtime_execution(), proof_ref=proof.as_posix())),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof))
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot(evaluated_at_utc=EVALUATED_AT)

    assert snapshot.configured_live_proof_available is True
    assert snapshot.core_query_base_url_configured is True
    assert snapshot.core_query_control_plane_base_url_configured is True
    assert snapshot.live_core_source_proof_valid is True
    assert snapshot.configured_scheduled_worker_source_contract_available is False
    assert snapshot.scheduled_worker_source_contract_valid is False
    assert snapshot.configured_scheduled_worker_deployment_evidence_available is False
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert "live_core_source_proof_missing" not in snapshot.certification_blockers
    assert snapshot.certification_blockers == (
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    )
    assert snapshot.certification_status == "not_certified"


def test_source_ingestion_readiness_keeps_live_core_blocker_for_unbound_valid_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    proof = tmp_path / "live-proof.json"
    proof.write_text(
        json.dumps(runtime_execution()),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof))
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot(evaluated_at_utc=EVALUATED_AT)

    assert snapshot.configured_live_proof_available is True
    assert snapshot.live_core_source_proof_valid is False
    assert "live_core_source_proof_missing" in snapshot.certification_blockers


def test_source_ingestion_readiness_keeps_live_core_blocker_for_invalid_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    proof = tmp_path / "live-proof.json"
    proof.write_text('{"schemaVersion": "wrong"}', encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof))
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_live_proof_available is True
    assert snapshot.live_core_source_proof_valid is False
    assert "live_core_source_proof_missing" in snapshot.certification_blockers


def _bound_runtime_execution(
    payload: dict[str, Any],
    *,
    proof_ref: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "source-ingestion-runtime-execution.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        bound = bind_aggregate_proof_provenance(
            payload,
            artifact_path=artifact_path,
            proof_ref=proof_ref,
            repository_root=ROOT,
        )
        bound["aggregateProofProvenance"]["sourceTreeDirty"] = False
        return bound


def test_source_ingestion_readiness_keeps_live_core_blocker_for_malformed_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    proof = tmp_path / "live-proof.json"
    proof.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof))
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_live_proof_available is True
    assert snapshot.live_core_source_proof_valid is False
    assert "live_core_source_proof_missing" in snapshot.certification_blockers


def test_source_contract_does_not_clear_scheduled_worker_deployment_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    contract_path = tmp_path / "scheduled-worker-source-contract.json"
    contract_path.write_text(
        json.dumps(source_contract(repository_root=ROOT)),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.setenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, str(contract_path))
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_scheduled_worker_source_contract_available is True
    assert snapshot.scheduled_worker_source_contract_valid is True
    assert snapshot.configured_scheduled_worker_deployment_evidence_available is False
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert "scheduled_worker_deploy_proof_missing" in snapshot.certification_blockers


def test_deployment_evidence_clears_only_scheduled_worker_deployment_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    evidence_path = tmp_path / "scheduled-worker-deployment-evidence.json"
    source_contract_path = tmp_path / "scheduled-worker-source-contract.json"
    source_contract_path.write_text(
        json.dumps(source_contract(repository_root=ROOT)),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(deployment_evidence(repository_root=ROOT)),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.setenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, str(source_contract_path))
    monkeypatch.setenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, str(evidence_path))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_scheduled_worker_deployment_evidence_available is True
    assert snapshot.scheduled_worker_deployment_evidence_valid is True
    assert "scheduled_worker_deploy_proof_missing" not in snapshot.certification_blockers
    assert snapshot.certification_blockers == (
        "live_core_source_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    )
    assert snapshot.certification_status == "not_certified"


def test_source_ingestion_readiness_keeps_deployment_blocker_for_invalid_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    evidence_path = tmp_path / "scheduled-worker-deployment-evidence.json"
    source_contract_path = tmp_path / "scheduled-worker-source-contract.json"
    source_contract_path.write_text(
        json.dumps(source_contract(repository_root=ROOT)),
        encoding="utf-8",
    )
    evidence_path.write_text('{"schemaVersion": "wrong"}', encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.setenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, str(source_contract_path))
    monkeypatch.setenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, str(evidence_path))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_scheduled_worker_deployment_evidence_available is True
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert "scheduled_worker_deploy_proof_missing" in snapshot.certification_blockers


def test_source_ingestion_readiness_keeps_deployment_blocker_for_malformed_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    evidence_path = tmp_path / "scheduled-worker-deployment-evidence.json"
    source_contract_path = tmp_path / "scheduled-worker-source-contract.json"
    source_contract_path.write_text(
        json.dumps(source_contract(repository_root=ROOT)),
        encoding="utf-8",
    )
    evidence_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.setenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, str(source_contract_path))
    monkeypatch.setenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, str(evidence_path))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_scheduled_worker_deployment_evidence_available is True
    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert "scheduled_worker_deploy_proof_missing" in snapshot.certification_blockers


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
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot(repository_root=tmp_path)

    assert snapshot.example_manifest_available is True
    assert snapshot.configured_manifest_available is True
    assert snapshot.run_once_configured is True


def test_source_ingestion_readiness_supports_split_core_runtime_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.setenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, "http://localhost:8202")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.core_base_url_configured is True
    assert snapshot.core_query_base_url_configured is True
    assert snapshot.core_query_control_plane_base_url_configured is True
    assert snapshot.run_once_configuration_status == "configured"
    assert snapshot.configuration_blockers == ()


def test_source_ingestion_readiness_reports_partial_split_core_url_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(CORE_QUERY_BASE_URL_ENV, "http://localhost:8201")
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.core_base_url_configured is False
    assert snapshot.core_query_base_url_configured is True
    assert snapshot.core_query_control_plane_base_url_configured is False
    assert snapshot.configuration_blockers == (
        "lotus_core_query_control_plane_base_url_not_configured",
        "lotus_core_base_url_not_configured",
    )


def test_source_ingestion_readiness_blocks_unreadable_configured_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_manifest = tmp_path / "missing.json"
    monkeypatch.setenv(MANIFEST_ENV, str(missing_manifest))
    monkeypatch.delenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_source_ingestion_readiness_snapshot()

    assert snapshot.configured_manifest_available is False
    assert snapshot.run_once_configured is False
    assert snapshot.configuration_blockers == ("source_ingestion_manifest_unreadable",)
