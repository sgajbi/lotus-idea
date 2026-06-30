.PHONY: install lint ci-contract-gate repository-hygiene-gate maintainability-gate private-import-boundary-gate documentation-contract-gate quality-scorecard-gate monetary-float-guard no-sensitive-content-guard source-observability-contract-gate api-route-metadata-gate api-problem-details-boundary-gate api-idempotency-boundary-gate api-camel-model-boundary-gate openapi-problem-details-example-gate signal-api-contract-gate operation-metric-contract-gate ai-model-risk-ops-contract-gate ai-model-risk-operations-proof-contract-gate implementation-truth-gate data-mesh-contract-gate mesh-policy-proof-contract-gate opportunity-archetype-contract-gate downstream-realization-contract-gate downstream-route-contract-proof-gate outbox-event-contract-gate outbox-consumer-contract-gate migration-contract-gate migration-execution-gate durable-repository-proof-contract-gate runtime-trust-telemetry-proof-contract-gate ai-lineage-store-proof-contract-gate ai-workflow-pack-registration-proof-contract-gate ai-workflow-pack-runtime-execution-proof-contract-gate report-intake-route-proof-contract-gate report-materialization-proof-contract-gate workbench-read-path-proof-contract-gate gateway-workbench-operational-proof-contract-gate gateway-workbench-discovery-proof-contract-gate outbox-broker-proof-contract-gate outbox-consumer-runtime-proof-contract-gate outbox-platform-mesh-event-publication-proof-contract-gate platform-mesh-onboarding-proof-contract-gate source-ingestion-worker-check source-ingestion-scheduled-worker-check source-ingestion-live-proof-contract-gate risk-concentration-live-proof-contract-gate high-volatility-live-proof-contract-gate risk-drawdown-live-proof-contract-gate core-benchmark-assignment-live-proof-contract-gate core-portfolio-state-live-proof-contract-gate bond-maturity-live-proof-contract-gate missing-benchmark-live-proof-contract-gate missing-benchmark-performance-readiness-proof-contract-gate low-income-core-cashflow-live-proof-contract-gate manage-mandate-live-proof-contract-gate mandate-restriction-live-proof-contract-gate mandate-restriction-source-product-proof-contract-gate missing-suitability-live-proof-contract-gate missing-risk-profile-source-product-proof-contract-gate missing-risk-profile-live-proof-contract-gate performance-underperformance-live-proof-contract-gate implementation-proof-readiness-check runtime-trust-telemetry-preview-check runtime-trust-telemetry-snapshot-check migrate migrate-rollback supported-features-gate endpoint-certification-gate postgres-integration-gate typecheck architecture-boundary-gate architecture-boundary-report quality-baseline openapi-gate test test-unit test-integration test-e2e test-unit-coverage test-integration-coverage test-e2e-coverage test-coverage coverage-gate security-audit check ci docker-build clean

