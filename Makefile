.PHONY: install dependency-refresh lint ci-contract-gate repository-hygiene-gate test-client-lifecycle-gate maintainability-gate duplicate-implementation-inventory duplicate-implementation-gate private-import-boundary-gate foundation-structure-gate documentation-contract-gate quality-scorecard-gate github-issue-closure-matrix-gate monetary-float-guard no-sensitive-content-guard runtime-dependency-closure-gate source-observability-contract-gate api-route-metadata-gate api-problem-details-boundary-gate api-idempotency-boundary-gate api-camel-model-boundary-gate api-signal-model-boundary-gate api-temporal-validation-boundary-gate openapi-problem-details-example-gate caller-context-contract-gate signal-api-contract-gate trusted-tenant-context-gate source-temporal-contract-gate review-queue-snapshot-contract-gate operation-metric-contract-gate service-slo-capacity-contract-gate ai-model-risk-ops-contract-gate ai-model-risk-operations-proof-contract-gate ci-signal-evidence-contract-gate implementation-truth-gate data-mesh-contract-gate mesh-policy-proof-contract-gate opportunity-archetype-contract-gate downstream-realization-contract-gate downstream-route-contract-proof-gate outbox-event-contract-gate outbox-consumer-contract-gate outbox-recovery-contract-gate migration-contract-gate migration-execution-gate deployment-migration-contract-gate durable-repository-proof-contract-gate runtime-trust-telemetry-proof-contract-gate ai-lineage-store-proof-contract-gate ai-workflow-pack-registration-proof-contract-gate ai-workflow-pack-runtime-execution-proof-contract-gate report-intake-route-source-contract-proof-gate report-materialization-source-contract-proof-gate workbench-read-path-source-contract-proof-gate gateway-workbench-contract-proof-contract-gate gateway-workbench-discovery-contract-proof-contract-gate outbox-broker-source-contract-proof-gate outbox-consumer-contract-proof-contract-gate outbox-platform-mesh-event-source-contract-proof-gate platform-mesh-onboarding-proof-contract-gate source-ingestion-worker-check source-ingestion-scheduled-worker-check source-ingestion-live-proof-contract-gate canonical-opportunity-source-proofs canonical-signal-api-proof risk-concentration-live-proof-contract-gate high-volatility-live-proof-contract-gate risk-drawdown-live-proof-contract-gate core-benchmark-assignment-live-proof-contract-gate core-portfolio-state-live-proof-contract-gate bond-maturity-live-proof-contract-gate missing-benchmark-live-proof-contract-gate missing-benchmark-performance-readiness-proof-contract-gate low-income-core-cashflow-live-proof-contract-gate manage-mandate-live-proof-contract-gate mandate-restriction-live-proof-contract-gate mandate-restriction-source-product-proof-contract-gate missing-suitability-live-proof-contract-gate missing-risk-profile-source-product-proof-contract-gate missing-risk-profile-live-proof-contract-gate performance-underperformance-live-proof-contract-gate implementation-proof-readiness-check runtime-trust-telemetry-preview-check runtime-trust-telemetry-snapshot-check migrate migrate-rollback deployment-migrate supported-features-gate endpoint-certification-gate postgres-integration-gate typecheck architecture-boundary-gate architecture-boundary-report quality-baseline openapi-gate test test-unit test-integration test-e2e test-unit-coverage test-integration-coverage test-e2e-coverage test-coverage security-audit check ci ci-release docker-build container-runtime-smoke release-sbom container-image-scan release-image-identity-contract-gate clean

.PHONY: candidate-state-contract-gate review-identity-contract-gate conversion-outcome-contract-gate outbox-supportability-contract-gate outbox-supportability-rule-test service-slo-rule-test service-capacity-baseline-contract-gate service-load-soak-proof-gate service-resource-baseline-contract-gate service-resource-proof-gate service-capacity-workload downstream-capacity-seed service-resource-baseline postgres-capacity-threshold-proof supported-feature-promotion-contract-gate disaster-recovery-contract-gate disaster-recovery-proof-gate postgres-disaster-recovery-seed postgres-disaster-recovery-drill postgres-disaster-recovery-resume data-lifecycle-contract-gate scheduled-data-lifecycle-seed scheduled-data-lifecycle-review scheduled-data-lifecycle-review-proof-gate
.PHONY: license-compliance-gate license-release-evidence-gate lotus-ai-attestation-contract-proof lotus-ai-attestation-contract-proof-gate ai-provider-retention-contract-gate archive-lifecycle-posture-contract-gate ai-lineage-store-ci-proof durable-repository-ci-proof

