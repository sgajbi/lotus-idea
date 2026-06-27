from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report
from app.application.ai_lineage_store_proof import build_ai_lineage_store_proof_payload
from app.application.ai_model_risk_operations_proof import (
    build_ai_model_risk_operations_proof_payload,
)
from app.application.ai_workflow_pack_registration_proof import (
    build_ai_workflow_pack_registration_proof_payload,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    build_ai_workflow_pack_runtime_execution_proof_payload,
)
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.mesh_policy_proof import build_mesh_policy_proof_payload
from app.application.outbox_broker_proof import build_outbox_broker_proof_payload
from app.application.outbox_consumer_runtime_proof import (
    build_outbox_consumer_runtime_proof_payload,
)
from app.application.runtime_trust_telemetry_proof import (
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
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
from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_fixture,
    write_lotus_ai_workflow_pack_runtime_execution_fixture,
)


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
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert (
        "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json"
        in ai_explanation["evidenceRefs"]
    )
    assert "make ai-model-risk-ops-contract-gate" in ai_explanation["evidenceRefs"]
    assert "make ai-model-risk-operations-proof-contract-gate" in (ai_explanation["evidenceRefs"])
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation["blockers"]
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation["blockers"]
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
    assert "source ingestion scheduled-worker proof artifact" in source_ingestion["evidenceRefs"]
    assert "durable_repository_not_configured" in source_ingestion["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    assert os.environ[MANIFEST_ENV] == "pre-existing-manifest.json"
    assert os.environ[CORE_BASE_URL_ENV] == "http://pre-existing-core"
    assert os.environ[SCHEDULED_WORKER_PROOF_ENV] == "pre-existing-proof.json"


def test_generate_implementation_proof_readiness_uses_explicit_live_source_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(MANIFEST_ENV, "pre-existing-manifest.json")
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://pre-existing-core")
    monkeypatch.setenv(LIVE_PROOF_ENV, "pre-existing-live-proof.json")
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
    live_proof = tmp_path / "source-ingestion-live-proof.json"
    live_proof.write_text(
        json.dumps(
            build_source_ingestion_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                live_core_source_attempted=True,
                worker_summary={
                    "schemaVersion": MANIFEST_SCHEMA_VERSION,
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
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-ingestion-manifest",
            str(manifest),
            "--core-base-url",
            "http://localhost:8310",
            "--source-ingestion-live-proof",
            str(live_proof),
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
    assert "live_core_source_proof_missing" not in source_ingestion["blockers"]
    assert "scheduled_worker_deploy_proof_missing" in source_ingestion["blockers"]
    assert "source ingestion live proof artifact" in source_ingestion["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    assert os.environ[MANIFEST_ENV] == "pre-existing-manifest.json"
    assert os.environ[CORE_BASE_URL_ENV] == "http://pre-existing-core"
    assert os.environ[LIVE_PROOF_ENV] == "pre-existing-live-proof.json"


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
    assert "certified_runtime_trust_telemetry_missing" not in payload["overallBlockers"]
    assert "data_mesh_runtime_telemetry_not_certified" not in payload["overallBlockers"]
    assert "platform_mesh_certification_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_lineage_store_proof(
    tmp_path: Path,
) -> None:
    ai_lineage_proof = tmp_path / "ai-lineage-store-proof.json"
    ai_lineage_proof.write_text(
        json.dumps(
            build_ai_lineage_store_proof_payload(
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
            "--ai-lineage-store-proof",
            str(ai_lineage_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "certified_ai_lineage_store_missing" not in ai_explanation["blockers"]
    assert "certified_ai_lineage_store_missing" not in payload["overallBlockers"]
    assert "lotus_ai_runtime_execution_missing" in ai_explanation["blockers"]
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation["blockers"]
    assert "AI lineage store proof artifact" in ai_explanation["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_model_risk_operations_proof(
    tmp_path: Path,
) -> None:
    ai_model_risk_proof = tmp_path / "ai-model-risk-operations-proof.json"
    ai_model_risk_proof.write_text(
        json.dumps(
            build_ai_model_risk_operations_proof_payload(
                generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-26T00:00:00Z",
            "--ai-model-risk-operations-proof",
            str(ai_model_risk_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation["blockers"]
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation["blockers"]
    assert "AI model-risk operations proof artifact" in ai_explanation["evidenceRefs"]
    assert "certified_runtime_trust_telemetry_missing" in ai_explanation["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_workflow_pack_registration_proof(
    tmp_path: Path,
) -> None:
    ai_workflow_pack_proof = tmp_path / "ai-workflow-pack-registration-proof.json"
    ai_workflow_pack_proof.write_text(
        json.dumps(
            build_ai_workflow_pack_registration_proof_payload(
                generated_at_utc=datetime(2026, 6, 25, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                lotus_ai_root=write_lotus_ai_workflow_pack_fixture(tmp_path),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-25T00:00:00Z",
            "--ai-workflow-pack-registration-proof",
            str(ai_workflow_pack_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "workflow_pack_runtime_contract_not_certified" not in ai_explanation["blockers"]
    assert "workflow_pack_runtime_contract_not_certified" not in payload["overallBlockers"]
    assert "lotus_ai_runtime_execution_missing" in ai_explanation["blockers"]
    assert "AI workflow-pack registration proof artifact" in ai_explanation["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_workflow_pack_runtime_execution_proof(
    tmp_path: Path,
) -> None:
    ai_runtime_proof = tmp_path / "ai-workflow-pack-runtime-execution-proof.json"
    ai_runtime_proof.write_text(
        json.dumps(
            build_ai_workflow_pack_runtime_execution_proof_payload(
                generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                lotus_ai_root=write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-26T00:00:00Z",
            "--ai-workflow-pack-runtime-execution-proof",
            str(ai_runtime_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "lotus_ai_runtime_execution_missing" not in ai_explanation["blockers"]
    assert "lotus_ai_runtime_execution_missing" not in payload["overallBlockers"]
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation["blockers"]
    assert "AI workflow-pack runtime execution proof artifact" in ai_explanation["evidenceRefs"]
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


def test_generate_implementation_proof_readiness_uses_explicit_outbox_broker_proof(
    tmp_path: Path,
) -> None:
    outbox_proof = tmp_path / "outbox-broker-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_proof_payload(
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
            "--outbox-broker-proof",
            str(outbox_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "outbox_broker_not_configured" not in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" not in payload["overallBlockers"]
    assert "downstream_consumer_runtime_proof_missing" in payload["overallBlockers"]
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_outbox_consumer_runtime_proof(
    tmp_path: Path,
) -> None:
    outbox_proof = tmp_path / "outbox-broker-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    consumer_proof = tmp_path / "outbox-consumer-runtime-proof.json"
    consumer_proof.write_text(
        json.dumps(
            build_outbox_consumer_runtime_proof_payload(
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
            "--outbox-broker-proof",
            str(outbox_proof),
            "--outbox-consumer-runtime-proof",
            str(consumer_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "outbox_broker_not_configured" not in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" not in payload["overallBlockers"]
    assert "downstream_consumer_runtime_proof_missing" not in payload["overallBlockers"]
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert "gateway_workbench_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_mesh_policy_proof(
    tmp_path: Path,
) -> None:
    mesh_policy_proof = tmp_path / "mesh-policy-proof.json"
    mesh_policy_proof.write_text(
        json.dumps(
            build_mesh_policy_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--mesh-policy-proof",
            str(mesh_policy_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    data_mesh = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "data-mesh-certification"
    )
    assert "mesh_slo_policy_certification_missing" not in data_mesh["blockers"]
    assert "mesh_access_policy_certification_missing" not in data_mesh["blockers"]
    assert "mesh_evidence_policy_certification_missing" not in data_mesh["blockers"]
    assert "data_mesh_not_certified" in data_mesh["blockers"]
    assert "mesh policy proof artifact" in data_mesh["evidenceRefs"]
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