VENV_DIR ?= .venv
UNIT_TESTS ?= tests/unit
INTEGRATION_TESTS ?= tests/integration
E2E_TESTS ?= tests/e2e
IMPLEMENTATION_PROOF_EVALUATED_AT_UTC ?= 2026-06-21T10:10:00Z
IMPLEMENTATION_PROOF_OUTPUT ?=
LOTUS_CORE_BASE_URL ?=
LOTUS_CORE_QUERY_BASE_URL ?=
LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL ?=
LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF ?=
LOTUS_IDEA_AI_LINEAGE_STORE_PROOF ?=
LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT ?= output/ai/ai-lineage-store-proof.json
LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF ?=
LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT ?= output/ai/ai-model-risk-operations-proof.json
LOTUS_AI_ROOT ?= ../lotus-ai
LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF ?=
LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT ?= output/ai/ai-workflow-pack-registration-proof.json
LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF ?=
LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT ?= output/ai/ai-workflow-pack-runtime-execution-proof.json
LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF ?=
LOTUS_REPORT_ROOT ?= ../lotus-report
LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT ?= output/downstream/report-intake-route-proof.json
LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF ?=
LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT ?= output/downstream/report-materialization-proof.json
LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF ?=
LOTUS_ADVISE_ROOT ?= ../lotus-advise
LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT ?= output/downstream/advise-proposal-route-proof.json
LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF ?=
LOTUS_MANAGE_ROOT ?= ../lotus-manage
LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT ?= output/downstream/manage-action-route-proof.json
LOTUS_IDEA_MESH_POLICY_PROOF ?=
LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT ?= output/data-mesh/mesh-policy-proof.json
LOTUS_PLATFORM_ROOT ?= ../lotus-platform
LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF ?=
LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT ?= output/data-mesh/platform-mesh-onboarding-proof.json
LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF ?=
LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT ?= output/workbench/gateway-workbench-operational-proof.json
LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF ?=
LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT ?= output/workbench/gateway-workbench-discovery-proof.json
LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF ?=
LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT ?= output/outbox/outbox-consumer-runtime-proof.json
LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF ?=
LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT ?= output/outbox/outbox-platform-mesh-event-publication-proof.json
LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF ?=
LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF ?=
LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF ?=
LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF ?=
LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF ?=
LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF ?=
LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF ?=
LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF ?=
LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF ?=
LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF ?=
LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF ?=
LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF ?=
LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT ?= output/opportunity/mandate-restriction-source-product-proof.json
LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF ?=
LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF ?=
LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT ?= output/opportunity/missing-risk-profile-source-product-proof.json
LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF ?=

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
else
VENV_PYTHON := $(VENV_DIR)/bin/python
endif

install:
	python -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

lint:
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m ruff format --check .
	$(MAKE) ci-contract-gate
	$(MAKE) repository-hygiene-gate
	$(MAKE) maintainability-gate
	$(MAKE) private-import-boundary-gate
	$(MAKE) documentation-contract-gate
	$(MAKE) quality-scorecard-gate
	$(MAKE) monetary-float-guard
	$(MAKE) no-sensitive-content-guard
	$(MAKE) source-observability-contract-gate
	$(MAKE) api-route-metadata-gate
	$(MAKE) api-problem-details-boundary-gate
	$(MAKE) api-idempotency-boundary-gate
	$(MAKE) api-camel-model-boundary-gate
	$(MAKE) openapi-problem-details-example-gate
	$(MAKE) signal-api-contract-gate
	$(MAKE) operation-metric-contract-gate
	$(MAKE) ai-model-risk-ops-contract-gate
	$(MAKE) ai-model-risk-operations-proof-contract-gate
	$(MAKE) implementation-truth-gate
	$(MAKE) data-mesh-contract-gate
	$(MAKE) mesh-policy-proof-contract-gate
	$(MAKE) opportunity-archetype-contract-gate
	$(MAKE) downstream-realization-contract-gate
	$(MAKE) downstream-route-contract-proof-gate
	$(MAKE) outbox-event-contract-gate
	$(MAKE) outbox-consumer-contract-gate
	$(MAKE) migration-contract-gate
	$(MAKE) migration-execution-gate
	$(MAKE) durable-repository-proof-contract-gate
	$(MAKE) runtime-trust-telemetry-proof-contract-gate
	$(MAKE) ai-lineage-store-proof-contract-gate
	$(MAKE) ai-workflow-pack-registration-proof-contract-gate
	$(MAKE) ai-workflow-pack-runtime-execution-proof-contract-gate
	$(MAKE) report-intake-route-proof-contract-gate
	$(MAKE) report-materialization-proof-contract-gate
	$(MAKE) workbench-read-path-proof-contract-gate
	$(MAKE) gateway-workbench-operational-proof-contract-gate
	$(MAKE) gateway-workbench-discovery-proof-contract-gate
	$(MAKE) outbox-broker-proof-contract-gate
	$(MAKE) outbox-consumer-runtime-proof-contract-gate
	$(MAKE) outbox-platform-mesh-event-publication-proof-contract-gate
	$(MAKE) platform-mesh-onboarding-proof-contract-gate
	$(MAKE) source-ingestion-worker-check
	$(MAKE) source-ingestion-scheduled-worker-check
	$(MAKE) source-ingestion-live-proof-contract-gate
	$(MAKE) risk-concentration-live-proof-contract-gate
	$(MAKE) high-volatility-live-proof-contract-gate
	$(MAKE) risk-drawdown-live-proof-contract-gate
	$(MAKE) core-benchmark-assignment-live-proof-contract-gate
	$(MAKE) core-portfolio-state-live-proof-contract-gate
	$(MAKE) bond-maturity-live-proof-contract-gate
	$(MAKE) missing-benchmark-live-proof-contract-gate
	$(MAKE) missing-benchmark-performance-readiness-proof-contract-gate
	$(MAKE) low-income-core-cashflow-live-proof-contract-gate
	$(MAKE) manage-mandate-live-proof-contract-gate
	$(MAKE) mandate-restriction-live-proof-contract-gate
	$(MAKE) mandate-restriction-source-product-proof-contract-gate
	$(MAKE) missing-suitability-live-proof-contract-gate
	$(MAKE) missing-risk-profile-source-product-proof-contract-gate
	$(MAKE) missing-risk-profile-live-proof-contract-gate
	$(MAKE) performance-underperformance-live-proof-contract-gate
	$(MAKE) implementation-proof-readiness-check
	$(MAKE) runtime-trust-telemetry-preview-check
	$(MAKE) runtime-trust-telemetry-snapshot-check
	$(MAKE) supported-features-gate
	$(MAKE) endpoint-certification-gate

