from __future__ import annotations

REQUIRED_LINT_TARGETS = (
    "ci-contract-gate",
    "repository-hygiene-gate",
    "test-client-lifecycle-gate",
    "maintainability-gate",
    "duplicate-implementation-gate",
    "private-import-boundary-gate",
    "foundation-structure-gate",
    "documentation-contract-gate",
    "quality-scorecard-gate",
    "github-issue-closure-matrix-gate",
    "monetary-float-guard",
    "no-sensitive-content-guard",
    "runtime-dependency-closure-gate",
    "license-compliance-gate",
    "source-observability-contract-gate",
    "api-route-metadata-gate",
    "api-problem-details-boundary-gate",
    "api-idempotency-boundary-gate",
    "api-camel-model-boundary-gate",
    "api-signal-model-boundary-gate",
    "api-temporal-validation-boundary-gate",
    "openapi-problem-details-example-gate",
    "caller-context-contract-gate",
    "signal-api-contract-gate",
    "trusted-tenant-context-gate",
    "source-temporal-contract-gate",
    "operation-metric-contract-gate",
    "supported-feature-promotion-contract-gate",
    "ai-model-risk-ops-contract-gate",
    "ai-model-risk-operations-proof-contract-gate",
    "operator-workflows-ops-contract-gate",
    "outbox-supportability-contract-gate",
    "disaster-recovery-contract-gate",
    "operator-workflows-operations-proof-contract-gate",
    "ci-signal-evidence-contract-gate",
    "implementation-truth-gate",
    "data-mesh-contract-gate",
    "mesh-policy-proof-contract-gate",
    "opportunity-archetype-contract-gate",
    "downstream-realization-contract-gate",
    "downstream-route-contract-proof-gate",
    "outbox-event-contract-gate",
    "outbox-consumer-contract-gate",
    "migration-contract-gate",
    "migration-execution-gate",
    "deployment-migration-contract-gate",
    "durable-repository-proof-contract-gate",
    "runtime-trust-telemetry-proof-contract-gate",
    "ai-lineage-store-proof-contract-gate",
    "ai-workflow-pack-registration-proof-contract-gate",
    "ai-workflow-pack-runtime-execution-proof-contract-gate",
    "lotus-ai-attestation-contract-proof-gate",
    "ai-provider-retention-contract-gate",
    "archive-lifecycle-posture-contract-gate",
    "report-intake-route-source-contract-proof-gate",
    "report-materialization-source-contract-proof-gate",
    "workbench-read-path-source-contract-proof-gate",
    "gateway-workbench-contract-proof-contract-gate",
    "gateway-workbench-discovery-contract-proof-contract-gate",
    "outbox-broker-source-contract-proof-gate",
    "outbox-consumer-contract-proof-contract-gate",
    "outbox-platform-mesh-event-source-contract-proof-gate",
    "platform-mesh-onboarding-proof-contract-gate",
    "source-ingestion-worker-check",
    "source-ingestion-scheduled-worker-check",
    "source-ingestion-live-proof-contract-gate",
    "risk-concentration-live-proof-contract-gate",
    "high-volatility-live-proof-contract-gate",
    "risk-drawdown-live-proof-contract-gate",
    "core-benchmark-assignment-live-proof-contract-gate",
    "core-portfolio-state-live-proof-contract-gate",
    "bond-maturity-live-proof-contract-gate",
    "missing-benchmark-live-proof-contract-gate",
    "missing-benchmark-performance-readiness-proof-contract-gate",
    "low-income-core-cashflow-live-proof-contract-gate",
    "manage-mandate-live-proof-contract-gate",
    "mandate-restriction-live-proof-contract-gate",
    "mandate-restriction-source-product-proof-contract-gate",
    "missing-suitability-live-proof-contract-gate",
    "missing-risk-profile-source-product-proof-contract-gate",
    "missing-risk-profile-live-proof-contract-gate",
    "performance-underperformance-live-proof-contract-gate",
    "runtime-trust-telemetry-preview-check",
    "supported-features-gate",
    "endpoint-certification-gate",
)
TEST_TARGET_EXPECTATIONS = {
    "test-unit": "$(VENV_PYTHON) -m pytest $(UNIT_TESTS)",
    "test-integration": "$(VENV_PYTHON) -m pytest $(INTEGRATION_TESTS)",
    "test-e2e": "$(VENV_PYTHON) -m pytest $(E2E_TESTS)",
    "test-unit-coverage": (
        "COVERAGE_FILE=.coverage.unit $(VENV_PYTHON) -m pytest $(UNIT_TESTS) "
        "--cov=src --cov-report="
    ),
    "test-integration-coverage": (
        "COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest "
        "$(INTEGRATION_TESTS) --cov=src --cov-report="
    ),
    "test-e2e-coverage": (
        "COVERAGE_FILE=.coverage.e2e $(VENV_PYTHON) -m pytest $(E2E_TESTS) --cov=src --cov-report="
    ),
}
REQUIRED_TEST_SELECTORS = {
    "UNIT_TESTS ?= tests/unit": "Makefile must define UNIT_TESTS for scoped unit validation",
    "INTEGRATION_TESTS ?= tests/integration": (
        "Makefile must define INTEGRATION_TESTS for scoped integration validation"
    ),
    "E2E_TESTS ?= tests/e2e": "Makefile must define E2E_TESTS for scoped e2e validation",
    "COVERAGE_DATA_DIR ?= .": "Makefile must define COVERAGE_DATA_DIR for coverage artifacts",
}

