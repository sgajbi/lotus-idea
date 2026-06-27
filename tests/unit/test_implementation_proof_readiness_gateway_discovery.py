from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.gateway_workbench_discovery_proof import (
    build_gateway_workbench_discovery_proof_payload,
)
from app.application.gateway_workbench_operational_proof import (
    build_gateway_workbench_operational_proof_payload,
)
from app.application.implementation_proof_readiness import (
    _apply_gateway_workbench_discovery_proof,
    _capability,
    build_implementation_proof_readiness_snapshot,
)
from app.application.platform_mesh_onboarding_proof import (
    build_platform_mesh_onboarding_proof_payload,
)
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload
from app.domain import InMemoryIdeaRepository
from tests.unit.test_gateway_workbench_discovery_proof import _write_platform_fixture


ROOT = Path(__file__).resolve().parents[2]
GENERATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_gateway_workbench_discovery_proof_application_is_noop_for_other_capability() -> None:
    capability = _capability(
        "source-ingestion",
        "Source ingestion",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("gateway_workbench_discovery_proof_missing",),
    )

    result = _apply_gateway_workbench_discovery_proof(
        capability,
        "output/workbench/gateway-workbench-discovery-proof.json",
    )

    assert result is capability


def test_readiness_uses_gateway_workbench_discovery_proof_without_support_promotion(
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_proof(tmp_path)

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=GENERATED_AT_UTC,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        gateway_workbench_discovery_proof=proof,
        gateway_workbench_discovery_proof_ref=(
            "output/workbench/gateway-workbench-discovery-proof.json"
        ),
    )

    assert "gateway_workbench_discovery_proof_missing" not in snapshot.overall_blockers
    assert "data_mesh_not_certified" in snapshot.overall_blockers
    assert "producer_products_not_active" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_product_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    data_mesh = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "data-mesh-certification"
    )
    runtime_telemetry = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "runtime-trust-telemetry-preview"
    )
    assert "gateway_workbench_discovery_proof_missing" not in data_mesh.blockers
    assert "gateway_workbench_discovery_proof_missing" not in runtime_telemetry.blockers
    assert "output/workbench/gateway-workbench-discovery-proof.json" in data_mesh.evidence_refs
    assert (
        "output/workbench/gateway-workbench-discovery-proof.json" in runtime_telemetry.evidence_refs
    )
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_gateway_workbench_discovery_proof(tmp_path: Path) -> dict[str, object]:
    platform_root = _write_platform_fixture(tmp_path)
    workbench_read_path_proof = build_workbench_read_path_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=ROOT,
    )
    return build_gateway_workbench_discovery_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=ROOT,
        platform_root=platform_root,
        platform_mesh_onboarding_proof=build_platform_mesh_onboarding_proof_payload(
            generated_at_utc=GENERATED_AT_UTC,
            repository_root=ROOT,
            platform_root=platform_root,
        ),
        workbench_read_path_proof=workbench_read_path_proof,
        gateway_workbench_operational_proof=build_gateway_workbench_operational_proof_payload(
            generated_at_utc=GENERATED_AT_UTC,
            repository_root=ROOT,
            workbench_read_path_proof=workbench_read_path_proof,
            workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
        ),
        platform_mesh_onboarding_proof_ref="output/data-mesh/platform-mesh-onboarding-proof.json",
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
        gateway_workbench_operational_proof_ref=(
            "output/workbench/gateway-workbench-operational-proof.json"
        ),
    )
