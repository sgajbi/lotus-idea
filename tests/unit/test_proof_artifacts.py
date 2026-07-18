from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.bond_maturity_runtime_evidence import BOND_MATURITY_RUNTIME_EXECUTION_ENV
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.low_income_cashflow_runtime_evidence import (
    LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
)
from app.application.runtime_trust_telemetry.test_execution_contract import (
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
)
from app.application.source_ingestion_readiness import SOURCE_INGESTION_RUNTIME_EXECUTION_ENV
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)
from app.runtime.proof_artifacts import (
    ConfiguredImplementationProofArtifacts,
    configured_implementation_proof_artifacts,
)


def test_configured_implementation_proof_artifacts_loads_relative_source_safe_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_artifacts(*_configured_artifact_paths(tmp_path).values())
    _configure_relative_artifact_env(monkeypatch)

    artifacts = configured_implementation_proof_artifacts(repository_root=tmp_path)

    _assert_configured_artifacts_are_bound(artifacts)


def test_configured_implementation_proof_artifacts_rejects_non_object_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(DURABLE_REPOSITORY_PROOF_ENV, str(proof_path))

    with pytest.raises(ValueError, match="durable repository proof must be a JSON object"):
        configured_implementation_proof_artifacts(repository_root=tmp_path)


def _configured_artifact_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "durable": tmp_path / "output" / "persistence" / "durable-repository-proof.json",
        "source_ingestion_runtime_execution": (
            tmp_path / "output" / "source-ingestion" / "source-ingestion-runtime-execution.json"
        ),
        "runtime": (
            tmp_path
            / "output"
            / "trust-telemetry"
            / "test-execution"
            / "runtime-trust-telemetry-test-execution.json"
        ),
        "ai_lineage": tmp_path / "output" / "ai" / "ai-lineage-store-proof.json",
        "ai_workflow_pack": (
            tmp_path / "output" / "ai" / "ai-workflow-pack-registration-source-contract-proof.json"
        ),
        "ai_runtime": (
            tmp_path / "output" / "ai" / "ai-workflow-pack-runtime-execution-proof.json"
        ),
        "workbench": (tmp_path / "output" / "workbench" / "read-path-source-contract-proof.json"),
        "gateway_workbench": (
            tmp_path / "output" / "workbench" / "gateway-workbench-contract-proof.json"
        ),
        "gateway_workbench_discovery": (
            tmp_path / "output" / "workbench" / "gateway-workbench-discovery-contract-proof.json"
        ),
        "outbox": tmp_path / "output" / "outbox" / "broker" / "source-contract-proof.json",
        "outbox_mesh_event": (
            tmp_path / "output" / "outbox" / "platform-mesh" / "event-source-contract-proof.json"
        ),
        "platform_mesh": (
            tmp_path / "output" / "data-mesh" / "platform-catalog-source-contract.json"
        ),
        "low_income": (
            tmp_path
            / "output"
            / "opportunity-archetypes"
            / "low-income-core-cashflow-live-proof.json"
        ),
        "bond_maturity": (
            tmp_path / "output" / "opportunity-archetypes" / "bond-maturity-live-proof.json"
        ),
    }


