from __future__ import annotations

SCRIPT_TARGET_EXPECTATIONS = {
    "deployment-migration-contract-gate": "scripts/deployment_migration_contract_gate.py",
    "foundation-structure-gate": "scripts/foundation_structure_gate.py",
    "source-ingestion-worker-check": "scripts/source_ingestion_worker_contract_gate.py",
    "source-ingestion-scheduled-worker-check": (
        "scripts/source_ingestion_scheduled_worker_contract_gate.py"
    ),
    "source-ingestion-runtime-execution-contract-gate": (
        "scripts/source_ingestion/runtime_execution_contract_gate.py"
    ),
    "risk-concentration-live-proof-contract-gate": (
        "scripts/risk_concentration_runtime_evidence/runtime_execution_contract_gate.py"
    ),
    "performance-underperformance-live-proof-contract-gate": (
        "scripts/performance_underperformance_runtime_evidence/runtime_execution_contract_gate.py"
    ),
    "core-benchmark-assignment-live-proof-contract-gate": (
        "scripts/core_benchmark_assignment_runtime_evidence/runtime_execution_contract_gate.py"
    ),
    "core-portfolio-state-live-proof-contract-gate": (
        "scripts/core_portfolio_state_live_proof_contract_gate.py"
    ),
    "bond-maturity-live-proof-contract-gate": "scripts/bond_maturity_live_proof_contract_gate.py",
    "missing-benchmark-live-proof-contract-gate": (
        "scripts/missing_benchmark_live_proof_contract_gate.py"
    ),
    "missing-benchmark-performance-readiness-proof-contract-gate": (
        "scripts/missing_benchmark_performance_readiness_proof_contract_gate.py"
    ),
    "low-income-core-cashflow-live-proof-contract-gate": (
        "scripts/low_income_core_cashflow_live_proof_contract_gate.py"
    ),
    "risk-drawdown-live-proof-contract-gate": (
        "scripts/risk_drawdown_runtime_evidence/runtime_execution_contract_gate.py"
    ),
    "manage-mandate-live-proof-contract-gate": "scripts/manage_mandate_live_proof_contract_gate.py",
    "mandate-restriction-live-proof-contract-gate": (
        "scripts/mandate_restriction_live_proof_contract_gate.py"
    ),
    "mandate-restriction-source-product-proof-contract-gate": (
        "scripts/mandate_restriction_source_product_proof_contract_gate.py"
    ),
    "missing-suitability-live-proof-contract-gate": (
        "scripts/missing_suitability_live_proof_contract_gate.py"
    ),
    "missing-risk-profile-source-product-proof-contract-gate": (
        "scripts/missing_risk_profile_source_product_proof_contract_gate.py"
    ),
    "missing-risk-profile-live-proof-contract-gate": (
        "scripts/missing_risk_profile_live_proof_contract_gate.py"
    ),
    "mesh-policy-source-contract-proof-gate": (
        "scripts/data_mesh/mesh_policy_source_contract_gate.py"
    ),
    "opportunity-archetype-contract-gate": "scripts/opportunity_archetype_contract_gate.py",
    "durable-repository-proof-contract-gate": (
        "scripts/persistence/durable_repository_proof_contract_gate.py"
    ),
    "runtime-trust-telemetry-test-execution-contract-gate": (
        "scripts/runtime_trust_telemetry/test_execution_contract_gate.py"
    ),
    "ai-lineage-store-proof-contract-gate": "scripts/ai_lineage_store_proof_contract_gate.py",
    "ai-workflow-pack-registration-proof-contract-gate": (
        "scripts/ai_workflow_pack_registration/source_contract_proof_gate.py"
    ),
    "ai-workflow-pack-runtime-execution-proof-contract-gate": (
        "scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py"
    ),
    "ai-attestation-source-contract-gate": ("scripts/ai_attestation/source_contract_gate.py"),
    "downstream-route-source-contract-proof-gate": "scripts/downstream_realization/route_source_contract_gate.py",
    "report-intake-route-source-contract-proof-gate": "scripts/report/intake_route_source_contract_gate.py",
    "report-materialization-source-contract-proof-gate": (
        "scripts/report/materialization_source_contract_gate.py"
    ),
    "workbench-read-path-source-contract-proof-gate": (
        "scripts/workbench/read_path_source_contract_gate.py"
    ),
    "gateway-workbench-contract-proof-contract-gate": ("scripts/workbench/contract_proof_gate.py"),
    "gateway-workbench-discovery-contract-proof-contract-gate": (
        "scripts/workbench/discovery_contract_proof_gate.py"
    ),
    "outbox-broker-source-contract-proof-gate": (
        "scripts/outbox/broker/source_contract_proof_gate.py"
    ),
    "outbox-consumer-contract-proof-contract-gate": (
        "scripts/outbox/consumer_contract_proof_contract_gate.py"
    ),
    "outbox-platform-mesh-event-source-contract-proof-gate": (
        "scripts/outbox/platform_mesh/source_contract_proof_gate.py"
    ),
    "outbox-consumer-contract-gate": "scripts/outbox/consumer_contract_gate.py",
    "api-route-metadata-gate": "scripts/api_route_metadata_gate.py",
    "api-problem-details-boundary-gate": "scripts/api_problem_details_boundary_gate.py",
    "api-idempotency-boundary-gate": "scripts/api_idempotency_boundary_gate.py",
    "api-camel-model-boundary-gate": "scripts/api_camel_model_boundary_gate.py",
    "api-signal-model-boundary-gate": "scripts/api_signal_model_boundary_gate.py",
    "api-temporal-validation-boundary-gate": ("scripts/api_temporal_validation_boundary_gate.py"),
    "openapi-problem-details-example-gate": "scripts/openapi_problem_details_example_gate.py",
    "caller-context-contract-gate": "scripts/caller_context_contract_gate.py",
    "signal-api-contract-gate": "scripts/signal_api_contract_gate.py",
    "trusted-tenant-context-gate": "scripts/trusted_tenant_context_gate.py",
    "source-temporal-contract-gate": "scripts/source_temporal_contract_gate.py",
    "operation-metric-contract-gate": "scripts/operation_metric_contract_gate.py",
    "supported-feature-promotion-contract-gate": (
        "scripts/supported_feature_promotion_contract_gate.py"
    ),
    "ai-model-risk-ops-contract-gate": "scripts/ai_model_risk_operations_contract_gate.py",
    "ai-model-risk-operations-proof-contract-gate": (
        "scripts/ai_model_risk_operations/source_contract_proof_gate.py"
    ),
    "operator-workflows-ops-contract-gate": "scripts/operator_workflows_operations_contract_gate.py",
    "outbox-supportability-contract-gate": "scripts/outbox/supportability_contract_gate.py",
    "disaster-recovery-contract-gate": "scripts/disaster_recovery_contract_gate.py",
    "data-lifecycle-contract-gate": "scripts/data_lifecycle_contract_gate.py",
    "scheduled-data-lifecycle-review": "scripts/data_lifecycle/run_scheduled_review.py",
    "scheduled-data-lifecycle-seed": "scripts/data_lifecycle/seed_scheduled_review_fixture.py",
    "scheduled-data-lifecycle-review-proof-gate": (
        "scripts/data_lifecycle/scheduled_review_proof_gate.py"
    ),
    "disaster-recovery-proof-gate": "scripts/disaster_recovery_proof_contract_gate.py",
    "postgres-disaster-recovery-seed": ("scripts/seed_postgres_disaster_recovery_fixture.py"),
    "postgres-disaster-recovery-drill": ("scripts/run_postgres_disaster_recovery_drill.py"),
    "postgres-disaster-recovery-resume": ("scripts/validate_postgres_disaster_recovery_resume.py"),
    "operator-workflows-operations-proof-contract-gate": (
        "scripts/operator_workflows_operations/source_contract_proof_gate.py"
    ),
    "ci-signal-evidence-contract-gate": "scripts/ci_signal_evidence_contract_gate.py",
    "high-volatility-live-proof-contract-gate": (
        "scripts/high_volatility_runtime_evidence/runtime_execution_contract_gate.py"
    ),
    "private-import-boundary-gate": "scripts/private_import_boundary_gate.py",
    "runtime-dependency-closure-gate": "scripts/runtime_dependency_closure_gate.py",
    "license-compliance-gate": "scripts/license_compliance_gate.py",
    "license-release-evidence-gate": "scripts/license_compliance_gate.py",
    "duplicate-implementation-inventory": "scripts/duplicate_implementation_inventory.py",
    "github-issue-closure-matrix-gate": "scripts/github_issue_closure_matrix_gate.py",
    "dependency-refresh": "scripts.refresh_runtime_dependency_locks",
}