GENERATED_READINESS_ARTIFACTS = (
    (
        "scripts/generate_scheduled_source_ingestion_worker_proof.py",
        "a scheduled source-ingestion worker proof artifact",
    ),
    (
        "scripts/persistence/generate_durable_repository_proof.py",
        "durable repository proof artifact",
    ),
    ("scripts/generate_runtime_trust_telemetry_proof.py", "runtime telemetry proof artifact"),
    ("scripts/generate_ai_lineage_store_proof.py", "an AI lineage store proof artifact"),
    (
        "scripts/ai_workflow_pack_registration/generate_source_contract_proof.py",
        "an AI workflow-pack registration source-contract proof artifact",
    ),
    (
        "scripts/generate_ai_workflow_pack_runtime_execution_proof.py",
        "an AI workflow-pack runtime execution proof artifact",
    ),
    (
        "scripts/workbench/generate_read_path_source_contract.py",
        "Workbench read-path source-contract proof artifact",
    ),
    (
        "scripts/outbox/broker/generate_source_contract_proof.py",
        "outbox broker source-contract proof artifact",
    ),
    (
        "scripts/outbox/generate_consumer_contract_proof.py",
        "an outbox consumer contract proof artifact",
    ),
    (
        "scripts/outbox/platform_mesh/generate_source_contract_proof.py",
        "an outbox platform-mesh event source-contract proof artifact",
    ),
    ("scripts/generate_advise_proposal_route_proof.py", "an Advise proposal route proof artifact"),
    ("scripts/generate_manage_action_route_proof.py", "a Manage action route proof artifact"),
    (
        "scripts/report/generate_intake_route_source_contract.py",
        "a Report intake-route source-contract proof artifact",
    ),
    (
        "scripts/report/generate_materialization_source_contract.py",
        "a report materialization source-contract artifact",
    ),
    ("scripts/generate_mesh_policy_proof.py", "mesh policy proof artifact"),
    (
        "scripts/generate_platform_mesh_onboarding_proof.py",
        "a platform mesh onboarding proof artifact",
    ),
    (
        "scripts/workbench/generate_contract_proof.py",
        "a Gateway/Workbench contract proof artifact",
    ),
    (
        "scripts/workbench/generate_discovery_contract_proof.py",
        "a Gateway/Workbench discovery contract proof artifact",
    ),
    (
        "scripts/generate_mandate_restriction_source_product_proof.py",
        "a mandate/restriction source-product proof artifact",
    ),
)