VENV_DIR ?= .venv
UNIT_TESTS ?= tests/unit
INTEGRATION_TESTS ?= tests/integration
E2E_TESTS ?= tests/e2e
COVERAGE_DATA_DIR ?= .
CONTAINER_BASE_IMAGE ?= python:3.12-slim
BUILD_GIT_COMMIT_SHA ?= $(if $(GITHUB_SHA),$(GITHUB_SHA),$(shell git rev-parse HEAD 2>/dev/null))
BUILD_GIT_BRANCH ?= $(if $(GITHUB_REF_NAME),$(GITHUB_REF_NAME),$(shell git branch --show-current 2>/dev/null))
BUILD_TIMESTAMP ?= $(shell python -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")
BUILD_REPO_URL ?= $(if $(GITHUB_REPOSITORY),https://github.com/$(GITHUB_REPOSITORY),$(shell git config --get remote.origin.url 2>/dev/null))
BUILD_CI_RUN_ID ?= $(if $(GITHUB_RUN_ID),$(GITHUB_RUN_ID),local)
BUILD_IMAGE_BUILD_ID ?= $(BUILD_GIT_COMMIT_SHA).$(BUILD_CI_RUN_ID)
BUILD_SERVICE_VERSION ?= 0.1.0
BUILD_IMAGE_TAG ?= $(if $(BUILD_GIT_COMMIT_SHA),$(BUILD_GIT_COMMIT_SHA),local)
CONTAINER_IMAGE_NAME ?= lotus-idea:$(BUILD_IMAGE_TAG)
CONTAINER_SCAN_OUTPUT ?= output/security/container-image-scan.trivy.json
CONTAINER_SCAN_SEVERITY ?= HIGH,CRITICAL
CONTAINER_SMOKE_NAME ?= lotus-idea-runtime-smoke
CONTAINER_SMOKE_HOST ?= 127.0.0.1
CONTAINER_SMOKE_HOST_PORT ?= 18330
CONTAINER_SMOKE_CONTAINER_PORT ?= 8330
CONTAINER_SMOKE_TIMEOUT_SECONDS ?= 45
DR_BACKUP_IDENTIFIER ?= dr-$(BUILD_CI_RUN_ID)-$(BUILD_GIT_COMMIT_SHA)
DR_BACKUP_SOURCE ?= ci-disposable-postgres
DR_OPERATOR_ID ?= github-actions
DR_CORRELATION_ID ?= dr-run-$(BUILD_CI_RUN_ID)
DR_RESTORE_EVIDENCE ?= output/disaster-recovery/postgres-restore-evidence.json
DR_RESUME_EVIDENCE ?= output/disaster-recovery/postgres-resume-evidence.json
SCHEDULED_LIFECYCLE_REVIEW_EVIDENCE ?= output/data-lifecycle/scheduled-review-evidence.json
CONTAINER_SMOKE_PROBE_INTERVAL_SECONDS ?= 1
RELEASE_IMAGE_IDENTITY_MANIFEST ?= release-evidence.json
RELEASE_IMAGE_IDENTITY_LABELS ?= release-image-labels.json
RELEASE_IMAGE_IDENTITY_RUNTIME_SMOKE ?= release-runtime-smoke.json
LICENSE_RELEASE_MANIFEST ?= release-evidence.json
LICENSE_RELEASE_SBOM ?= sbom.cdx.json
TRIVY_IMAGE ?= aquasec/trivy:0.71.2
PROMETHEUS_IMAGE ?= prom/prometheus:v2.47.2
IMPLEMENTATION_PROOF_EVALUATED_AT_UTC ?= 2026-06-21T10:10:00Z
IMPLEMENTATION_PROOF_OUTPUT ?=
LOTUS_CORE_BASE_URL ?=
LOTUS_CORE_QUERY_BASE_URL ?=
LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL ?=
LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF ?=
LOTUS_IDEA_AI_LINEAGE_STORE_PROOF ?=
LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT ?= output/ai/ai-lineage-store-proof.json
LOTUS_IDEA_AI_LINEAGE_STORE_CI_RECEIPT ?=
POSTGRES_RUNTIME_PROOF_JUNIT ?= output/persistence/postgres-runtime-proof.junit.xml
POSTGRES_CI_EXECUTION_RECEIPT_OUTPUT ?= output/persistence/postgres-ci-execution-receipt.json
LOTUS_IDEA_DURABLE_REPOSITORY_PROOF_OUTPUT ?= output/persistence/durable-repository-proof.json
LOTUS_IDEA_DURABLE_REPOSITORY_CI_RECEIPT ?=
DURABLE_REPOSITORY_CI_RECEIPT_OUTPUT ?= output/persistence/durable-repository-ci-execution-receipt.json
LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF ?=
LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT ?= output/ai/ai-model-risk-operations-source-contract-proof.json
LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF ?=
LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF_OUTPUT ?= output/operations/operator-workflows-operations-source-contract-proof.json
LOTUS_AI_ROOT ?= ../lotus-ai
LOTUS_AI_BASE_URL ?= http://127.0.0.1:8140
LOTUS_IDEA_AI_RUNTIME_PROOF_TIMEOUT_SECONDS ?= 2
LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF ?=
LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT ?= output/ai/ai-workflow-pack-registration-source-contract-proof.json
LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF ?=
LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT ?= output/ai/ai-workflow-pack-runtime-execution-proof.json
LOTUS_IDEA_LOTUS_AI_ATTESTATION_CONTRACT_PROOF_OUTPUT ?= output/ai/lotus-ai-attestation-contract-proof.json
LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF ?=
LOTUS_REPORT_ROOT ?= ../lotus-report
LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT ?= output/report/intake-route-source-contract-proof.json
LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF ?=
LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT ?= output/report/materialization-source-contract-proof.json
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
LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF ?=
LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT ?= output/workbench/gateway-workbench-contract-proof.json
LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF ?=
LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT ?= output/workbench/gateway-workbench-discovery-contract-proof.json
LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF ?=
LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT ?= output/outbox/outbox-consumer-contract-proof.json
LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF ?=
LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT ?= output/outbox/platform-mesh/event-source-contract-proof.json
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
CANONICAL_OPPORTUNITY_PORTFOLIO_ID ?=
CANONICAL_OPPORTUNITY_AS_OF_DATE ?=
CANONICAL_OPPORTUNITY_RISK_BASE_URL ?=
CANONICAL_OPPORTUNITY_PERFORMANCE_BASE_URL ?=
CANONICAL_OPPORTUNITY_PERIOD_NAME ?= 1Y
CANONICAL_OPPORTUNITY_REPORTING_CURRENCY ?=
CANONICAL_OPPORTUNITY_TIMEOUT_SECONDS ?= 5.0
CANONICAL_OPPORTUNITY_GENERATED_AT_UTC ?=
CANONICAL_OPPORTUNITY_EVALUATED_AT_UTC ?=
CANONICAL_OPPORTUNITY_CORRELATION_ID ?=
CANONICAL_OPPORTUNITY_TRACE_ID ?=
CANONICAL_OPPORTUNITY_OUTPUT_DIRECTORY ?= output/opportunity/canonical-source-proofs
CANONICAL_SIGNAL_API_IDEA_BASE_URL ?= http://idea.dev.lotus
CANONICAL_SIGNAL_API_PERIOD_NAME ?= 1Y
CANONICAL_SIGNAL_API_REPORTING_CURRENCY ?= USD
CANONICAL_SIGNAL_API_OUTPUT ?= output/opportunity/canonical-signal-api-proof.json
SERVICE_CAPACITY_BASE_URL ?= http://localhost:8330
SERVICE_CAPACITY_PROFILE ?= test
SERVICE_CAPACITY_SCENARIO_ARGS ?= --scenario api
SERVICE_CAPACITY_REQUEST_COUNT ?= 10
SERVICE_CAPACITY_CONCURRENCY ?= 1
SERVICE_CAPACITY_OUTPUT ?= output/observability/service-capacity-baseline.json
SERVICE_LOAD_SOAK_PROOF ?= output/observability/service-load-soak-proof.json
POSTGRES_CAPACITY_PROOF_OUTPUT ?= output/observability/postgres-capacity-threshold-proof.json
POSTGRES_CAPACITY_EXPECTED_DATABASE ?=
POSTGRES_CAPACITY_MAX_TARGET_CONNECTIONS ?= 100
POSTGRES_CAPACITY_MAX_LOAD_CONNECTIONS ?= 100
POSTGRES_CAPACITY_CONFIRMATION ?=
SERVICE_CAPACITY_POSTGRES_THRESHOLD_PROOF_ARG ?=
SERVICE_CAPACITY_DEPENDENCY_RECOVERY_PROOF_ARG ?=
SERVICE_CAPACITY_LOAD_SOAK_PROOF_ARG ?=
SERVICE_CAPACITY_DOWNSTREAM_SEED_ARG ?=
SERVICE_CAPACITY_RESOURCE_BASELINE_ARG ?=
SERVICE_CAPACITY_COST_ATTRIBUTION_ARG ?=
DOWNSTREAM_CAPACITY_SEED_AS_OF_DATE ?= 2026-07-11
DOWNSTREAM_CAPACITY_SEEDED_AT_UTC ?= 2026-07-11T08:00:00Z
DOWNSTREAM_CAPACITY_SEED_CONFIRMATION ?=
DOWNSTREAM_CAPACITY_SEED_OUTPUT ?= output/observability/downstream-capacity-seed.json
SERVICE_RESOURCE_METRICS_URL ?= http://127.0.0.1:8330/metrics
SERVICE_RESOURCE_PROFILE ?= test
SERVICE_RESOURCE_SAMPLE_COUNT ?= 5
SERVICE_RESOURCE_SAMPLE_INTERVAL_SECONDS ?= 1
SERVICE_RESOURCE_OUTPUT ?= output/observability/service-resource-baseline.json

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
DOCKER_SOCKET_MOUNT := //var/run/docker.sock:/var/run/docker.sock
DOCKER_WORKDIR := //work
else
VENV_PYTHON := $(VENV_DIR)/bin/python
DOCKER_SOCKET_MOUNT := /var/run/docker.sock:/var/run/docker.sock
DOCKER_WORKDIR := /work
endif

install:
	python -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install --constraint requirements/runtime-resolved.lock.txt -e ".[dev]"

dependency-refresh:
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"
	$(VENV_PYTHON) -m scripts.refresh_runtime_dependency_locks
	$(VENV_PYTHON) scripts/license_compliance_gate.py --write-notice

lint:
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m ruff format --check .
	$(MAKE) ci-contract-gate
	$(MAKE) repository-hygiene-gate
	$(MAKE) test-client-lifecycle-gate
	$(MAKE) maintainability-gate
	$(MAKE) duplicate-implementation-gate
	$(MAKE) private-import-boundary-gate
	$(MAKE) foundation-structure-gate
	$(MAKE) documentation-contract-gate
	$(MAKE) quality-scorecard-gate
	$(MAKE) github-issue-closure-matrix-gate
	$(MAKE) monetary-float-guard
	$(MAKE) no-sensitive-content-guard
	$(MAKE) runtime-dependency-closure-gate
	$(MAKE) license-compliance-gate
	$(MAKE) source-observability-contract-gate
	$(MAKE) api-route-metadata-gate
	$(MAKE) api-problem-details-boundary-gate
	$(MAKE) api-idempotency-boundary-gate
	$(MAKE) api-camel-model-boundary-gate
	$(MAKE) api-signal-model-boundary-gate
	$(MAKE) api-temporal-validation-boundary-gate
	$(MAKE) openapi-problem-details-example-gate
	$(MAKE) caller-context-contract-gate
	$(MAKE) signal-api-contract-gate
	$(MAKE) trusted-tenant-context-gate
	$(MAKE) candidate-state-contract-gate
	$(MAKE) review-identity-contract-gate
	$(MAKE) conversion-outcome-contract-gate
	$(MAKE) source-temporal-contract-gate
	$(MAKE) review-queue-snapshot-contract-gate
	$(MAKE) operation-metric-contract-gate
	$(MAKE) service-slo-capacity-contract-gate
	$(MAKE) service-capacity-baseline-contract-gate
	$(MAKE) service-resource-baseline-contract-gate
	$(MAKE) supported-feature-promotion-contract-gate
	$(MAKE) ai-model-risk-ops-contract-gate
	$(MAKE) ai-model-risk-operations-proof-contract-gate
	$(MAKE) operator-workflows-ops-contract-gate
	$(MAKE) outbox-supportability-contract-gate
	$(MAKE) disaster-recovery-contract-gate
	$(MAKE) data-lifecycle-contract-gate
	$(MAKE) operator-workflows-operations-proof-contract-gate
	$(MAKE) ci-signal-evidence-contract-gate
	$(MAKE) implementation-truth-gate
	$(MAKE) data-mesh-contract-gate
	$(MAKE) mesh-policy-proof-contract-gate
	$(MAKE) opportunity-archetype-contract-gate
	$(MAKE) downstream-realization-contract-gate
	$(MAKE) downstream-route-contract-proof-gate
	$(MAKE) outbox-event-contract-gate
	$(MAKE) outbox-consumer-contract-gate
	$(MAKE) outbox-recovery-contract-gate
	$(MAKE) migration-contract-gate
	$(MAKE) migration-execution-gate
	$(MAKE) deployment-migration-contract-gate
	$(MAKE) durable-repository-proof-contract-gate
	$(MAKE) runtime-trust-telemetry-proof-contract-gate
	$(MAKE) ai-lineage-store-proof-contract-gate
	$(MAKE) ai-workflow-pack-registration-proof-contract-gate
	$(MAKE) ai-workflow-pack-runtime-execution-proof-contract-gate
	$(MAKE) lotus-ai-attestation-contract-proof-gate
	$(MAKE) ai-provider-retention-contract-gate
	$(MAKE) archive-lifecycle-posture-contract-gate
	$(MAKE) report-intake-route-source-contract-proof-gate
	$(MAKE) report-materialization-source-contract-proof-gate
	$(MAKE) workbench-read-path-source-contract-proof-gate
	$(MAKE) gateway-workbench-contract-proof-contract-gate
	$(MAKE) gateway-workbench-discovery-contract-proof-contract-gate
	$(MAKE) outbox-broker-source-contract-proof-gate
	$(MAKE) outbox-consumer-contract-proof-contract-gate
	$(MAKE) outbox-platform-mesh-event-source-contract-proof-gate
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
	$(MAKE) runtime-trust-telemetry-preview-check
	$(MAKE) supported-features-gate
	$(MAKE) endpoint-certification-gate

ci-contract-gate:
	$(VENV_PYTHON) scripts/ci_contract_gate.py

repository-hygiene-gate:
	$(VENV_PYTHON) scripts/repository_hygiene_gate.py

test-client-lifecycle-gate:
	$(VENV_PYTHON) scripts/testing/test_client_lifecycle_gate.py

maintainability-gate:
	$(VENV_PYTHON) scripts/maintainability_gate.py

duplicate-implementation-inventory:
	$(VENV_PYTHON) scripts/duplicate_implementation_inventory.py

duplicate-implementation-gate:
	$(VENV_PYTHON) scripts/duplicate_implementation_inventory.py --fail-on-duplicates

private-import-boundary-gate:
	$(VENV_PYTHON) scripts/private_import_boundary_gate.py

foundation-structure-gate:
	$(VENV_PYTHON) scripts/foundation_structure_gate.py

documentation-contract-gate:
	$(VENV_PYTHON) scripts/documentation_contract_gate.py

quality-scorecard-gate:
	$(VENV_PYTHON) scripts/quality_scorecard_gate.py

github-issue-closure-matrix-gate:
	$(VENV_PYTHON) scripts/github_issue_closure_matrix_gate.py

monetary-float-guard:
	$(VENV_PYTHON) scripts/check_monetary_float_usage.py

no-sensitive-content-guard:
	$(VENV_PYTHON) scripts/no_sensitive_content_guard.py

runtime-dependency-closure-gate:
	$(VENV_PYTHON) scripts/runtime_dependency_closure_gate.py

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

api-signal-model-boundary-gate:
	$(VENV_PYTHON) scripts/api_signal_model_boundary_gate.py

api-temporal-validation-boundary-gate:
	$(VENV_PYTHON) scripts/api_temporal_validation_boundary_gate.py

openapi-problem-details-example-gate:
	$(VENV_PYTHON) scripts/openapi_problem_details_example_gate.py

caller-context-contract-gate:
	$(VENV_PYTHON) scripts/caller_context_contract_gate.py

signal-api-contract-gate:
	$(VENV_PYTHON) scripts/signal_api_contract_gate.py

trusted-tenant-context-gate:
	$(VENV_PYTHON) scripts/trusted_tenant_context_gate.py

candidate-state-contract-gate:
	$(VENV_PYTHON) scripts/candidate_state_contract_gate.py

review-identity-contract-gate:
	$(VENV_PYTHON) scripts/review_identity_contract_gate.py

conversion-outcome-contract-gate:
	$(VENV_PYTHON) scripts/conversion_outcome_contract_gate.py

source-temporal-contract-gate:
	$(VENV_PYTHON) scripts/source_temporal_contract_gate.py

review-queue-snapshot-contract-gate:
	$(VENV_PYTHON) scripts/review_queue_snapshot_contract_gate.py

operation-metric-contract-gate:
	$(VENV_PYTHON) scripts/operation_metric_contract_gate.py

service-slo-capacity-contract-gate:
	$(VENV_PYTHON) scripts/service_slo_capacity_contract_gate.py

service-capacity-baseline-contract-gate:
	$(VENV_PYTHON) scripts/service_capacity_baseline_contract_gate.py

service-load-soak-proof-gate:
	$(VENV_PYTHON) scripts/service_load_soak_proof_gate.py --artifact "$(SERVICE_LOAD_SOAK_PROOF)"

service-resource-baseline-contract-gate:
	$(VENV_PYTHON) scripts/service_resource_baseline_contract_gate.py

service-resource-proof-gate:
	$(VENV_PYTHON) scripts/service_resource_proof_gate.py --artifact "$(SERVICE_RESOURCE_OUTPUT)"

service-capacity-workload:
	$(VENV_PYTHON) scripts/run_service_capacity_workload.py --base-url "$(SERVICE_CAPACITY_BASE_URL)" --environment-profile "$(SERVICE_CAPACITY_PROFILE)" $(SERVICE_CAPACITY_SCENARIO_ARGS) --request-count "$(SERVICE_CAPACITY_REQUEST_COUNT)" --concurrency "$(SERVICE_CAPACITY_CONCURRENCY)" --commit-sha "$(BUILD_GIT_COMMIT_SHA)" --branch "$(BUILD_GIT_BRANCH)" --run-id "$(BUILD_CI_RUN_ID)" $(SERVICE_CAPACITY_POSTGRES_THRESHOLD_PROOF_ARG) $(SERVICE_CAPACITY_DEPENDENCY_RECOVERY_PROOF_ARG) $(SERVICE_CAPACITY_LOAD_SOAK_PROOF_ARG) $(SERVICE_CAPACITY_DOWNSTREAM_SEED_ARG) $(SERVICE_CAPACITY_RESOURCE_BASELINE_ARG) $(SERVICE_CAPACITY_COST_ATTRIBUTION_ARG) --output "$(SERVICE_CAPACITY_OUTPUT)"

downstream-capacity-seed:
	$(VENV_PYTHON) scripts/seed_downstream_capacity_resource.py --base-url "$(SERVICE_CAPACITY_BASE_URL)" --as-of-date "$(DOWNSTREAM_CAPACITY_SEED_AS_OF_DATE)" --seeded-at-utc "$(DOWNSTREAM_CAPACITY_SEEDED_AT_UTC)" --commit-sha "$(BUILD_GIT_COMMIT_SHA)" --branch "$(BUILD_GIT_BRANCH)" --run-id "$(BUILD_CI_RUN_ID)" --confirmation "$(DOWNSTREAM_CAPACITY_SEED_CONFIRMATION)" --output "$(DOWNSTREAM_CAPACITY_SEED_OUTPUT)"

service-resource-baseline:
	$(VENV_PYTHON) scripts/run_service_resource_baseline.py --metrics-url "$(SERVICE_RESOURCE_METRICS_URL)" --environment-profile "$(SERVICE_RESOURCE_PROFILE)" --sample-count "$(SERVICE_RESOURCE_SAMPLE_COUNT)" --sample-interval-seconds "$(SERVICE_RESOURCE_SAMPLE_INTERVAL_SECONDS)" --commit-sha "$(BUILD_GIT_COMMIT_SHA)" --branch "$(BUILD_GIT_BRANCH)" --run-id "$(BUILD_CI_RUN_ID)" --output "$(SERVICE_RESOURCE_OUTPUT)"

postgres-capacity-threshold-proof:
	$(VENV_PYTHON) scripts/run_postgres_capacity_threshold_proof.py --environment-profile "$(SERVICE_CAPACITY_PROFILE)" --expected-database-name "$(POSTGRES_CAPACITY_EXPECTED_DATABASE)" --maximum-target-connections "$(POSTGRES_CAPACITY_MAX_TARGET_CONNECTIONS)" --maximum-load-connections "$(POSTGRES_CAPACITY_MAX_LOAD_CONNECTIONS)" --confirmation "$(POSTGRES_CAPACITY_CONFIRMATION)" --commit-sha "$(BUILD_GIT_COMMIT_SHA)" --branch "$(BUILD_GIT_BRANCH)" --run-id "$(BUILD_CI_RUN_ID)" --output "$(POSTGRES_CAPACITY_PROOF_OUTPUT)"

service-slo-rule-test:
	MSYS_NO_PATHCONV=1 docker run --rm -v "$(CURDIR):/work" --entrypoint promtool $(PROMETHEUS_IMAGE) test rules /work/monitoring/prometheus/tests/lotus-idea-service-slo.test.yml

supported-feature-promotion-contract-gate:
	$(VENV_PYTHON) scripts/supported_feature_promotion_contract_gate.py

ai-model-risk-ops-contract-gate:
	$(VENV_PYTHON) scripts/ai_model_risk_operations_contract_gate.py

ai-model-risk-operations-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_model_risk_operations/source_contract_proof_gate.py

operator-workflows-ops-contract-gate:
	$(VENV_PYTHON) scripts/operator_workflows_operations_contract_gate.py

outbox-supportability-contract-gate:
	$(VENV_PYTHON) scripts/outbox/supportability_contract_gate.py

disaster-recovery-contract-gate:
	$(VENV_PYTHON) scripts/disaster_recovery_contract_gate.py

data-lifecycle-contract-gate:
	$(VENV_PYTHON) scripts/data_lifecycle_contract_gate.py

scheduled-data-lifecycle-review:
	$(VENV_PYTHON) scripts/data_lifecycle/run_scheduled_review.py --execution-profile synthetic_disposable_postgres --output-path $(SCHEDULED_LIFECYCLE_REVIEW_EVIDENCE)

scheduled-data-lifecycle-seed:
	$(VENV_PYTHON) scripts/data_lifecycle/seed_scheduled_review_fixture.py --confirm-disposable-database

scheduled-data-lifecycle-review-proof-gate:
	$(VENV_PYTHON) scripts/data_lifecycle/scheduled_review_proof_gate.py --evidence $(SCHEDULED_LIFECYCLE_REVIEW_EVIDENCE)

postgres-disaster-recovery-seed:
	$(VENV_PYTHON) scripts/seed_postgres_disaster_recovery_fixture.py --confirm-disposable-database

postgres-disaster-recovery-drill:
	$(VENV_PYTHON) scripts/run_postgres_disaster_recovery_drill.py --backup-identifier $(DR_BACKUP_IDENTIFIER) --backup-source $(DR_BACKUP_SOURCE) --operator-id $(DR_OPERATOR_ID) --correlation-id $(DR_CORRELATION_ID) --output-path $(DR_RESTORE_EVIDENCE)

postgres-disaster-recovery-resume:
	$(VENV_PYTHON) scripts/validate_postgres_disaster_recovery_resume.py --operator-id $(DR_OPERATOR_ID) --correlation-id $(DR_CORRELATION_ID) --output-path $(DR_RESUME_EVIDENCE)

disaster-recovery-proof-gate:
	$(VENV_PYTHON) scripts/disaster_recovery_proof_contract_gate.py --restore-evidence $(DR_RESTORE_EVIDENCE) --resume-evidence $(DR_RESUME_EVIDENCE)

outbox-supportability-rule-test:
	MSYS_NO_PATHCONV=1 docker run --rm -v "$(CURDIR):/work" --entrypoint promtool $(PROMETHEUS_IMAGE) test rules /work/monitoring/prometheus/tests/lotus-idea-outbox-supportability.test.yml

operator-workflows-operations-proof-contract-gate:
	$(VENV_PYTHON) scripts/operator_workflows_operations/source_contract_proof_gate.py

ci-signal-evidence-contract-gate:
	$(VENV_PYTHON) scripts/ci_signal_evidence_contract_gate.py

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
	$(VENV_PYTHON) scripts/outbox/event_contract_gate.py

outbox-consumer-contract-gate:
	$(VENV_PYTHON) scripts/outbox/consumer_contract_gate.py

outbox-recovery-contract-gate:
	$(VENV_PYTHON) scripts/outbox/recovery_contract_gate.py

migration-contract-gate:
	$(VENV_PYTHON) scripts/migration_contract_gate.py

migration-execution-gate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply --dry-run
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback --dry-run

deployment-migration-contract-gate:
	$(VENV_PYTHON) scripts/deployment_migration_contract_gate.py

durable-repository-proof-contract-gate:
	$(VENV_PYTHON) scripts/persistence/durable_repository_proof_contract_gate.py

runtime-trust-telemetry-proof-contract-gate:
	$(VENV_PYTHON) scripts/runtime_trust_telemetry_proof_contract_gate.py

ai-lineage-store-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_lineage_store_proof_contract_gate.py

ai-lineage-store-ci-proof:
	$(VENV_PYTHON) scripts/generate_postgres_ci_execution_receipt.py --test-report "$(POSTGRES_RUNTIME_PROOF_JUNIT)" --repository "$(GITHUB_REPOSITORY)" --workflow-path "$(CI_WORKFLOW_PATH)" --workflow-name "$(GITHUB_WORKFLOW)" --job-name "$(CI_JOB_NAME)" --run-id "$(GITHUB_RUN_ID)" --run-attempt "$(GITHUB_RUN_ATTEMPT)" --source-commit-sha "$(GITHUB_SHA)" --source-ref "$(GITHUB_REF)" --conclusion success --completed-at-utc "$(BUILD_TIMESTAMP)" --artifact-sha256 "$(CI_ARTIFACT_SHA256)" --output "$(POSTGRES_CI_EXECUTION_RECEIPT_OUTPUT)"
	$(VENV_PYTHON) scripts/generate_ai_lineage_store_proof.py --generated-at-utc "$(BUILD_TIMESTAMP)" --ci-execution-receipt "$(POSTGRES_CI_EXECUTION_RECEIPT_OUTPUT)" --output "$(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)"

durable-repository-ci-proof:
	$(VENV_PYTHON) scripts/persistence/generate_ci_execution_receipt.py --test-report "$(POSTGRES_RUNTIME_PROOF_JUNIT)" --repository "$(GITHUB_REPOSITORY)" --workflow-path "$(CI_WORKFLOW_PATH)" --workflow-name "$(GITHUB_WORKFLOW)" --job-name "$(CI_JOB_NAME)" --run-id "$(GITHUB_RUN_ID)" --run-attempt "$(GITHUB_RUN_ATTEMPT)" --source-commit-sha "$(GITHUB_SHA)" --source-ref "$(GITHUB_REF)" --conclusion success --completed-at-utc "$(BUILD_TIMESTAMP)" --artifact-sha256 "$(CI_ARTIFACT_SHA256)" --output "$(DURABLE_REPOSITORY_CI_RECEIPT_OUTPUT)"
	$(VENV_PYTHON) scripts/persistence/generate_durable_repository_proof.py --generated-at-utc "$(BUILD_TIMESTAMP)" --source-commit-sha "$(GITHUB_SHA)" --ci-execution-receipt "$(DURABLE_REPOSITORY_CI_RECEIPT_OUTPUT)" --output "$(LOTUS_IDEA_DURABLE_REPOSITORY_PROOF_OUTPUT)"

ai-workflow-pack-registration-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_workflow_pack_registration/source_contract_proof_gate.py

ai-workflow-pack-runtime-execution-proof-contract-gate:
	$(VENV_PYTHON) scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py

lotus-ai-attestation-contract-proof-gate:
	$(VENV_PYTHON) scripts/lotus_ai_attestation_contract_proof_gate.py

ai-provider-retention-contract-gate:
	$(VENV_PYTHON) scripts/ai_provider_retention_contract_gate.py

archive-lifecycle-posture-contract-gate:
	$(VENV_PYTHON) scripts/archive_lifecycle_posture_contract_gate.py

lotus-ai-attestation-contract-proof:
	$(VENV_PYTHON) scripts/generate_lotus_ai_attestation_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --lotus-ai-root $(LOTUS_AI_ROOT) --output $(LOTUS_IDEA_LOTUS_AI_ATTESTATION_CONTRACT_PROOF_OUTPUT)

report-intake-route-source-contract-proof-gate:
	$(VENV_PYTHON) scripts/report/intake_route_source_contract_gate.py

report-materialization-source-contract-proof-gate:
	$(VENV_PYTHON) scripts/report/materialization_source_contract_gate.py

workbench-read-path-source-contract-proof-gate:
	$(VENV_PYTHON) scripts/workbench/read_path_source_contract_gate.py

gateway-workbench-contract-proof-contract-gate:
	$(VENV_PYTHON) scripts/workbench/contract_proof_gate.py

gateway-workbench-discovery-contract-proof-contract-gate:
	$(VENV_PYTHON) scripts/workbench/discovery_contract_proof_gate.py

outbox-broker-source-contract-proof-gate:
	$(VENV_PYTHON) scripts/outbox/broker/source_contract_proof_gate.py

outbox-consumer-contract-proof-contract-gate:
	$(VENV_PYTHON) scripts/outbox/consumer_contract_proof_contract_gate.py

outbox-platform-mesh-event-source-contract-proof-gate:
	$(VENV_PYTHON) scripts/outbox/platform_mesh/source_contract_proof_gate.py

platform-mesh-onboarding-proof-contract-gate:
	$(VENV_PYTHON) scripts/data_mesh/platform_catalog_source_contract_gate.py

source-ingestion-worker-check:
	$(VENV_PYTHON) scripts/source_ingestion_worker_contract_gate.py

source-ingestion-scheduled-worker-check:
	$(VENV_PYTHON) scripts/source_ingestion_scheduled_worker_contract_gate.py

source-ingestion-live-proof-contract-gate:
	$(VENV_PYTHON) scripts/source_ingestion_live_proof_contract_gate.py

canonical-opportunity-source-proofs:
	$(VENV_PYTHON) scripts/run_canonical_opportunity_source_proofs.py --portfolio-id "$(CANONICAL_OPPORTUNITY_PORTFOLIO_ID)" --as-of-date "$(CANONICAL_OPPORTUNITY_AS_OF_DATE)" --risk-base-url "$(CANONICAL_OPPORTUNITY_RISK_BASE_URL)" --performance-base-url "$(CANONICAL_OPPORTUNITY_PERFORMANCE_BASE_URL)" --period-name "$(CANONICAL_OPPORTUNITY_PERIOD_NAME)" --reporting-currency "$(CANONICAL_OPPORTUNITY_REPORTING_CURRENCY)" --timeout-seconds "$(CANONICAL_OPPORTUNITY_TIMEOUT_SECONDS)" --generated-at-utc "$(CANONICAL_OPPORTUNITY_GENERATED_AT_UTC)" --evaluated-at-utc "$(CANONICAL_OPPORTUNITY_EVALUATED_AT_UTC)" --correlation-id "$(CANONICAL_OPPORTUNITY_CORRELATION_ID)" --trace-id "$(CANONICAL_OPPORTUNITY_TRACE_ID)" --output-directory "$(CANONICAL_OPPORTUNITY_OUTPUT_DIRECTORY)"

canonical-signal-api-proof:
	$(VENV_PYTHON) scripts/run_canonical_signal_api_proof.py --idea-base-url "$(CANONICAL_SIGNAL_API_IDEA_BASE_URL)" --portfolio-id "$(CANONICAL_OPPORTUNITY_PORTFOLIO_ID)" --as-of-date "$(CANONICAL_OPPORTUNITY_AS_OF_DATE)" --period-name "$(CANONICAL_SIGNAL_API_PERIOD_NAME)" --reporting-currency "$(CANONICAL_SIGNAL_API_REPORTING_CURRENCY)" --generated-at-utc "$(CANONICAL_OPPORTUNITY_GENERATED_AT_UTC)" --evaluated-at-utc "$(CANONICAL_OPPORTUNITY_EVALUATED_AT_UTC)" --correlation-id "$(CANONICAL_OPPORTUNITY_CORRELATION_ID)" --trace-id "$(CANONICAL_OPPORTUNITY_TRACE_ID)" --output "$(CANONICAL_SIGNAL_API_OUTPUT)"

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
	$(VENV_PYTHON) scripts/generate_scheduled_source_ingestion_worker_proof.py --manifest docs/examples/source-ingestion/high-cash-worker-manifest.example.json --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --run-forever --output output/source-ingestion/scheduled-worker-proof.json
	$(VENV_PYTHON) scripts/persistence/generate_durable_repository_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --source-commit-sha "$(BUILD_GIT_COMMIT_SHA)" $(if $(LOTUS_IDEA_DURABLE_REPOSITORY_CI_RECEIPT),--ci-execution-receipt $(LOTUS_IDEA_DURABLE_REPOSITORY_CI_RECEIPT),) --output $(LOTUS_IDEA_DURABLE_REPOSITORY_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json
	$(VENV_PYTHON) scripts/generate_ai_lineage_store_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) $(if $(LOTUS_IDEA_AI_LINEAGE_STORE_CI_RECEIPT),--ci-execution-receipt $(LOTUS_IDEA_AI_LINEAGE_STORE_CI_RECEIPT),) --output $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/ai_model_risk_operations/generate_source_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/operator_workflows_operations/generate_source_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/ai_workflow_pack_registration/generate_source_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --lotus-ai-root $(LOTUS_AI_ROOT) --output $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_ai_workflow_pack_runtime_execution_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --lotus-ai-base-url $(LOTUS_AI_BASE_URL) --timeout-seconds $(LOTUS_IDEA_AI_RUNTIME_PROOF_TIMEOUT_SECONDS) --output $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT) --allow-runtime-unavailable
	$(VENV_PYTHON) scripts/workbench/generate_read_path_source_contract.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/workbench/read-path-source-contract-proof.json
	$(VENV_PYTHON) scripts/workbench/generate_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --workbench-read-path-source-contract-proof output/workbench/read-path-source-contract-proof.json --output $(LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/outbox/broker/generate_source_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output output/outbox/broker/source-contract-proof.json
	$(VENV_PYTHON) scripts/outbox/generate_consumer_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/outbox/platform_mesh/generate_source_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --output $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_advise_proposal_route_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --advise-root $(LOTUS_ADVISE_ROOT) --output $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_manage_action_route_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --manage-root $(LOTUS_MANAGE_ROOT) --output $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/report/generate_intake_route_source_contract.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --report-root $(LOTUS_REPORT_ROOT) --output $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/report/generate_materialization_source_contract.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --report-root $(LOTUS_REPORT_ROOT) --output $(LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_mesh_policy_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/data_mesh/generate_platform_catalog_source_contract.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --output $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/workbench/generate_discovery_contract_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --platform-root $(LOTUS_PLATFORM_ROOT) --platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT) --workbench-read-path-source-contract-proof output/workbench/read-path-source-contract-proof.json --gateway-workbench-contract-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT) --output $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT) --allow-missing-evidence
	$(VENV_PYTHON) scripts/generate_mandate_restriction_source_product_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_missing_risk_profile_source_product_proof.py --generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --output $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT)
	$(VENV_PYTHON) scripts/generate_implementation_proof_readiness.py --evaluated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC) --source-ingestion-manifest docs/examples/source-ingestion/high-cash-worker-manifest.example.json $(if $(IMPLEMENTATION_PROOF_OUTPUT),--output $(IMPLEMENTATION_PROOF_OUTPUT),) $(if $(LOTUS_CORE_BASE_URL),--core-base-url $(LOTUS_CORE_BASE_URL),) $(if $(LOTUS_CORE_QUERY_BASE_URL),--core-query-base-url $(LOTUS_CORE_QUERY_BASE_URL),) $(if $(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),--core-query-control-plane-base-url $(LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL),) $(if $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),--source-ingestion-live-proof $(LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF),) $(if $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF),--ai-lineage-store-proof $(LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF),--ai-model-risk-operations-proof $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF),--ai-model-risk-operations-proof $(LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF),--operator-workflows-operations-proof $(LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF),--operator-workflows-operations-proof $(LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),--ai-workflow-pack-registration-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),--ai-workflow-pack-registration-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),--ai-workflow-pack-runtime-execution-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF),--ai-workflow-pack-runtime-execution-proof $(LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),--advise-proposal-route-proof $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF),--advise-proposal-route-proof $(LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF),--manage-action-route-proof $(LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF),--report-intake-route-source-contract-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF),--report-intake-route-source-contract-proof $(LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF),--report-materialization-source-contract-proof $(LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF),--report-materialization-source-contract-proof $(LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MESH_POLICY_PROOF),--mesh-policy-proof $(LOTUS_IDEA_MESH_POLICY_PROOF),--mesh-policy-proof $(LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF),--platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF),--platform-mesh-onboarding-proof $(LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF),--outbox-consumer-contract-proof $(LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF),--outbox-consumer-contract-proof $(LOTUS_IDEA_OUTBOX_CONSUMER_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF),--outbox-platform-mesh-event-source-contract-proof $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF),--outbox-platform-mesh-event-source-contract-proof $(LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF),--gateway-workbench-contract-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF),--gateway-workbench-contract-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF),--gateway-workbench-discovery-contract-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF),--gateway-workbench-discovery-contract-proof $(LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF),--risk-concentration-live-proof $(LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF),) $(if $(LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF),--high-volatility-live-proof $(LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF),--risk-drawdown-live-proof $(LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF),) $(if $(LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF),--performance-underperformance-live-proof $(LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF),--missing-benchmark-performance-readiness-proof $(LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF),) $(if $(LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF),--core-benchmark-assignment-live-proof $(LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF),) $(if $(LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF),--core-portfolio-state-live-proof $(LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF),) $(if $(LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF),--bond-maturity-live-proof $(LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF),--missing-benchmark-live-proof $(LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF),) $(if $(LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF),--low-income-core-cashflow-live-proof $(LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF),--manage-mandate-live-proof $(LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF),--mandate-restriction-live-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF),) $(if $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF),--mandate-restriction-source-product-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF),--mandate-restriction-source-product-proof $(LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF),--missing-suitability-live-proof $(LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF),) $(if $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF),--missing-risk-profile-source-product-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF),--missing-risk-profile-source-product-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_OUTPUT)) $(if $(LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF),--missing-risk-profile-live-proof $(LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF),) --source-ingestion-scheduled-worker-proof output/source-ingestion/scheduled-worker-proof.json --durable-repository-proof output/persistence/durable-repository-proof.json --runtime-trust-telemetry-proof output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json --workbench-read-path-source-contract-proof output/workbench/read-path-source-contract-proof.json --outbox-broker-source-contract-proof output/outbox/broker/source-contract-proof.json

