from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_workflow_pack_registration_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.bond_maturity_live_proof import BOND_MATURITY_LIVE_PROOF_ENV
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.gateway_workbench_discovery_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV,
)
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
)
from app.application.outbox.broker_proof import OUTBOX_BROKER_PROOF_ENV
from app.application.outbox.platform_mesh_event_publication_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
)
from app.application.platform_mesh_onboarding_proof import PLATFORM_MESH_ONBOARDING_PROOF_ENV
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.source_ingestion_readiness import LIVE_PROOF_ENV
from app.application.workbench_read_path_proof import WORKBENCH_READ_PATH_PROOF_ENV
from app.runtime.proof_artifacts import configured_implementation_proof_artifacts


def test_configured_implementation_proof_artifacts_loads_relative_source_safe_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    durable_path = tmp_path / "output" / "persistence" / "durable-repository-proof.json"
    source_ingestion_live_path = (
        tmp_path / "output" / "source-ingestion" / "source-ingestion-live-proof.json"
    )
    runtime_path = (
        tmp_path / "output" / "trust-telemetry" / "runtime" / "runtime-trust-telemetry-proof.json"
    )
    ai_lineage_path = tmp_path / "output" / "ai" / "ai-lineage-store-proof.json"
    ai_workflow_pack_path = tmp_path / "output" / "ai" / "ai-workflow-pack-registration-proof.json"
    ai_runtime_path = tmp_path / "output" / "ai" / "ai-workflow-pack-runtime-execution-proof.json"
    workbench_path = tmp_path / "output" / "workbench" / "workbench-read-path-proof.json"
    gateway_workbench_path = (
        tmp_path / "output" / "workbench" / "gateway-workbench-contract-proof.json"
    )
    gateway_workbench_discovery_path = (
        tmp_path / "output" / "workbench" / "gateway-workbench-discovery-proof.json"
    )
    outbox_path = tmp_path / "output" / "outbox" / "outbox-broker-proof.json"
    outbox_mesh_event_path = (
        tmp_path / "output" / "outbox" / "outbox-platform-mesh-event-publication-proof.json"
    )
    platform_mesh_path = tmp_path / "output" / "data-mesh" / "platform-mesh-onboarding-proof.json"
    low_income_path = (
        tmp_path / "output" / "opportunity-archetypes" / "low-income-core-cashflow-live-proof.json"
    )
    bond_maturity_path = (
        tmp_path / "output" / "opportunity-archetypes" / "bond-maturity-live-proof.json"
    )
    _write_artifacts(
        durable_path,
        source_ingestion_live_path,
        runtime_path,
        ai_lineage_path,
        ai_workflow_pack_path,
        ai_runtime_path,
        workbench_path,
        gateway_workbench_path,
        gateway_workbench_discovery_path,
        outbox_path,
        outbox_mesh_event_path,
        platform_mesh_path,
        bond_maturity_path,
        low_income_path,
    )
    _configure_relative_artifact_env(monkeypatch)

    artifacts = configured_implementation_proof_artifacts(repository_root=tmp_path)

    _assert_bound_artifact(
        artifacts.source_ingestion_live_proof,
        "source-ingestion-live-proof.json",
    )
    assert artifacts.source_ingestion_live_proof_ref == (
        "output/source-ingestion/source-ingestion-live-proof.json"
    )
    _assert_bound_artifact(artifacts.durable_repository_proof, "durable-repository-proof.json")
    assert artifacts.durable_repository_proof_ref == (
        "output/persistence/durable-repository-proof.json"
    )
    _assert_bound_artifact(
        artifacts.runtime_trust_telemetry_proof, "runtime-trust-telemetry-proof.json"
    )
    assert artifacts.runtime_trust_telemetry_proof_ref == (
        "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
    )
    _assert_bound_artifact(artifacts.ai_lineage_store_proof, "ai-lineage-store-proof.json")
    assert artifacts.ai_lineage_store_proof_ref == "output/ai/ai-lineage-store-proof.json"
    _assert_bound_artifact(
        artifacts.ai_workflow_pack_registration_proof,
        "ai-workflow-pack-registration-proof.json",
    )
    assert artifacts.ai_workflow_pack_registration_proof_ref == (
        "output/ai/ai-workflow-pack-registration-proof.json"
    )
    _assert_bound_artifact(
        artifacts.ai_workflow_pack_runtime_execution_proof,
        "ai-workflow-pack-runtime-execution-proof.json",
    )
    assert artifacts.ai_workflow_pack_runtime_execution_proof_ref == (
        "output/ai/ai-workflow-pack-runtime-execution-proof.json"
    )
    _assert_bound_artifact(artifacts.workbench_read_path_proof, "workbench-read-path-proof.json")
    assert (
        artifacts.workbench_read_path_proof_ref == "output/workbench/workbench-read-path-proof.json"
    )
    _assert_bound_artifact(
        artifacts.gateway_workbench_contract_proof,
        "gateway-workbench-contract-proof.json",
    )
    assert artifacts.gateway_workbench_contract_proof_ref == (
        "output/workbench/gateway-workbench-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.gateway_workbench_discovery_proof,
        "gateway-workbench-discovery-proof.json",
    )
    assert artifacts.gateway_workbench_discovery_proof_ref == (
        "output/workbench/gateway-workbench-discovery-proof.json"
    )
    _assert_bound_artifact(artifacts.outbox_broker_proof, "outbox-broker-proof.json")
    assert artifacts.outbox_broker_proof_ref == "output/outbox/outbox-broker-proof.json"
    _assert_bound_artifact(
        artifacts.outbox_platform_mesh_event_publication_proof,
        "outbox-platform-mesh-event-publication-proof.json",
    )
    assert artifacts.outbox_platform_mesh_event_publication_proof_ref == (
        "output/outbox/outbox-platform-mesh-event-publication-proof.json"
    )
    _assert_bound_artifact(
        artifacts.platform_mesh_onboarding_proof,
        "platform-mesh-onboarding-proof.json",
    )
    assert artifacts.platform_mesh_onboarding_proof_ref == (
        "output/data-mesh/platform-mesh-onboarding-proof.json"
    )
    _assert_bound_artifact(artifacts.bond_maturity_live_proof, "bond-maturity-live-proof.json")
    assert artifacts.bond_maturity_live_proof_ref == (
        "output/opportunity-archetypes/bond-maturity-live-proof.json"
    )
    _assert_bound_artifact(
        artifacts.low_income_core_cashflow_live_proof,
        "low-income-core-cashflow-live-proof.json",
    )
    assert artifacts.low_income_core_cashflow_live_proof_ref == (
        "output/opportunity-archetypes/low-income-core-cashflow-live-proof.json"
    )


