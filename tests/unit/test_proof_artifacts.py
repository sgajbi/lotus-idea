from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_workflow_pack_registration_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.gateway_workbench_operational_proof import (
    GATEWAY_WORKBENCH_OPERATIONAL_PROOF_ENV,
)
from app.application.gateway_workbench_discovery_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV,
)
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
)
from app.application.outbox_broker_proof import OUTBOX_BROKER_PROOF_ENV
from app.application.outbox_platform_mesh_event_publication_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
)
from app.application.platform_mesh_onboarding_proof import PLATFORM_MESH_ONBOARDING_PROOF_ENV
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.workbench_read_path_proof import WORKBENCH_READ_PATH_PROOF_ENV
from app.runtime.proof_artifacts import configured_implementation_proof_artifacts


def test_configured_implementation_proof_artifacts_loads_relative_source_safe_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    durable_path = tmp_path / "output" / "persistence" / "durable-repository-proof.json"
    runtime_path = (
        tmp_path / "output" / "trust-telemetry" / "runtime" / "runtime-trust-telemetry-proof.json"
    )
    ai_lineage_path = tmp_path / "output" / "ai" / "ai-lineage-store-proof.json"
    ai_workflow_pack_path = tmp_path / "output" / "ai" / "ai-workflow-pack-registration-proof.json"
    ai_runtime_path = tmp_path / "output" / "ai" / "ai-workflow-pack-runtime-execution-proof.json"
    workbench_path = tmp_path / "output" / "workbench" / "workbench-read-path-proof.json"
    gateway_workbench_path = (
        tmp_path / "output" / "workbench" / "gateway-workbench-operational-proof.json"
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
    for path in (
        durable_path,
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
        low_income_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"artifact": path.name}), encoding="utf-8")

    monkeypatch.setenv(
        DURABLE_REPOSITORY_PROOF_ENV,
        "output/persistence/durable-repository-proof.json",
    )
    monkeypatch.setenv(
        RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
        "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json",
    )
    monkeypatch.setenv(
        AI_LINEAGE_STORE_PROOF_ENV,
        "output/ai/ai-lineage-store-proof.json",
    )
    monkeypatch.setenv(
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        "output/ai/ai-workflow-pack-registration-proof.json",
    )
    monkeypatch.setenv(
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
        "output/ai/ai-workflow-pack-runtime-execution-proof.json",
    )
    monkeypatch.setenv(
        WORKBENCH_READ_PATH_PROOF_ENV,
        "output/workbench/workbench-read-path-proof.json",
    )
    monkeypatch.setenv(
        GATEWAY_WORKBENCH_OPERATIONAL_PROOF_ENV,
        "output/workbench/gateway-workbench-operational-proof.json",
    )
    monkeypatch.setenv(
        GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV,
        "output/workbench/gateway-workbench-discovery-proof.json",
    )
    monkeypatch.setenv(
        OUTBOX_BROKER_PROOF_ENV,
        "output/outbox/outbox-broker-proof.json",
    )
    monkeypatch.setenv(
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
        "output/outbox/outbox-platform-mesh-event-publication-proof.json",
    )
    monkeypatch.setenv(
        PLATFORM_MESH_ONBOARDING_PROOF_ENV,
        "output/data-mesh/platform-mesh-onboarding-proof.json",
    )
    monkeypatch.setenv(
        LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
        "output/opportunity-archetypes/low-income-core-cashflow-live-proof.json",
    )

    artifacts = configured_implementation_proof_artifacts(repository_root=tmp_path)

    assert artifacts.durable_repository_proof == {"artifact": "durable-repository-proof.json"}
    assert artifacts.durable_repository_proof_ref == (
        "output/persistence/durable-repository-proof.json"
    )
    assert artifacts.runtime_trust_telemetry_proof == {
        "artifact": "runtime-trust-telemetry-proof.json"
    }
    assert artifacts.runtime_trust_telemetry_proof_ref == (
        "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
    )
    assert artifacts.ai_lineage_store_proof == {"artifact": "ai-lineage-store-proof.json"}
    assert artifacts.ai_lineage_store_proof_ref == "output/ai/ai-lineage-store-proof.json"
    assert artifacts.ai_workflow_pack_registration_proof == {
        "artifact": "ai-workflow-pack-registration-proof.json"
    }
    assert artifacts.ai_workflow_pack_registration_proof_ref == (
        "output/ai/ai-workflow-pack-registration-proof.json"
    )
    assert artifacts.ai_workflow_pack_runtime_execution_proof == {
        "artifact": "ai-workflow-pack-runtime-execution-proof.json"
    }
    assert artifacts.ai_workflow_pack_runtime_execution_proof_ref == (
        "output/ai/ai-workflow-pack-runtime-execution-proof.json"
    )
    assert artifacts.workbench_read_path_proof == {"artifact": "workbench-read-path-proof.json"}
    assert (
        artifacts.workbench_read_path_proof_ref == "output/workbench/workbench-read-path-proof.json"
    )
    assert artifacts.gateway_workbench_operational_proof == {
        "artifact": "gateway-workbench-operational-proof.json"
    }
    assert artifacts.gateway_workbench_operational_proof_ref == (
        "output/workbench/gateway-workbench-operational-proof.json"
    )
    assert artifacts.gateway_workbench_discovery_proof == {
        "artifact": "gateway-workbench-discovery-proof.json"
    }
    assert artifacts.gateway_workbench_discovery_proof_ref == (
        "output/workbench/gateway-workbench-discovery-proof.json"
    )
    assert artifacts.outbox_broker_proof == {"artifact": "outbox-broker-proof.json"}
    assert artifacts.outbox_broker_proof_ref == "output/outbox/outbox-broker-proof.json"
    assert artifacts.outbox_platform_mesh_event_publication_proof == {
        "artifact": "outbox-platform-mesh-event-publication-proof.json"
    }
    assert artifacts.outbox_platform_mesh_event_publication_proof_ref == (
        "output/outbox/outbox-platform-mesh-event-publication-proof.json"
    )
    assert artifacts.platform_mesh_onboarding_proof == {
        "artifact": "platform-mesh-onboarding-proof.json"
    }
    assert artifacts.platform_mesh_onboarding_proof_ref == (
        "output/data-mesh/platform-mesh-onboarding-proof.json"
    )
    assert artifacts.low_income_core_cashflow_live_proof == {
        "artifact": "low-income-core-cashflow-live-proof.json"
    }
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