ci-contract-gate:
	$(VENV_PYTHON) scripts/ci_contract_gate.py

repository-hygiene-gate:
	$(VENV_PYTHON) scripts/repository_hygiene_gate.py

maintainability-gate:
	$(VENV_PYTHON) scripts/maintainability_gate.py

private-import-boundary-gate:
	$(VENV_PYTHON) scripts/private_import_boundary_gate.py

documentation-contract-gate:
	$(VENV_PYTHON) scripts/documentation_contract_gate.py

quality-scorecard-gate:
	$(VENV_PYTHON) scripts/quality_scorecard_gate.py

monetary-float-guard:
	$(VENV_PYTHON) scripts/check_monetary_float_usage.py

no-sensitive-content-guard:
	$(VENV_PYTHON) scripts/no_sensitive_content_guard.py

source-observability-contract-gate:
	$(VENV_PYTHON) scripts/source_observability_contract_gate.py

api-route-metadata-gate:
	$(VENV_PYTHON) scripts/api_route_metadata_gate.py

api-problem-details-boundary-gate:
	$(VENV_PYTHON) scripts/api_problem_details_boundary_gate.py

api-idempotency-boundary-gate:
	$(VENV_PYTHON) scripts/api_idempotency_boundary_gate.py

api-camel-model-boundary-gate:
	$(VENV_PYTHON) scripts/api_camel_model_boundary_gate.py

openapi-problem-details-example-gate:
	$(VENV_PYTHON) scripts/openapi_problem_details_example_gate.py

signal-api-contract-gate:
	$(VENV_PYTHON) scripts/signal_api_contract_gate.py

operation-metric-contract-gate:
	$(VENV_PYTHON) scripts/operation_metric_contract_gate.py

ai-model-risk-ops-contract-gate:
	$(VENV_PYTHON) scripts/ai_model_risk_operations_contract_gate.py

ai-model-risk-operations-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_model_risk_operations_proof_contract_gate.py

implementation-truth-gate:
	$(VENV_PYTHON) scripts/implementation_truth_gate.py

data-mesh-contract-gate:
	$(VENV_PYTHON) scripts/data_mesh_contract_gate.py

mesh-policy-proof-contract-gate:
	$(VENV_PYTHON) scripts/mesh_policy_proof_contract_gate.py

