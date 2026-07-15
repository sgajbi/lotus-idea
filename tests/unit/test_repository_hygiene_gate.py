from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_repository_hygiene_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "repository_hygiene_gate.py"
    spec = importlib.util.spec_from_file_location("repository_hygiene_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_hygiene_gate_passes_current_tracked_files() -> None:
    module = _load_repository_hygiene_gate()
    tracked_paths = module._tracked_paths()

    assert module.find_repository_hygiene_violations(tracked_paths) == []
    assert module.find_bounded_module_placement_violations(tracked_paths) == []
    assert module.find_executable_naming_violations(tracked_paths) == []


def test_repository_hygiene_gate_blocks_python_cache_artifacts() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            "src/app/__pycache__/main.cpython-313.pyc",
            "tests/unit/test_example.py",
        ]
    )

    assert violations == [
        "src/app/__pycache__/main.cpython-313.pyc: "
        "generated or dependency directory content must not be tracked"
    ]


def test_repository_hygiene_gate_blocks_local_env_and_coverage_artifacts() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            ".env",
            "coverage.xml",
            "quality/quality_scorecard.md",
        ]
    )

    assert violations == [
        ".env: generated or local-only artifact must not be tracked",
        "coverage.xml: generated or local-only artifact must not be tracked",
    ]


def test_repository_hygiene_gate_blocks_build_outputs_and_databases() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_repository_hygiene_violations(
        [
            "build/lib/app.py",
            "dist/lotus_idea-0.1.0.tar.gz",
            "local/test.db",
        ]
    )

    assert violations == [
        "build/lib/app.py: generated or dependency directory content must not be tracked",
        "dist/lotus_idea-0.1.0.tar.gz: "
        "generated or dependency directory content must not be tracked",
        "local/test.db: generated or local-only file type must not be tracked",
    ]


def test_repository_hygiene_gate_enforces_lifecycle_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    tracked_paths = sorted(
        module.REQUIRED_BOUNDED_MODULE_PATHS - {"src/app/domain/data_lifecycle/authority.py"}
        | {"src/app/domain/lifecycle_authority.py"}
    )

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        "src/app/domain/data_lifecycle/authority.py: required bounded-module path is missing",
        "src/app/domain/lifecycle_authority.py: legacy flat-module path must not be reintroduced",
    ]