runtime-trust-telemetry-preview-check:
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_preview.py --generated-at-utc 2026-06-21T10:10:00Z

runtime-trust-telemetry-snapshot-check:
	$(VENV_PYTHON) scripts/generate_runtime_trust_telemetry_snapshot.py --generated-at-utc 2026-06-21T10:10:00Z

.PHONY: github-security-posture-check
github-security-posture-check:
	$(VENV_PYTHON) scripts/github_security_posture_check.py

migrate:
	$(VENV_PYTHON) scripts/run_migrations.py --direction apply

migrate-rollback:
	$(VENV_PYTHON) scripts/run_migrations.py --direction rollback

deployment-migrate:
	$(VENV_PYTHON) scripts/run_deployment_migrations.py --operation apply --environment-class $(DEPLOYMENT_ENVIRONMENT_CLASS) --evidence-output $(DEPLOYMENT_MIGRATION_EVIDENCE_OUTPUT)

supported-features-gate:
	$(VENV_PYTHON) scripts/supported_features_gate.py

endpoint-certification-gate:
	$(VENV_PYTHON) scripts/endpoint_certification_gate.py

postgres-integration-gate:
	$(VENV_PYTHON) -m pytest tests/integration/test_postgres_runtime_integration.py tests/integration/persistence/test_candidate_persistence_runtime.py tests/integration/outbox/test_postgres_recovery_runtime.py tests/integration/test_postgres_review_queue_runtime.py tests/integration/test_postgres_downstream_submission_runtime.py tests/integration/test_postgres_data_lifecycle_runtime.py --junitxml="$(POSTGRES_RUNTIME_PROOF_JUNIT)"

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
	$(VENV_PYTHON) scripts/coverage_gate.py --coverage-dir $(COVERAGE_DATA_DIR)