PASSED_READINESS_ARTIFACTS = (
    (
        "--source-ingestion-scheduled-worker-proof",
        "scheduled source-ingestion worker proof artifact",
    ),
    ("--durable-repository-proof", "durable repository proof artifact"),
    ("--runtime-trust-telemetry-proof", "runtime trust telemetry proof artifact"),
    ("--ai-lineage-store-proof", "AI lineage store proof artifact"),
    (
        "--ai-workflow-pack-registration-proof",
        "AI workflow-pack registration source-contract proof artifact",
    ),
    (
        "--ai-workflow-pack-runtime-execution-proof",
        "AI workflow-pack runtime execution proof artifact",
    ),
    ("--advise-proposal-route-proof", "Advise proposal route proof artifact"),
    ("--manage-action-route-proof", "Manage action route proof artifact"),
    (
        "--report-intake-route-source-contract-proof",
        "Report intake-route source-contract proof artifact",
    ),
    (
        "--report-materialization-source-contract-proof",
        "report materialization source contract artifact",
    ),
    ("--mesh-policy-proof", "mesh policy proof artifact"),
    (
        "--workbench-read-path-source-contract-proof",
        "Workbench read-path source-contract proof artifact",
    ),
    (
        "--outbox-broker-source-contract-proof",
        "outbox broker source-contract proof artifact",
    ),
    ("--outbox-consumer-contract-proof", "outbox consumer contract proof artifact"),
    (
        "--outbox-platform-mesh-event-source-contract-proof",
        "outbox platform-mesh event source-contract proof artifact",
    ),
    ("--platform-mesh-onboarding-proof", "platform mesh onboarding proof artifact"),
    ("--gateway-workbench-contract-proof", "Gateway/Workbench contract proof artifact"),
    (
        "--gateway-workbench-discovery-contract-proof",
        "Gateway/Workbench discovery contract proof artifact",
    ),
    (
        "--mandate-restriction-source-product-proof",
        "Mandate/restriction source-product proof artifact",
    ),
)