def test_repository_hygiene_gate_enforces_runtime_trust_telemetry_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/runtime_trust_telemetry/generate_test_execution_contract.py",
        "scripts/runtime_trust_telemetry/test_execution_contract_gate.py",
        "src/app/application/runtime_trust_telemetry/telemetry.py",
        "src/app/application/runtime_trust_telemetry/test_execution_contract.py",
        "tests/unit/runtime_trust_telemetry/test_implementation_proof_generation.py",
        "tests/unit/runtime_trust_telemetry/test_telemetry.py",
        "tests/unit/runtime_trust_telemetry/test_test_execution_contract.py",
    }
    retired_paths = {
        "scripts/generate_runtime_trust_telemetry_preview.py",
        "scripts/generate_runtime_trust_telemetry_proof.py",
        "scripts/runtime_trust_telemetry_proof_contract_gate.py",
        "src/app/application/runtime_trust_telemetry.py",
        "src/app/application/runtime_trust_telemetry_proof.py",
        "tests/unit/test_runtime_trust_telemetry.py",
        "tests/unit/test_runtime_trust_telemetry_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_source_ingestion_runtime_evidence_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/source_ingestion/__init__.py",
        "scripts/source_ingestion/generate_runtime_execution.py",
        "scripts/source_ingestion/runtime_execution_contract_gate.py",
        "src/app/application/source_ingestion_runtime_evidence/__init__.py",
        "src/app/application/source_ingestion_runtime_evidence/runtime_execution.py",
        "tests/unit/source_ingestion_runtime_evidence/__init__.py",
        "tests/unit/source_ingestion_runtime_evidence/test_aggregate_readiness.py",
        "tests/unit/source_ingestion_runtime_evidence/test_contract_gate.py",
        "tests/unit/source_ingestion_runtime_evidence/test_runtime_execution.py",
    }
    retired_paths = {
        "scripts/generate_source_ingestion_live_proof.py",
        "scripts/source_ingestion_live_proof_contract_gate.py",
        "src/app/application/source_ingestion_live_proof.py",
        "tests/unit/test_source_ingestion_aggregate_proof_readiness.py",
        "tests/unit/test_source_ingestion_live_proof.py",
        "tests/unit/test_source_ingestion_live_proof_contract_gate.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_performance_runtime_evidence_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/performance_underperformance_runtime_evidence/__init__.py",
        "scripts/performance_underperformance_runtime_evidence/generate_runtime_execution.py",
        "scripts/performance_underperformance_runtime_evidence/runtime_execution_contract_gate.py",
        "src/app/application/performance_runtime_evidence/request_identity.py",
        "src/app/application/performance_underperformance_runtime_evidence/contract.py",
        "src/app/application/performance_underperformance_runtime_evidence/runtime_execution.py",
        "tests/support/performance_underperformance_runtime_evidence.py",
        "tests/unit/performance_underperformance_runtime_evidence/test_contract_gate.py",
        "tests/unit/performance_underperformance_runtime_evidence/test_runtime_execution.py",
    }
    retired_paths = {
        "scripts/generate_performance_underperformance_live_proof.py",
        "scripts/performance_underperformance_live_proof_contract_gate.py",
        "src/app/application/performance_underperformance_live_proof.py",
        "tests/unit/test_performance_underperformance_live_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_core_benchmark_runtime_evidence_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/core_benchmark_assignment_runtime_evidence/__init__.py",
        "scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py",
        "scripts/core_benchmark_assignment_runtime_evidence/runtime_execution_contract_gate.py",
        "src/app/application/core_benchmark_assignment_runtime_evidence/__init__.py",
        "src/app/application/core_benchmark_assignment_runtime_evidence/contract.py",
        "src/app/application/core_benchmark_assignment_runtime_evidence/runtime_execution.py",
        "tests/support/core_benchmark_assignment_runtime_evidence.py",
        "tests/unit/core_benchmark_assignment_runtime_evidence/__init__.py",
        "tests/unit/core_benchmark_assignment_runtime_evidence/test_generator.py",
        "tests/unit/core_benchmark_assignment_runtime_evidence/test_runtime_execution.py",
    }
    retired_paths = {
        "scripts/core_benchmark_assignment_live_proof_contract_gate.py",
        "scripts/generate_core_benchmark_assignment_live_proof.py",
        "src/app/application/core_benchmark_assignment_live_proof.py",
        "tests/unit/test_core_benchmark_assignment_live_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(f"{path}: legacy flat-module path must not be reintroduced" for path in retired_paths),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_risk_concentration_runtime_evidence_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/risk_concentration_runtime_evidence/__init__.py",
        "scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py",
        "scripts/risk_concentration_runtime_evidence/runtime_execution_contract_gate.py",
        "src/app/application/risk_concentration_runtime_evidence/__init__.py",
        "src/app/application/risk_concentration_runtime_evidence/contract.py",
        "src/app/application/risk_concentration_runtime_evidence/runtime_execution.py",
        "tests/support/risk_concentration_runtime_evidence.py",
        "tests/unit/risk_concentration_runtime_evidence/__init__.py",
        "tests/unit/risk_concentration_runtime_evidence/test_contract_gate.py",
        "tests/unit/risk_concentration_runtime_evidence/test_runtime_execution.py",
    }
    retired_paths = {
        "scripts/generate_risk_concentration_live_proof.py",
        "scripts/risk_concentration_live_proof_contract_gate.py",
        "src/app/application/risk_concentration_live_proof.py",
        "tests/unit/test_risk_concentration_live_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_outbox_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "src/app/domain/outbox/delivery.py",
        "src/app/domain/outbox/events.py",
        "tests/unit/outbox/postgres_fake_helpers.py",
    }
    retired_paths = {
        "src/app/domain/events.py",
        "src/app/domain/outbox_delivery_state.py",
        "tests/unit/postgres_outbox_fake_helpers.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        "src/app/domain/events.py: legacy flat-module path must not be reintroduced",
        "src/app/domain/outbox/delivery.py: required bounded-module path is missing",
        "src/app/domain/outbox/events.py: required bounded-module path is missing",
        "src/app/domain/outbox_delivery_state.py: legacy flat-module path must not be reintroduced",
        "tests/unit/outbox/postgres_fake_helpers.py: required bounded-module path is missing",
        "tests/unit/postgres_outbox_fake_helpers.py: legacy flat-module path must not be reintroduced",
    ]