def _assert_configured_artifacts_are_bound(
    artifacts: ConfiguredImplementationProofArtifacts,
) -> None:
    _assert_bound_artifact(
        artifacts.source_ingestion_runtime_execution,
        "source-ingestion-runtime-execution.json",
    )
    assert artifacts.source_ingestion_runtime_execution_ref == (
        "output/source-ingestion/source-ingestion-runtime-execution.json"
    )
    _assert_bound_artifact(artifacts.durable_repository_proof, "durable-repository-proof.json")
    assert artifacts.durable_repository_proof_ref == (
        "output/persistence/durable-repository-proof.json"
    )
    _assert_bound_artifact(
        artifacts.runtime_trust_telemetry_test_execution,
        "runtime-trust-telemetry-test-execution.json",
    )
    assert artifacts.runtime_trust_telemetry_test_execution_ref == (
        "output/trust-telemetry/test-execution/runtime-trust-telemetry-test-execution.json"
    )
    _assert_bound_artifact(artifacts.ai_lineage_store_proof, "ai-lineage-store-proof.json")
    assert artifacts.ai_lineage_store_proof_ref == "output/ai/ai-lineage-store-proof.json"
    _assert_bound_artifact(
        artifacts.ai_workflow_pack_registration_proof,
        "ai-workflow-pack-registration-source-contract-proof.json",
    )
    assert artifacts.ai_workflow_pack_registration_proof_ref == (
        "output/ai/ai-workflow-pack-registration-source-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.ai_workflow_pack_runtime_execution_proof,
        "ai-workflow-pack-runtime-execution-proof.json",
    )
    assert artifacts.ai_workflow_pack_runtime_execution_proof_ref == (
        "output/ai/ai-workflow-pack-runtime-execution-proof.json"
    )
    _assert_bound_artifact(
        artifacts.workbench_read_path_source_contract_proof,
        "read-path-source-contract-proof.json",
    )
    assert (
        artifacts.workbench_read_path_source_contract_proof_ref
        == "output/workbench/read-path-source-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.gateway_workbench_contract_proof,
        "gateway-workbench-contract-proof.json",
    )
    assert artifacts.gateway_workbench_contract_proof_ref == (
        "output/workbench/gateway-workbench-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.gateway_workbench_discovery_contract_proof,
        "gateway-workbench-discovery-contract-proof.json",
    )
    assert artifacts.gateway_workbench_discovery_contract_proof_ref == (
        "output/workbench/gateway-workbench-discovery-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.outbox_broker_source_contract_proof,
        "source-contract-proof.json",
    )
    assert artifacts.outbox_broker_source_contract_proof_ref == (
        "output/outbox/broker/source-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.outbox_platform_mesh_event_source_contract_proof,
        "event-source-contract-proof.json",
    )
    assert artifacts.outbox_platform_mesh_event_source_contract_proof_ref == (
        "output/outbox/platform-mesh/event-source-contract-proof.json"
    )
    _assert_bound_artifact(
        artifacts.platform_catalog_source_contract,
        "platform-catalog-source-contract.json",
    )
    assert artifacts.platform_catalog_source_contract_ref == (
        "output/data-mesh/platform-catalog-source-contract.json"
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


def _write_artifacts(*paths: Path) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"artifact": path.name}), encoding="utf-8")


def _configure_relative_artifact_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env_paths = {
        DURABLE_REPOSITORY_PROOF_ENV: "output/persistence/durable-repository-proof.json",
        SOURCE_INGESTION_RUNTIME_EXECUTION_ENV: "output/source-ingestion/source-ingestion-runtime-execution.json",
        RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV: (
            "output/trust-telemetry/test-execution/runtime-trust-telemetry-test-execution.json"
        ),
        AI_LINEAGE_STORE_PROOF_ENV: "output/ai/ai-lineage-store-proof.json",
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-registration-source-contract-proof.json"
        ),
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-runtime-execution-proof.json"
        ),
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV: (
            "output/workbench/read-path-source-contract-proof.json"
        ),
        GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV: (
            "output/workbench/gateway-workbench-contract-proof.json"
        ),
        GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV: (
            "output/workbench/gateway-workbench-discovery-contract-proof.json"
        ),
        OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV: (
            "output/outbox/broker/source-contract-proof.json"
        ),
        OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV: (
            "output/outbox/platform-mesh/event-source-contract-proof.json"
        ),
        PLATFORM_CATALOG_SOURCE_CONTRACT_ENV: (
            "output/data-mesh/platform-catalog-source-contract.json"
        ),
        BOND_MATURITY_RUNTIME_EXECUTION_ENV: (
            "output/opportunity-archetypes/bond-maturity-live-proof.json"
        ),
        LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV: (
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