REQUIRED_READINESS_WIRING = (
    ("--source-ingestion-manifest", "pass the source-ingestion manifest"),
    ("LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT", "pass the default AI lineage proof"),
    ("LOTUS_IDEA_AI_LINEAGE_STORE_PROOF", "support optional AI lineage proof wiring"),
    (
        "LOTUS_AI_ROOT",
        "support default lotus-ai root wiring for AI workflow-pack registration proof generation",
    ),
    (
        "LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT",
        "pass the default AI workflow-pack registration proof output into readiness generation",
    ),
    ("LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF", "support optional AI pack proof"),
    (
        "LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT",
        "pass the default AI workflow-pack runtime execution proof output into readiness generation",
    ),
    ("LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF", "support AI runtime proof"),
    ("LOTUS_ADVISE_ROOT", "support default lotus-advise root wiring"),
    ("LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT", "pass default Advise proof"),
    ("LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF", "support optional Advise proof"),
    ("LOTUS_MANAGE_ROOT", "support default lotus-manage root wiring"),
    ("LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT", "pass default Manage proof"),
    ("LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF", "support optional Manage proof"),
    (
        "LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT",
        "pass the default Report intake-route source-contract proof into readiness generation",
    ),
    (
        "LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT",
        "pass default materialization source contract",
    ),
    (
        "LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF",
        "support optional materialization source contract",
    ),
    ("LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT", "pass default mesh policy proof"),
    ("LOTUS_IDEA_MESH_POLICY_PROOF", "support optional mesh policy proof"),
    (
        "LOTUS_PLATFORM_ROOT",
        "support default platform root wiring for platform mesh onboarding proof generation",
    ),
    (
        "LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT",
        "pass the default platform mesh onboarding proof output into readiness generation",
    ),
    ("LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF", "support optional onboarding proof"),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT",
        "pass the default Gateway/Workbench contract proof output into readiness generation",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF",
        "support optional Gateway/Workbench contract proof wiring",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT",
        "pass the default Gateway/Workbench discovery contract proof output into readiness generation",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF",
        "support optional Gateway/Workbench discovery contract proof wiring",
    ),
    ("LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT", "pass default outbox proof"),
    ("LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF", "support optional outbox proof"),
    (
        "LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT",
        "pass default outbox platform-mesh event source-contract proof",
    ),
    (
        "LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF",
        "support optional outbox platform-mesh event source-contract proof",
    ),
    (
        "--allow-missing-evidence",
        "keep cross-repo proof generation CI-stable when sibling evidence is absent",
    ),
    (
        "--source-ingestion-live-proof",
        "support optional live source-ingestion proof artifact wiring",
    ),
    (
        "LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF",
        "support optional Risk concentration live proof artifact wiring",
    ),
    (
        "--risk-concentration-live-proof",
        "pass optional Risk concentration live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF",
        "support optional Performance underperformance live proof artifact wiring",
    ),
    (
        "--performance-underperformance-live-proof",
        "pass optional Performance underperformance live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF",
        "support optional Performance benchmark-readiness proof wiring for missing-benchmark review",
    ),
    (
        "--missing-benchmark-performance-readiness-proof",
        "pass optional Performance benchmark-readiness proof into readiness generation",
    ),
    (
        "LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF",
        "support optional Core benchmark assignment live proof artifact wiring",
    ),
    (
        "--core-benchmark-assignment-live-proof",
        "pass optional Core benchmark assignment live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF",
        "support optional Core portfolio-state live proof artifact wiring",
    ),
    (
        "--core-portfolio-state-live-proof",
        "pass optional Core portfolio-state live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF",
        "support optional Core bond maturity live proof artifact wiring",
    ),
    (
        "--bond-maturity-live-proof",
        "pass optional Core bond maturity live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF",
        "support optional Core cashflow live proof artifact wiring",
    ),
    (
        "--low-income-core-cashflow-live-proof",
        "pass optional Core cashflow live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF",
        "support optional Risk drawdown live proof artifact wiring",
    ),
    (
        "--risk-drawdown-live-proof",
        "pass optional Risk drawdown live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF",
        "support optional Manage mandate live proof artifact wiring",
    ),
    (
        "--manage-mandate-live-proof",
        "pass optional Manage mandate live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF",
        "support optional Advise mandate/restriction live proof artifact wiring",
    ),
    (
        "--mandate-restriction-live-proof",
        "pass optional Advise mandate/restriction live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF",
        "support optional Advise mandate/restriction source-product proof artifact wiring",
    ),
    (
        "LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT",
        "support default Advise mandate/restriction source-product proof output wiring",
    ),
    (
        "--mandate-restriction-source-product-proof",
        "pass optional Advise mandate/restriction source-product proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF",
        "support optional Advise missing suitability live proof artifact wiring",
    ),
    (
        "--missing-suitability-live-proof",
        "pass optional Advise missing suitability live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF",
        "support optional Advise missing risk-profile live proof artifact wiring",
    ),
    (
        "LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF",
        "support optional Advise missing risk-profile source-product proof artifact wiring",
    ),
    (
        "LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT",
        "support default Advise missing risk-profile source-product proof output wiring",
    ),
    (
        "--missing-risk-profile-live-proof",
        "pass optional Advise missing risk-profile live proof artifact into readiness generation",
    ),
    (
        "--missing-risk-profile-source-product-proof",
        "pass optional Advise missing risk-profile source-product proof artifact into readiness generation",
    ),
    ("--core-query-base-url", "support optional Core query-service URL wiring"),
    (
        "--core-query-control-plane-base-url",
        "support optional Core query-control-plane URL wiring",
    ),
    (
        "IMPLEMENTATION_PROOF_OUTPUT",
        "support optional implementation proof output artifact wiring",
    ),
)