def test_repository_hygiene_gate_enforces_outbox_broker_proof_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/outbox/broker/generate_source_contract_proof.py",
        "scripts/outbox/broker/source_contract_proof_gate.py",
        "src/app/application/outbox/broker/source_contract_proof.py",
        "tests/unit/outbox/broker/test_readiness_consumption.py",
        "tests/unit/outbox/broker/test_source_contract_proof.py",
    }
    retired_paths = {
        "scripts/outbox/broker_proof_contract_gate.py",
        "scripts/outbox/generate_broker_proof.py",
        "src/app/application/outbox/broker_proof.py",
        "tests/unit/outbox/test_outbox_broker_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_report_intake_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/report/generate_intake_route_source_contract.py",
        "scripts/report/intake_route_source_contract_gate.py",
        "src/app/application/report/intake_route_source_contract.py",
        "tests/unit/report/test_intake_route_source_contract.py",
    }
    retired_paths = {
        "scripts/generate_report_intake_route_proof.py",
        "scripts/report_intake_route_proof_contract_gate.py",
        "src/app/application/report_intake_route_proof.py",
        "tests/unit/test_report_intake_route_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_downstream_route_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/downstream_realization/__init__.py",
        "scripts/downstream_realization/generate_advise_route_source_contract.py",
        "scripts/downstream_realization/generate_manage_route_source_contract.py",
        "scripts/downstream_realization/route_source_contract_gate.py",
        "src/app/application/downstream_realization/__init__.py",
        "src/app/application/downstream_realization/route_source_contract.py",
        "src/app/application/downstream_realization/submission_use_cases.py",
        "tests/unit/downstream_realization/__init__.py",
        "tests/unit/downstream_realization/fixtures.py",
        "tests/unit/downstream_realization/test_route_source_contract.py",
    }
    retired_paths = {
        "scripts/downstream_route_contract_proof_gate.py",
        "scripts/generate_advise_proposal_route_proof.py",
        "scripts/generate_manage_action_route_proof.py",
        "src/app/application/downstream_route_contract_proof.py",
        "src/app/application/downstream_realization.py",
        "tests/support/downstream_route_contract_fixtures.py",
        "tests/support/downstream_route_source_contract_fixtures.py",
        "tests/unit/test_downstream_route_contract_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_report_materialization_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/report/generate_materialization_source_contract.py",
        "scripts/report/materialization_source_contract_gate.py",
        "src/app/application/report/materialization_source_contract.py",
        "tests/unit/report/test_materialization_source_contract.py",
    }
    retired_paths = {
        "scripts/generate_report_materialization_proof.py",
        "scripts/report_materialization_proof_contract_gate.py",
        "src/app/application/report_materialization_proof.py",
        "tests/unit/test_report_materialization_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_outbox_platform_mesh_proof_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/outbox/platform_mesh/generate_source_contract_proof.py",
        "scripts/outbox/platform_mesh/source_contract_proof_gate.py",
        "src/app/application/outbox/platform_mesh/source_contract_proof.py",
        "tests/unit/outbox/platform_mesh/test_readiness_consumption.py",
        "tests/unit/outbox/platform_mesh/test_source_contract_proof.py",
    }
    retired_paths = {
        "scripts/outbox/generate_platform_mesh_event_publication_proof.py",
        "scripts/outbox/platform_mesh_event_publication_proof_contract_gate.py",
        "src/app/application/outbox/platform_mesh_event_publication_proof.py",
        "tests/unit/outbox/test_outbox_platform_mesh_event_publication_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_persistence_bounded_module_placement() -> None:
    module = _load_repository_hygiene_gate()
    required_path = "src/app/infrastructure/persistence/aggregate_mutation.py"
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - {required_path})

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [f"{required_path}: required bounded-module path is missing"]


def test_repository_hygiene_gate_enforces_workbench_proof_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/workbench/contract_proof_gate.py",
        "scripts/workbench/generate_contract_proof.py",
        "src/app/application/workbench/contract_proof.py",
        "tests/unit/workbench/test_contract_proof.py",
    }
    retired_paths = {
        "scripts/gateway_workbench_contract_proof_contract_gate.py",
        "scripts/generate_gateway_workbench_contract_proof.py",
        "src/app/application/gateway_workbench_contract_proof.py",
        "tests/unit/test_gateway_workbench_contract_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        "scripts/gateway_workbench_contract_proof_contract_gate.py: "
        "legacy flat-module path must not be reintroduced",
        "scripts/generate_gateway_workbench_contract_proof.py: "
        "legacy flat-module path must not be reintroduced",
        "scripts/workbench/contract_proof_gate.py: required bounded-module path is missing",
        "scripts/workbench/generate_contract_proof.py: required bounded-module path is missing",
        "src/app/application/gateway_workbench_contract_proof.py: "
        "legacy flat-module path must not be reintroduced",
        "src/app/application/workbench/contract_proof.py: required bounded-module path is missing",
        "tests/unit/test_gateway_workbench_contract_proof.py: "
        "legacy flat-module path must not be reintroduced",
        "tests/unit/workbench/test_contract_proof.py: required bounded-module path is missing",
    ]