opportunity-archetype-contract-gate:
	$(VENV_PYTHON) scripts/opportunity_archetype_contract_gate.py

downstream-realization-contract-gate:
	$(VENV_PYTHON) scripts/downstream_realization_contract_gate.py

downstream-route-contract-proof-gate:
	$(VENV_PYTHON) scripts/downstream_route_contract_proof_gate.py

outbox-event-contract-gate:
	$(VENV_PYTHON) scripts/outbox_event_contract_gate.py

outbox-consumer-contract-gate:
	$(VENV_PYTHON) scripts/outbox_consumer_contract_gate.py

migration-contract-gate:
	$(VENV_PYTHON) scripts/migration_contract_gate.py

migration-execution-gate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply --dry-run
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback --dry-run

durable-repository-proof-contract-gate:
	$(VENV_PYTHON) scripts/durable_repository_proof_contract_gate.py

runtime-trust-telemetry-proof-contract-gate:
	$(VENV_PYTHON) scripts/runtime_trust_telemetry_proof_contract_gate.py

ai-lineage-store-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_lineage_store_proof_contract_gate.py

ai-workflow-pack-registration-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_workflow_pack_registration_proof_contract_gate.py

ai-workflow-pack-runtime-execution-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py

report-intake-route-proof-contract-gate:
	$(VENV_PYTHON) scripts/report_intake_route_proof_contract_gate.py

report-materialization-proof-contract-gate:
	$(VENV_PYTHON) scripts/report_materialization_proof_contract_gate.py

workbench-read-path-proof-contract-gate:
	$(VENV_PYTHON) scripts/workbench_read_path_proof_contract_gate.py

gateway-workbench-operational-proof-contract-gate:
	$(VENV_PYTHON) scripts/gateway_workbench_operational_proof_contract_gate.py

gateway-workbench-discovery-proof-contract-gate:
	$(VENV_PYTHON) scripts/gateway_workbench_discovery_proof_contract_gate.py

outbox-broker-proof-contract-gate:
	$(VENV_PYTHON) scripts/outbox_broker_proof_contract_gate.py

outbox-consumer-runtime-proof-contract-gate:
	$(VENV_PYTHON) scripts/outbox_consumer_runtime_proof_contract_gate.py

outbox-platform-mesh-event-publication-proof-contract-gate:
	$(VENV_PYTHON) scripts/outbox_platform_mesh_event_publication_proof_contract_gate.py

platform-mesh-onboarding-proof-contract-gate:
	$(VENV_PYTHON) scripts/platform_mesh_onboarding_proof_contract_gate.py

source-ingestion-worker-check:
	$(VENV_PYTHON) scripts/source_ingestion_worker_contract_gate.py

source-ingestion-scheduled-worker-check:
	$(VENV_PYTHON) scripts/source_ingestion_scheduled_worker_contract_gate.py

source-ingestion-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/source_ingestion_live_proof_contract_gate.py

risk-concentration-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/risk_concentration_live_proof_contract_gate.py

high-volatility-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/high_volatility_live_proof_contract_gate.py

risk-drawdown-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/risk_drawdown_live_proof_contract_gate.py

manage-mandate-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/manage_mandate_live_proof_contract_gate.py

mandate-restriction-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/mandate_restriction_live_proof_contract_gate.py

mandate-restriction-source-product-proof-contract-gate:
	$(VENV_PYTHON) scripts/mandate_restriction_source_product_proof_contract_gate.py

missing-suitability-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/missing_suitability_live_proof_contract_gate.py

missing-risk-profile-source-product-proof-contract-gate:
	$(VENV_PYTHON) scripts/missing_risk_profile_source_product_proof_contract_gate.py

missing-risk-profile-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/missing_risk_profile_live_proof_contract_gate.py

performance-underperformance-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/performance_underperformance_live_proof_contract_gate.py

core-benchmark-assignment-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/core_benchmark_assignment_live_proof_contract_gate.py

core-portfolio-state-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/core_portfolio_state_live_proof_contract_gate.py