security-audit:
	$(VENV_PYTHON) -m pip_audit -r requirements/runtime-resolved.lock.txt -r requirements/ci-tooling.lock.txt

check: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test

ci: lint typecheck architecture-boundary-gate openapi-gate migration-contract-gate migration-execution-gate supported-features-gate endpoint-certification-gate test-integration test-e2e test-coverage security-audit

ci-release: ci implementation-proof-readiness-check runtime-trust-telemetry-snapshot-check postgres-integration-gate docker-build container-runtime-smoke container-image-scan release-sbom

docker-build:
	docker build --build-arg PYTHON_BASE_IMAGE=$(CONTAINER_BASE_IMAGE) --build-arg GIT_COMMIT_SHA=$(BUILD_GIT_COMMIT_SHA) --build-arg GIT_BRANCH=$(BUILD_GIT_BRANCH) --build-arg BUILD_TIMESTAMP=$(BUILD_TIMESTAMP) --build-arg REPO_URL=$(BUILD_REPO_URL) --build-arg CI_RUN_ID=$(BUILD_CI_RUN_ID) --build-arg IMAGE_BUILD_ID=$(BUILD_IMAGE_BUILD_ID) --build-arg SERVICE_VERSION=$(BUILD_SERVICE_VERSION) -t $(CONTAINER_IMAGE_NAME) .