def test_configured_implementation_proof_artifacts_rejects_non_object_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(DURABLE_REPOSITORY_PROOF_ENV, str(proof_path))

    with pytest.raises(ValueError, match="durable repository proof must be a JSON object"):
        configured_implementation_proof_artifacts(repository_root=tmp_path)


def _write_artifacts(*paths: Path) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"artifact": path.name}), encoding="utf-8")


def _configure_relative_artifact_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env_paths = {
        DURABLE_REPOSITORY_PROOF_ENV: "output/persistence/durable-repository-proof.json",
        LIVE_PROOF_ENV: "output/source-ingestion/source-ingestion-live-proof.json",
        RUNTIME_TRUST_TELEMETRY_PROOF_ENV: (
            "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
        ),
        AI_LINEAGE_STORE_PROOF_ENV: "output/ai/ai-lineage-store-proof.json",
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-registration-proof.json"
        ),
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-runtime-execution-proof.json"
        ),
        WORKBENCH_READ_PATH_PROOF_ENV: "output/workbench/workbench-read-path-proof.json",
        GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV: (
            "output/workbench/gateway-workbench-contract-proof.json"
        ),
        GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV: (
            "output/workbench/gateway-workbench-discovery-proof.json"
        ),
        OUTBOX_BROKER_PROOF_ENV: "output/outbox/outbox-broker-proof.json",
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV: (
            "output/outbox/outbox-platform-mesh-event-publication-proof.json"
        ),
        PLATFORM_MESH_ONBOARDING_PROOF_ENV: (
            "output/data-mesh/platform-mesh-onboarding-proof.json"
        ),
        BOND_MATURITY_LIVE_PROOF_ENV: (
            "output/opportunity-archetypes/bond-maturity-live-proof.json"
        ),
        LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV: (
            "output/opportunity-archetypes/low-income-core-cashflow-live-proof.json"
        ),
    }
    for env_name, path in env_paths.items():
        monkeypatch.setenv(env_name, path)


def _assert_bound_artifact(payload: dict[str, object] | None, artifact_name: str) -> None:
    assert payload is not None
    assert payload["artifact"] == artifact_name
    provenance = payload["aggregateProofProvenance"]
    assert isinstance(provenance, dict)
    assert provenance["repository"] == "lotus-idea"
    assert isinstance(provenance["artifactSha256"], str)
    assert len(provenance["artifactSha256"]) == 64
    assert isinstance(provenance["sourceRevision"], str)
    assert provenance["sourceRevision"]