missing-benchmark-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/missing_benchmark_live_proof_contract_gate.py

missing-benchmark-performance-readiness-proof-contract-gate:
	$(VENV_PYTHON) scripts/missing_benchmark_performance_readiness_proof_contract_gate.py

low-income-core-cashflow-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/low_income_core_cashflow_live_proof_contract_gate.py

bond-maturity-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/bond_maturity_live_proof_contract_gate.py

implementation-proof-readiness-check:
	$(VENV_PYTHON) scripts/generate_scheduled_source_ingestion_worker_proof.py --manifest docs/examples/source-ingestion/high-cash-worker-manifest.example.json --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/source-ingestion/scheduled-worker-proof.json
	$(VENV_PYTHON) scripts/generate_durable_repository_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/persistence/durable-repository-proof.json
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json
	$(VENV_PYTHON) scripts/generate_ai_lineage_store_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_ai_model_risk_operations_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_ai_workflow_pack_registration_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --lotus-ai-root $(LOTUS_AI_ROOT) --output $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_ai_workflow_pack_runtime_execution_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --lotus-ai-root $(LOTUS_AI_ROOT) --output $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_workbench_read_path_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/workbench/workbench-read-path-proof.json
	$(VENV_PYTHON) scripts/generate_gateway_workbench_operational_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --workbench-read-path-proof output/workbench/workbench-read-path-proof.json --output $(LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_outbox_broker_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/outbox/outbox-broker-proof.json
	$(VENV_PYTHON) scripts/generate_outbox_consumer_runtime_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_outbox_platform_mesh_event_publication_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --output $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_advise_proposal_route_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --advise-root $(LOTUS_ADVISE_ROOT) --output $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_manage_action_route_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --manage-root $(LOTUS_MANAGE_ROOT) --output $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_report_intake_route_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --report-root $(LOTUS_REPORT_ROOT) --output $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_report_materialization_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --report-root $(LOTUS_REPORT_ROOT) --output $(LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_mesh_policy_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_platform_mesh_onboarding_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --output $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_gateway_workbench_discovery_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT) --workbench-read-path-proof output/workbench/workbench-read-path-proof.json --gateway-workbench-operational-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT) --output $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_mandate_restriction_source_product_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_missing_risk_profile_source_product_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_implementation_proof_readiness.py --evaluated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --source-ingestion-manifest docs/examples/source-ingestion/high-cash-worker-manifest.example.json $(if $(IMPLEMENTATION_PROOF_OUTPUT),--output $(IMPLEMENTATION_PROOF_OUTPUT),) $(if $(LOTUS_CORE_BASE_URL),--core-base-url $(LOTUS_CORE_BASE_URL),) $(if $(LOTUS_CORE_QUERY_BASE_URL),--core-query-base-url $(LOTUS_CORE_QUERY_BASE_URL),) $(if $(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),--core-query-control-plane-base-url $(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),) $(if $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),--source-ingestion-live-proof $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),) $(if $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF),--ai-model-risk-operations-proof $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF),--ai-model-risk-operations-proof $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),--ai-workflow-pack-registration-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),--ai-workflow-pack-registration-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),--ai-workflow-pack-runtime-execution-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),--ai-workflow-pack-runtime-execution-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),--advise-proposal-route-proof $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),--advise-proposal-route-proof $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF),--report-intake-route-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF),--report-intake-route-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF),--report-materialization-proof $(LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF),--report-materialization-proof $(LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MESH_POLICY_PROOF),--mesh-policy-proof $(LOTUS_IDEA_MESH_POLICY_PROOF),--mesh-policy-proof $(LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF),--platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF),--platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF),--outbox-consumer-runtime-proof $(LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF),--outbox-consumer-runtime-proof $(LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF),--outbox-platform-mesh-event-publication-proof $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF),--outbox-platform-mesh-event-publication-proof $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF),--gateway-workbench-operational-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF),--gateway-workbench-operational-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF),--gateway-workbench-discovery-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF),--gateway-workbench-discovery-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF),--risk-concentration-live-proof $(LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF),) $(if $(LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF),--high-volatility-live-proof $(LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF),--risk-drawdown-live-proof $(LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF),) $(if $(LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF),--performance-underperformance-live-proof $(LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF),--missing-benchmark-performance-readiness-proof $(LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF),) $(if $(LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF),--core-benchmark-assignment-live-proof $(LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF),) $(if $(LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF),--core-portfolio-state-live-proof $(LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF),) $(if $(LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF),--bond-maturity-live-proof $(LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF),--missing-benchmark-live-proof $(LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF),) $(if $(LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF),--low-income-core-cashflow-live-proof $(LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF),--manage-mandate-live-proof $(LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF),--mandate-restriction-live-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF),--mandate-restriction-source-product-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF),--mandate-restriction-source-product-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF),--missing-suitability-live-proof $(LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF),--missing-risk-profile-source-product-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF),--missing-risk-profile-source-product-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF),--missing-risk-profile-live-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF),) --source-ingestion-scheduled-worker-proof output/source-ingestion/scheduled-worker-proof.json --durable-repository-proof output/persistence/durable-repository-proof.json --runtime-trust-telemetry-proof output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json --workbench-read-path-proof output/workbench/workbench-read-path-proof.json --outbox-broker-proof output/outbox/outbox-broker-proof.json

