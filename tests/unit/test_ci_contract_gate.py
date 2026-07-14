from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_passes_current_repository_contract() -> None:
    module = _load_ci_contract_gate()

    assert module.validate_ci_contract() == []


def test_ci_contract_gate_rejects_floating_action_tags() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7
"""

    errors = module._validate_action_pins("feature-lane.yml", workflow)

    assert errors == [
        "feature-lane.yml:7: actions/checkout must use an immutable 40-character "
        "SHA pin, not a floating tag or branch"
    ]


def test_ci_contract_gate_rejects_unverified_action_sha() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/setup-python@0000000000000000000000000000000000000000 # v6.3.0
"""

    errors = module._validate_action_pins("pr-merge-gate.yml", workflow)

    assert errors == [
        "pr-merge-gate.yml:7: actions/setup-python must pin "
        "ece7cb06caefa5fff74198d8649806c4678c61a1 for verified v6.3.0"
    ]


def test_ci_contract_gate_requires_action_version_provenance_comment() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: docker/setup-buildx-action@d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5
"""

    errors = module._validate_action_pins("main-releasability.yml", workflow)

    assert errors == [
        "main-releasability.yml:7: docker/setup-buildx-action SHA pin must carry "
        "`# v4.1.0` provenance"
    ]


def test_ci_contract_gate_blocks_weakened_clean_target() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "python scripts/clean_generated_artifacts.py",
            "python -c \"print('clean')\"",
        )
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile clean target must run `scripts/clean_generated_artifacts.py`" in errors


def test_ci_contract_gate_blocks_unscoped_unit_test_target() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(VENV_PYTHON) -m pytest $(UNIT_TESTS)", "$(VENV_PYTHON) -m pytest tests/unit")
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile test-unit target must run `$(VENV_PYTHON) -m pytest $(UNIT_TESTS)`" in errors


def test_ci_contract_gate_blocks_unscoped_coverage_test_target() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest "
            "$(INTEGRATION_TESTS) --cov=src --cov-report=",
            "COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest "
            "tests/integration --cov=src --cov-report=",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile test-integration-coverage target must run "
        "`COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest "
        "$(INTEGRATION_TESTS) --cov=src --cov-report=`"
    ) in errors


def test_ci_contract_gate_blocks_stale_implementation_proof_readiness_target() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--source-ingestion-scheduled-worker-proof output/source-ingestion/scheduled-worker-proof.json",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the scheduled "
        "source-ingestion worker proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_durable_repository_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--durable-repository-proof output/persistence/durable-repository-proof.json",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "durable repository proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_runtime_trust_telemetry_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--runtime-trust-telemetry-proof "
            "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "runtime trust telemetry proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_lineage_store_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),"
            "--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),"
            "--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "AI lineage store proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_lineage_store_proof_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/generate_ai_lineage_store_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "an AI lineage store proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_lineage_store_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) ai-lineage-store-proof-contract-gate\n", "")
        .replace(
            "scripts/ai_lineage_store_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) ai-lineage-store-proof-contract-gate`" in errors
    assert (
        "Makefile ai-lineage-store-proof-contract-gate target must run "
        "`scripts/ai_lineage_store_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_opportunity_archetype_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) opportunity-archetype-contract-gate\n", "")
        .replace(
            "scripts/opportunity_archetype_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) opportunity-archetype-contract-gate`" in errors
    assert (
        "Makefile opportunity-archetype-contract-gate target must run "
        "`scripts/opportunity_archetype_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_workflow_pack_runtime_execution_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),"
            "--ai-workflow-pack-runtime-execution-proof "
            "$(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),"
            "--ai-workflow-pack-runtime-execution-proof "
            "$(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT)) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "AI workflow-pack runtime execution proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_workflow_pack_runtime_execution_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "scripts/generate_ai_workflow_pack_runtime_execution_proof.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "an AI workflow-pack runtime execution proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_workflow_pack_runtime_execution_output_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT",
            "REMOVED_AI_WORKFLOW_PACK_RUNTIME_PROOF_OUTPUT",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the default "
        "AI workflow-pack runtime execution proof output into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_ai_workflow_pack_runtime_execution_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) ai-workflow-pack-runtime-execution-proof-contract-gate\n", "")
        .replace(
            "scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call "
        "`$(MAKE) ai-workflow-pack-runtime-execution-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile ai-workflow-pack-runtime-execution-proof-contract-gate target must run "
        "`scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_report_intake_route_source_contract_proof_readiness_wiring() -> (
    None
):
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF),"
            "--report-intake-route-source-contract-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF),"
            "--report-intake-route-source-contract-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT)) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Report intake-route source-contract proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_advise_proposal_route_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),"
            "--advise-proposal-route-proof $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),"
            "--advise-proposal-route-proof "
            "$(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT)) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Advise proposal route proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_manage_action_route_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),"
            "--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),"
            "--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT)) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Manage action route proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_advise_and_manage_route_proof_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/generate_advise_proposal_route_proof.py", "scripts/removed.py")
        .replace("scripts/generate_manage_action_route_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "an Advise proposal route proof artifact"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "a Manage action route proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_downstream_route_contract_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) downstream-route-contract-proof-gate\n", "")
        .replace(
            "scripts/downstream_route_contract_proof_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) downstream-route-contract-proof-gate`" in errors
    assert (
        "Makefile downstream-route-contract-proof-gate target must run "
        "`scripts/downstream_route_contract_proof_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_report_intake_route_source_contract_proof_generation() -> (
    None
):
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/report/generate_intake_route_source_contract.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "a Report intake-route source-contract proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_report_intake_route_default_output_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT",
            "REMOVED_REPORT_PROOF_OUTPUT",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the default "
        "Report intake-route source-contract proof into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_strict_default_report_intake_route_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile").read_text(encoding="utf-8").replace(" --allow-missing-evidence", "")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must keep cross-repo "
        "proof generation CI-stable when sibling evidence is absent"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must keep all cross-repo "
        "proof generators CI-stable when sibling evidence is absent"
    ) in errors


def test_ci_contract_gate_blocks_missing_read_path_source_contract_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--workbench-read-path-source-contract-proof "
            "output/workbench/read-path-source-contract-proof.json",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Workbench read-path source-contract proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_outbox_broker_source_contract_proof_readiness_wiring() -> (
    None
):
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--outbox-broker-source-contract-proof output/outbox/broker/source-contract-proof.json",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "outbox broker source-contract proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_outbox_consumer_contract_proof_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/outbox/generate_consumer_contract_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "an outbox consumer contract proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_outbox_consumer_contract_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--outbox-consumer-contract-proof",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "outbox consumer contract proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_platform_mesh_onboarding_proof_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/generate_platform_mesh_onboarding_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "a platform mesh onboarding proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_platform_mesh_onboarding_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--platform-mesh-onboarding-proof",
            "--removed-platform-mesh-onboarding-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "platform mesh onboarding proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_gateway_workbench_contract_proof_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/workbench/generate_contract_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "a Gateway/Workbench contract proof artifact"
    ) in errors


def test_ci_contract_gate_blocks_missing_gateway_workbench_contract_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--gateway-workbench-contract-proof",
            "--removed-gateway-workbench-contract-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Gateway/Workbench contract proof artifact into readiness generation"
    ) in errors


def test_ci_gate_requires_gateway_workbench_discovery_contract_generation() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("scripts/workbench/generate_discovery_contract_proof.py", "scripts/removed.py")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "a Gateway/Workbench discovery contract proof artifact"
    ) in errors


def test_ci_gate_requires_gateway_workbench_discovery_contract_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "--gateway-workbench-discovery-contract-proof",
            "--removed-gateway-workbench-discovery-contract-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "Gateway/Workbench discovery contract proof artifact into readiness generation"
    ) in errors


def test_ci_gate_requires_gateway_workbench_discovery_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) gateway-workbench-discovery-contract-proof-contract-gate\n", "")
        .replace(
            "scripts/workbench/discovery_contract_proof_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) gateway-workbench-discovery-contract-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile gateway-workbench-discovery-contract-proof-contract-gate target must run "
        "`scripts/workbench/discovery_contract_proof_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_platform_mesh_onboarding_output_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT",
            "REMOVED_PLATFORM_MESH_PROOF_OUTPUT",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the default "
        "platform mesh onboarding proof output into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_platform_mesh_root_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile").read_text(encoding="utf-8").replace("LOTUS_PLATFORM_ROOT", "REMOVED")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support default "
        "platform root wiring for platform mesh onboarding proof generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_live_source_proof_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),"
            "--source-ingestion-live-proof $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support "
        "optional live source-ingestion proof artifact wiring"
    ) in errors


def test_ci_contract_gate_blocks_missing_risk_concentration_live_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF", "REMOVED_RISK_PROOF")
        .replace("--risk-concentration-live-proof", "--removed-risk-concentration-live-proof")
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support "
        "optional Risk concentration live proof artifact wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must pass optional Risk "
        "concentration live proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_performance_underperformance_live_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF",
            "REMOVED_PERFORMANCE_PROOF",
        )
        .replace(
            "--performance-underperformance-live-proof",
            "--removed-performance-underperformance-live-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support optional "
        "Performance underperformance live proof artifact wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must pass optional Performance "
        "underperformance live proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_performance_underperformance_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) performance-underperformance-live-proof-contract-gate\n", "")
        .replace(
            "scripts/performance_underperformance_live_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call "
        "`$(MAKE) performance-underperformance-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile performance-underperformance-live-proof-contract-gate target must run "
        "`scripts/performance_underperformance_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_manage_mandate_live_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF",
            "REMOVED_MANAGE_MANDATE_PROOF",
        )
        .replace(
            "--manage-mandate-live-proof",
            "--removed-manage-mandate-live-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support optional "
        "Manage mandate live proof artifact wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must pass optional Manage "
        "mandate live proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_manage_mandate_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) manage-mandate-live-proof-contract-gate\n", "")
        .replace(
            "scripts/manage_mandate_live_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) manage-mandate-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile manage-mandate-live-proof-contract-gate target must run "
        "`scripts/manage_mandate_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_suitability_live_proof_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF",
            "REMOVED_MISSING_SUITABILITY_PROOF",
        )
        .replace(
            "--missing-suitability-live-proof",
            "--removed-missing-suitability-live-proof",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support optional "
        "Advise missing suitability live proof artifact wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must pass optional Advise "
        "missing suitability live proof artifact into readiness generation"
    ) in errors


def test_ci_contract_gate_blocks_missing_suitability_live_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) missing-suitability-live-proof-contract-gate\n", "")
        .replace(
            "scripts/missing_suitability_live_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) missing-suitability-live-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile missing-suitability-live-proof-contract-gate target must run "
        "`scripts/missing_suitability_live_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_live_core_url_readiness_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(LOTUS_CORE_QUERY_BASE_URL),"
            "--core-query-base-url $(LOTUS_CORE_QUERY_BASE_URL),) ",
            "",
        )
        .replace(
            "$(if $(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),"
            "--core-query-control-plane-base-url "
            "$(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support "
        "optional Core query-service URL wiring"
    ) in errors
    assert (
        "Makefile implementation-proof-readiness-check target must support "
        "optional Core query-control-plane URL wiring"
    ) in errors


def test_ci_contract_gate_blocks_missing_implementation_proof_output_wiring() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "$(if $(IMPLEMENTATION_PROOF_OUTPUT),--output $(IMPLEMENTATION_PROOF_OUTPUT),) ",
            "",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must support "
        "optional implementation proof output artifact wiring"
    ) in errors


def test_ci_contract_gate_blocks_missing_runtime_trust_telemetry_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "scripts/runtime_trust_telemetry_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile runtime-trust-telemetry-proof-contract-gate target must run "
        "`scripts/runtime_trust_telemetry_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_report_intake_route_source_contract_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) report-intake-route-source-contract-proof-gate\n", "")
        .replace(
            "scripts/report/intake_route_source_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) report-intake-route-source-contract-proof-gate`"
        in errors
    )
    assert (
        "Makefile report-intake-route-source-contract-proof-gate target must run "
        "`scripts/report/intake_route_source_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_workbench_read_path_source_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "scripts/workbench/read_path_source_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile workbench-read-path-source-contract-proof-gate target must run "
        "`scripts/workbench/read_path_source_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_outbox_broker_source_contract_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "scripts/outbox/broker/source_contract_proof_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile outbox-broker-source-contract-proof-gate target must run "
        "`scripts/outbox/broker/source_contract_proof_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_outbox_consumer_contract_proof_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "scripts/outbox/consumer_contract_proof_contract_gate.py",
            "scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile outbox-consumer-contract-proof-contract-gate target must run "
        "`scripts/outbox/consumer_contract_proof_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_missing_operation_metric_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace("$(MAKE) operation-metric-contract-gate\n", "")
        .replace(
            "$(VENV_PYTHON) scripts/operation_metric_contract_gate.py",
            "$(VENV_PYTHON) scripts/removed.py",
        )
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) operation-metric-contract-gate`" in errors
    assert (
        "Makefile operation-metric-contract-gate target must run "
        "`scripts/operation_metric_contract_gate.py`"
    ) in errors
