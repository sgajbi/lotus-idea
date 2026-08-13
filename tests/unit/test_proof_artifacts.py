from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast

import pytest

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_model_risk_operations.source_contract_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
)
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.bond_maturity_runtime_evidence import BOND_MATURITY_RUNTIME_EXECUTION_ENV
from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.report.materialization_runtime_execution import (
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
)
from app.application.report.intake_route_source_contract import (
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
)
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.workbench.runtime_execution import (
    GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV,
)
from app.application.low_income_cashflow_runtime_evidence import (
    LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.broker.runtime_execution import (
    OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
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
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)
from app.runtime.proof_artifacts import (
    ConfiguredImplementationProofArtifacts,
    _JSON_PROOF_ARTIFACTS,
    _REF_ONLY_PROOF_ARTIFACTS,
    configured_implementation_proof_artifacts,
)


@dataclass(frozen=True)
class ConfiguredArtifactBinding:
    payload_field: str
    ref_field: str
    artifact_name: str
    expected_ref: str


@dataclass(frozen=True)
class ConfiguredRefOnlyArtifactBinding:
    ref_field: str
    env_name: str
    expected_ref: str


CONFIGURED_ARTIFACT_BINDINGS: tuple[ConfiguredArtifactBinding, ...] = (
    ConfiguredArtifactBinding(
        payload_field="source_ingestion_runtime_execution",
        ref_field="source_ingestion_runtime_execution_ref",
        artifact_name="source-ingestion-runtime-execution.json",
        expected_ref="output/source-ingestion/source-ingestion-runtime-execution.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="durable_repository_proof",
        ref_field="durable_repository_proof_ref",
        artifact_name="durable-repository-proof.json",
        expected_ref="output/persistence/durable-repository-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="runtime_trust_telemetry_test_execution",
        ref_field="runtime_trust_telemetry_test_execution_ref",
        artifact_name="runtime-trust-telemetry-test-execution.json",
        expected_ref="output/trust-telemetry/test-execution/runtime-trust-telemetry-test-execution.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="ai_lineage_store_proof",
        ref_field="ai_lineage_store_proof_ref",
        artifact_name="ai-lineage-store-proof.json",
        expected_ref="output/ai/ai-lineage-store-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="ai_model_risk_operations_proof",
        ref_field="ai_model_risk_operations_proof_ref",
        artifact_name="ai-model-risk-operations-proof.json",
        expected_ref="output/ai/ai-model-risk-operations-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="operator_workflows_operations_proof",
        ref_field="operator_workflows_operations_proof_ref",
        artifact_name="operator-workflows-operations-proof.json",
        expected_ref="output/operations/operator-workflows-operations-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="ai_workflow_pack_registration_proof",
        ref_field="ai_workflow_pack_registration_proof_ref",
        artifact_name="ai-workflow-pack-registration-source-contract-proof.json",
        expected_ref="output/ai/ai-workflow-pack-registration-source-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="ai_workflow_pack_runtime_execution_proof",
        ref_field="ai_workflow_pack_runtime_execution_proof_ref",
        artifact_name="ai-workflow-pack-runtime-execution-proof.json",
        expected_ref="output/ai/ai-workflow-pack-runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="advise_intake_runtime_execution_proof",
        ref_field="advise_intake_runtime_execution_proof_ref",
        artifact_name="advise-intake-runtime-execution-proof.json",
        expected_ref="output/downstream/advise-intake-runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="manage_intake_runtime_execution_proof",
        ref_field="manage_intake_runtime_execution_proof_ref",
        artifact_name="manage-intake-runtime-execution-proof.json",
        expected_ref="output/downstream/manage-intake-runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="report_intake_route_source_contract_proof",
        ref_field="report_intake_route_source_contract_proof_ref",
        artifact_name="report-intake-route-source-contract-proof.json",
        expected_ref="output/report/report-intake-route-source-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="report_materialization_runtime_execution_proof",
        ref_field="report_materialization_runtime_execution_proof_ref",
        artifact_name="materialization-runtime-execution-proof.json",
        expected_ref="output/report/materialization-runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="workbench_read_path_source_contract_proof",
        ref_field="workbench_read_path_source_contract_proof_ref",
        artifact_name="read-path-source-contract-proof.json",
        expected_ref="output/workbench/read-path-source-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="gateway_workbench_contract_proof",
        ref_field="gateway_workbench_contract_proof_ref",
        artifact_name="gateway-workbench-contract-proof.json",
        expected_ref="output/workbench/gateway-workbench-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="gateway_workbench_discovery_contract_proof",
        ref_field="gateway_workbench_discovery_contract_proof_ref",
        artifact_name="gateway-workbench-discovery-contract-proof.json",
        expected_ref="output/workbench/gateway-workbench-discovery-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="gateway_workbench_runtime_execution_proof",
        ref_field="gateway_workbench_runtime_execution_proof_ref",
        artifact_name="gateway-workbench-runtime-execution-proof.json",
        expected_ref="output/workbench/gateway-workbench-runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="outbox_broker_source_contract_proof",
        ref_field="outbox_broker_source_contract_proof_ref",
        artifact_name="source-contract-proof.json",
        expected_ref="output/outbox/broker/source-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="outbox_broker_runtime_execution_proof",
        ref_field="outbox_broker_runtime_execution_proof_ref",
        artifact_name="runtime-execution-proof.json",
        expected_ref="output/outbox/broker/runtime-execution-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="outbox_platform_mesh_event_source_contract_proof",
        ref_field="outbox_platform_mesh_event_source_contract_proof_ref",
        artifact_name="event-source-contract-proof.json",
        expected_ref="output/outbox/platform-mesh/event-source-contract-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="platform_catalog_source_contract",
        ref_field="platform_catalog_source_contract_ref",
        artifact_name="platform-catalog-source-contract.json",
        expected_ref="output/data-mesh/platform-catalog-source-contract.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="bond_maturity_live_proof",
        ref_field="bond_maturity_live_proof_ref",
        artifact_name="bond-maturity-live-proof.json",
        expected_ref="output/opportunity-archetypes/bond-maturity-live-proof.json",
    ),
    ConfiguredArtifactBinding(
        payload_field="low_income_core_cashflow_live_proof",
        ref_field="low_income_core_cashflow_live_proof_ref",
        artifact_name="low-income-core-cashflow-live-proof.json",
        expected_ref="output/opportunity-archetypes/low-income-core-cashflow-live-proof.json",
    ),
)


CONFIGURED_REF_ONLY_ARTIFACT_BINDINGS: tuple[ConfiguredRefOnlyArtifactBinding, ...] = (
    ConfiguredRefOnlyArtifactBinding(
        ref_field="source_ingestion_scheduled_worker_source_contract_ref",
        env_name=SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
        expected_ref="output/source-ingestion/scheduled-worker-source-contract.json",
    ),
    ConfiguredRefOnlyArtifactBinding(
        ref_field="source_ingestion_scheduled_worker_deployment_evidence_ref",
        env_name=SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
        expected_ref="output/source-ingestion/scheduled-worker-deployment-evidence.json",
    ),
)


def test_configured_artifact_binding_matrix_covers_runtime_loader_bindings() -> None:
    assert {
        (binding.payload_field, binding.ref_field) for binding in CONFIGURED_ARTIFACT_BINDINGS
    } == {(binding.proof_field, binding.ref_field) for binding in _JSON_PROOF_ARTIFACTS}
    assert {binding.ref_field for binding in CONFIGURED_REF_ONLY_ARTIFACT_BINDINGS} == {
        binding.ref_field for binding in _REF_ONLY_PROOF_ARTIFACTS
    }


def test_configured_implementation_proof_artifacts_loads_relative_source_safe_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_artifacts(*_configured_artifact_paths(tmp_path).values())
    _configure_relative_artifact_env(monkeypatch)

    artifacts = configured_implementation_proof_artifacts(repository_root=tmp_path)

    _assert_configured_artifacts_are_bound(artifacts)
    _assert_ref_only_artifact_refs_are_bound(artifacts)


def test_configured_ref_only_artifacts_resolve_refs_without_json_parsing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for binding in CONFIGURED_REF_ONLY_ARTIFACT_BINDINGS:
        path = tmp_path / binding.expected_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json because this artifact is ref-only", encoding="utf-8")
        monkeypatch.setenv(binding.env_name, binding.expected_ref)

    artifacts = configured_implementation_proof_artifacts(repository_root=tmp_path)

    _assert_ref_only_artifact_refs_are_bound(artifacts)


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
        "ai_model_risk_operations": (
            tmp_path / "output" / "ai" / "ai-model-risk-operations-proof.json"
        ),
        "operator_workflows_operations": (
            tmp_path / "output" / "operations" / "operator-workflows-operations-proof.json"
        ),
        "ai_workflow_pack": (
            tmp_path / "output" / "ai" / "ai-workflow-pack-registration-source-contract-proof.json"
        ),
        "ai_runtime": (
            tmp_path / "output" / "ai" / "ai-workflow-pack-runtime-execution-proof.json"
        ),
        "advise_runtime": (
            tmp_path / "output" / "downstream" / "advise-intake-runtime-execution-proof.json"
        ),
        "manage_runtime": (
            tmp_path / "output" / "downstream" / "manage-intake-runtime-execution-proof.json"
        ),
        "report_intake_route": (
            tmp_path / "output" / "report" / "report-intake-route-source-contract-proof.json"
        ),
        "report_materialization_runtime": (
            tmp_path / "output" / "report" / "materialization-runtime-execution-proof.json"
        ),
        "workbench": (tmp_path / "output" / "workbench" / "read-path-source-contract-proof.json"),
        "gateway_workbench": (
            tmp_path / "output" / "workbench" / "gateway-workbench-contract-proof.json"
        ),
        "gateway_workbench_discovery": (
            tmp_path / "output" / "workbench" / "gateway-workbench-discovery-contract-proof.json"
        ),
        "gateway_workbench_runtime": (
            tmp_path / "output" / "workbench" / "gateway-workbench-runtime-execution-proof.json"
        ),
        "outbox": tmp_path / "output" / "outbox" / "broker" / "source-contract-proof.json",
        "outbox_runtime": (
            tmp_path / "output" / "outbox" / "broker" / "runtime-execution-proof.json"
        ),
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
    for binding in CONFIGURED_ARTIFACT_BINDINGS:
        payload = cast(dict[str, object] | None, getattr(artifacts, binding.payload_field))
        artifact_ref = cast(str, getattr(artifacts, binding.ref_field))

        _assert_bound_artifact(payload, binding.artifact_name)
        assert artifact_ref == binding.expected_ref


def _assert_ref_only_artifact_refs_are_bound(
    artifacts: ConfiguredImplementationProofArtifacts,
) -> None:
    for binding in CONFIGURED_REF_ONLY_ARTIFACT_BINDINGS:
        assert getattr(artifacts, binding.ref_field) == binding.expected_ref


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
        AI_MODEL_RISK_OPERATIONS_PROOF_ENV: "output/ai/ai-model-risk-operations-proof.json",
        OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV: (
            "output/operations/operator-workflows-operations-proof.json"
        ),
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-registration-source-contract-proof.json"
        ),
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV: (
            "output/ai/ai-workflow-pack-runtime-execution-proof.json"
        ),
        ADVISE_INTAKE_RUNTIME_EXECUTION_ENV: (
            "output/downstream/advise-intake-runtime-execution-proof.json"
        ),
        MANAGE_INTAKE_RUNTIME_EXECUTION_ENV: (
            "output/downstream/manage-intake-runtime-execution-proof.json"
        ),
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV: (
            "output/report/report-intake-route-source-contract-proof.json"
        ),
        REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV: (
            "output/report/materialization-runtime-execution-proof.json"
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
        GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV: (
            "output/workbench/gateway-workbench-runtime-execution-proof.json"
        ),
        OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV: (
            "output/outbox/broker/source-contract-proof.json"
        ),
        OUTBOX_BROKER_RUNTIME_EXECUTION_ENV: ("output/outbox/broker/runtime-execution-proof.json"),
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
        SCHEDULED_WORKER_SOURCE_CONTRACT_ENV: (
            "output/source-ingestion/scheduled-worker-source-contract.json"
        ),
        SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV: (
            "output/source-ingestion/scheduled-worker-deployment-evidence.json"
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