runtime-trust-telemetry-preview-check:
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_preview.py --generated-at-utc 2026-06-21T10:10:00Z

runtime-trust-telemetry-snapshot-check:
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_snapshot.py --generated-at-utc 2026-06-21T10:10:00Z

migrate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply

migrate-rollback:
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback

supported-features-gate:
	$(VENV_PYTHON) scripts/supported_features_gate.py

endpoint-certification-gate:
	$(VENV_PYTHON) scripts/endpoint_certification_gate.py

postgres-integration-gate:
	$(VENV_PYTHON) -m pytest tests/integration/test_postgres_runtime_integration.py

typecheck:
	$(VENV_PYTHON) -m mypy --config-file mypy.ini

architecture-boundary-gate:
	$(VENV_PYTHON) scripts/architecture_boundary_gate.py --mode blocking

architecture-boundary-report:
	$(VENV_PYTHON) scripts/architecture_boundary_gate.py --mode report-only

quality-baseline: architecture-boundary-report
	$(VENV_PYTHON) scripts/generate_quality_baseline.py

openapi-gate:
	$(VENV_PYTHON) scripts/openapi_quality_gate.py

test:
	$(MAKE) test-unit

test-unit:
	$(VENV_PYTHON) -m pytest $(UNIT_TESTS)

test-integration:
	$(VENV_PYTHON) -m pytest $(INTEGRATION_TESTS)

test-e2e:
	$(VENV_PYTHON) -m pytest $(E2E_TESTS)

test-unit-coverage:
	COVERAGE_FILE=.coverage.unit $(VENV_PYTHON) -m pytest $(UNIT_TESTS) --cov=src --cov-report=

test-integration-coverage:
	COVERAGE_FILE=.coverage.integration $(VENV_PYTHON) -m pytest $(INTEGRATION_TESTS) --cov=src --cov-report=

test-e2e-coverage:
	COVERAGE_FILE=.coverage.e2e $(VENV_PYTHON) -m pytest $(E2E_TESTS) --cov=src --cov-report=

test-coverage: test-unit-coverage test-integration-coverage test-e2e-coverage
	$(MAKE) coverage-gate

coverage-gate:
	$(VENV_PYTHON) scripts/coverage_gate.py

security-audit:
	$(VENV_PYTHON) -m pip_audit -r requirements/shared-runtime.lock.txt -r requirements/ci-tooling.lock.txt

check: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test

ci: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test-integration test-e2e test-coverage security-audit

docker-build:
	docker build -t backend-service:ci-test .

clean:
	python scripts/clean_generated_artifacts.py