def test_repository_hygiene_gate_enforces_workbench_discovery_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/workbench/discovery_contract_proof_gate.py",
        "scripts/workbench/generate_discovery_contract_proof.py",
        "src/app/application/workbench/discovery_contract_proof.py",
        "tests/unit/workbench/test_discovery_contract_proof.py",
    }
    retired_paths = {
        "scripts/gateway_workbench_discovery_proof_contract_gate.py",
        "scripts/gateway_workbench_discovery_contract_proof_contract_gate.py",
        "scripts/generate_gateway_workbench_discovery_proof.py",
        "scripts/generate_gateway_workbench_discovery_contract_proof.py",
        "src/app/application/gateway_workbench_discovery_proof.py",
        "src/app/application/gateway_workbench_discovery_contract_proof.py",
        "tests/unit/test_gateway_workbench_discovery_proof.py",
        "tests/unit/test_gateway_workbench_discovery_contract_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_platform_catalog_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/data_mesh/generate_platform_catalog_source_contract.py",
        "scripts/data_mesh/platform_catalog_source_contract_gate.py",
        "src/app/application/data_mesh/platform_catalog_source_contract.py",
        "tests/unit/data_mesh/test_platform_catalog_source_contract.py",
    }
    retired_paths = {
        "scripts/generate_platform_mesh_onboarding_proof.py",
        "scripts/platform_mesh_onboarding_proof_contract_gate.py",
        "src/app/application/platform_mesh_onboarding_proof.py",
        "tests/unit/test_platform_mesh_onboarding_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_mesh_policy_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/data_mesh/generate_mesh_policy_source_contract.py",
        "scripts/data_mesh/mesh_policy_source_contract_gate.py",
        "src/app/application/data_mesh/mesh_policy_source_contract.py",
        "tests/unit/data_mesh/test_mesh_policy_source_contract.py",
    }
    retired_paths = {
        "scripts/generate_mesh_policy_proof.py",
        "scripts/mesh_policy_proof_contract_gate.py",
        "src/app/application/mesh_policy_proof.py",
        "tests/unit/test_mesh_policy_proof.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_enforces_review_queue_domain_package() -> None:
    module = _load_repository_hygiene_gate()
    required_path = "src/app/domain/review_queue/snapshot.py"
    retired_path = "src/app/domain/review_queue_snapshot.py"
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - {required_path} | {retired_path})

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == [
        f"{required_path}: required bounded-module path is missing",
        f"{retired_path}: legacy flat-module path must not be reintroduced",
    ]


def test_repository_hygiene_gate_enforces_ai_attestation_source_contract_package() -> None:
    module = _load_repository_hygiene_gate()
    required_paths = {
        "scripts/ai_attestation/generate_source_contract.py",
        "scripts/ai_attestation/source_contract_gate.py",
        "src/app/application/ai_attestation/source_contract.py",
        "tests/support/ai_attestation/source_fixture.py",
        "tests/unit/ai_attestation/test_source_contract.py",
        "tests/unit/ai_attestation/test_source_contract_automation.py",
    }
    retired_paths = {
        "scripts/generate_lotus_ai_attestation_contract_proof.py",
        "scripts/lotus_ai_attestation_contract_proof_gate.py",
        "src/app/application/lotus_ai_attestation_contract_proof.py",
        "tests/support/lotus_ai_attestation_source_fixture.py",
        "tests/unit/test_generate_lotus_ai_attestation_contract_proof.py",
        "tests/unit/test_lotus_ai_attestation_contract_proof.py",
        "tests/unit/test_lotus_ai_attestation_contract_proof_gate.py",
    }
    tracked_paths = sorted(module.REQUIRED_BOUNDED_MODULE_PATHS - required_paths | retired_paths)

    violations = module.find_bounded_module_placement_violations(tracked_paths)

    assert violations == sorted(
        [
            *(
                f"{path}: legacy flat-module path must not be reintroduced"
                for path in retired_paths
            ),
            *(f"{path}: required bounded-module path is missing" for path in required_paths),
        ]
    )


def test_repository_hygiene_gate_rejects_rfc_coupled_executable_names() -> None:
    module = _load_repository_hygiene_gate()

    violations = module.find_executable_naming_violations(
        [
            "scripts/rfc_0002_validator.py",
            "tests/unit/test_slice_06_lifecycle.py",
            "docs/rfcs/RFC-0002-slice-06.md",
        ]
    )

    assert violations == [
        "scripts/rfc_0002_validator.py: executable artifact must be named for its capability, "
        "not an RFC or slice",
        "tests/unit/test_slice_06_lifecycle.py: executable artifact must be named for its "
        "capability, not an RFC or slice",
    ]


def test_repository_hygiene_gate_allows_explicit_rfc_tracking_artifact() -> None:
    module = _load_repository_hygiene_gate()
    tracking_workflow = ".github/workflows/rfc-0002-closure.yml"

    violations = module.find_executable_naming_violations(
        [tracking_workflow, "contracts/rfc-0002-closure.json"],
        rfc_tracking_paths=frozenset({tracking_workflow}),
    )

    assert violations == []