container-runtime-smoke:
	python scripts/container_runtime_smoke.py \
		--image-name $(CONTAINER_IMAGE_NAME) \
		--container-name $(CONTAINER_SMOKE_NAME) \
		--host $(CONTAINER_SMOKE_HOST) \
		--host-port $(CONTAINER_SMOKE_HOST_PORT) \
		--container-port $(CONTAINER_SMOKE_CONTAINER_PORT) \
		--startup-timeout-seconds $(CONTAINER_SMOKE_TIMEOUT_SECONDS) \
		--probe-interval-seconds $(CONTAINER_SMOKE_PROBE_INTERVAL_SECONDS)

release-image-identity-contract-gate:
	$(VENV_PYTHON) scripts/release_image_identity_contract.py --manifest $(RELEASE_IMAGE_IDENTITY_MANIFEST) --labels $(RELEASE_IMAGE_IDENTITY_LABELS) --runtime-smoke $(RELEASE_IMAGE_IDENTITY_RUNTIME_SMOKE)

license-compliance-gate:
	$(VENV_PYTHON) scripts/license_compliance_gate.py

license-release-evidence-gate:
	$(VENV_PYTHON) scripts/license_compliance_gate.py --release-manifest $(LICENSE_RELEASE_MANIFEST) --sbom $(LICENSE_RELEASE_SBOM)

release-sbom:
	$(VENV_PYTHON) -m cyclonedx_py requirements requirements/runtime-resolved.lock.txt --pyproject pyproject.toml --output-reproducible --output-format JSON --output-file sbom.cdx.json
	$(VENV_PYTHON) scripts/finalize_release_sbom.py sbom.cdx.json

container-image-scan:
	mkdir -p $(dir $(CONTAINER_SCAN_OUTPUT))
	docker run --rm -v $(DOCKER_SOCKET_MOUNT) -v "$(CURDIR):/work" -w $(DOCKER_WORKDIR) $(TRIVY_IMAGE) image --severity $(CONTAINER_SCAN_SEVERITY) --exit-code 1 --ignore-unfixed --format json --output $(CONTAINER_SCAN_OUTPUT) $(CONTAINER_IMAGE_NAME)

clean:
	python scripts/clean_generated_artifacts.py
