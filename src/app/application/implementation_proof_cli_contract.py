from __future__ import annotations

from app.application.bond_maturity_runtime_evidence import BOND_MATURITY_RUNTIME_EXECUTION_ENV
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
from app.application.core_benchmark_assignment_runtime_evidence import (
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_ENV,
)
from app.application.core_portfolio_state_runtime_evidence import (
    CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_ENV,
)
from app.application.downstream_realization.route_source_contract import (
    ADVISE_ROUTE_SOURCE_CONTRACT_ENV,
    MANAGE_ROUTE_SOURCE_CONTRACT_ENV,
)
from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.high_volatility_runtime_evidence import HIGH_VOLATILITY_RUNTIME_EXECUTION_ENV
from app.application.low_income_cashflow_runtime_evidence import (
    LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
)
from app.application.manage_mandate_runtime_evidence import MANAGE_MANDATE_RUNTIME_EXECUTION_ENV
from app.application.advise_mandate_restriction_runtime_evidence import (
    ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_ENV,
)
from app.application.advise_source_product_evidence import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV,
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV,
)
from app.application.data_mesh.mesh_policy_source_contract import (
    MESH_POLICY_SOURCE_CONTRACT_ENV,
)
from app.application.core_missing_benchmark_runtime_evidence import (
    CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_ENV as MISSING_BENCHMARK_LIVE_PROOF_ENV,
)
from app.application.performance_benchmark_readiness_runtime_evidence import (
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_ENV,
)
from app.application.advise_missing_suitability_runtime_evidence import (
    ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_ENV,
)
from app.application.advise_missing_risk_profile_runtime_evidence import (
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_ENV,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.broker.runtime_execution import (
    OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
)
from app.application.outbox.consumer_contract_proof import (
    OUTBOX_CONSUMER_CONTRACT_PROOF_ENV,
)
from app.application.outbox.consumer_runtime import (
    OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
)
from app.application.performance_underperformance_runtime_evidence import (
    PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_ENV,
)
from app.application.report.intake_route_source_contract import (
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.report.materialization_source_contract import (
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV,
)
from app.application.report.materialization_runtime_execution import (
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
)
from app.application.risk_concentration_runtime_evidence import (
    RISK_CONCENTRATION_RUNTIME_EXECUTION_ENV,
)
from app.application.risk_drawdown_runtime_evidence import RISK_DRAWDOWN_RUNTIME_EXECUTION_ENV
from app.application.runtime_trust_telemetry.test_execution_contract import (
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)

PROOF_ARTIFACT_ARGS: tuple[tuple[str, str, str], ...] = (
    (
        "--source-ingestion-scheduled-worker-source-contract",
        SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
        "Optional scheduled source-ingestion worker source-contract artifact path.",
    ),
    (
        "--source-ingestion-scheduled-worker-deployment-evidence",
        SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
        "Optional scheduled source-ingestion worker deployment-evidence artifact path.",
    ),
    (
        "--durable-repository-proof",
        DURABLE_REPOSITORY_PROOF_ENV,
        "Optional durable PostgreSQL repository proof artifact path.",
    ),
    (
        "--runtime-trust-telemetry-test-execution",
        RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
        "Optional deterministic in-memory runtime trust telemetry test-execution artifact path.",
    ),
    (
        "--ai-lineage-store-proof",
        AI_LINEAGE_STORE_PROOF_ENV,
        "Optional durable AI explanation lineage store proof artifact path.",
    ),
    (
        "--ai-model-risk-operations-proof",
        AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
        "Optional AI model-risk operations dashboard and alert proof artifact path.",
    ),
    (
        "--operator-workflows-operations-proof",
        OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
        "Optional non-AI operator workflow operations dashboard and alert proof artifact path.",
    ),
    (
        "--ai-workflow-pack-registration-proof",
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        "Optional Lotus AI idea workflow-pack registration source-contract proof path.",
    ),
    (
        "--ai-workflow-pack-runtime-execution-proof",
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
        "Optional lotus-ai idea workflow-pack runtime execution proof artifact path.",
    ),
    (
        "--advise-proposal-route-source-contract-proof",
        ADVISE_ROUTE_SOURCE_CONTRACT_ENV,
        "Optional digest-bound lotus-advise route source-contract artifact path.",
    ),
    (
        "--advise-intake-runtime-execution-proof",
        ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
        "Optional lotus-advise idea-intake runtime execution proof artifact path.",
    ),
    (
        "--manage-action-route-source-contract-proof",
        MANAGE_ROUTE_SOURCE_CONTRACT_ENV,
        "Optional digest-bound lotus-manage route source-contract artifact path.",
    ),
    (
        "--manage-intake-runtime-execution-proof",
        MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
        "Optional lotus-manage idea action-intake runtime execution proof artifact path.",
    ),
    (
        "--report-intake-route-source-contract-proof",
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
        "Optional lotus-report idea evidence intake route proof artifact path.",
    ),
    (
        "--report-materialization-source-contract-proof",
        REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV,
        "Optional lotus-report idea evidence materialization source-contract artifact path.",
    ),
    (
        "--report-materialization-runtime-execution-proof",
        REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
        "Optional lotus-report idea evidence materialization runtime execution artifact path.",
    ),
    (
        "--mesh-policy-source-contract-proof",
        MESH_POLICY_SOURCE_CONTRACT_ENV,
        "Optional digest-bound repo-owned mesh policy source-contract artifact path.",
    ),
    (
        "--workbench-read-path-source-contract-proof",
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
        "Optional Workbench read-path source-contract proof artifact path.",
    ),
    (
        "--gateway-workbench-contract-proof",
        GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
        "Optional bounded Gateway/Workbench contract proof artifact path.",
    ),
    (
        "--gateway-workbench-discovery-contract-proof",
        GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
        "Optional bounded Gateway/Workbench discovery contract proof artifact path.",
    ),
    (
        "--outbox-broker-source-contract-proof",
        OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
        "Optional outbox broker source-contract proof artifact path.",
    ),
    (
        "--outbox-broker-runtime-execution-proof",
        OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
        "Optional outbox broker runtime publication proof artifact path.",
    ),
    (
        "--outbox-consumer-contract-proof",
        OUTBOX_CONSUMER_CONTRACT_PROOF_ENV,
        "Optional bounded outbox downstream consumer contract proof artifact path.",
    ),
    (
        "--outbox-consumer-runtime-execution-proof",
        OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV,
        "Optional outbox downstream domain-consumer runtime execution proof artifact path.",
    ),
    (
        "--outbox-platform-mesh-event-source-contract-proof",
        OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
        "Optional bounded outbox platform-mesh event source-contract proof artifact path.",
    ),
    (
        "--platform-catalog-source-contract-proof",
        PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
        "Optional digest-bound platform catalog source-contract artifact path.",
    ),
    (
        "--risk-concentration-live-proof",
        RISK_CONCENTRATION_RUNTIME_EXECUTION_ENV,
        "Optional lotus-risk concentration live source proof artifact path.",
    ),
    (
        "--high-volatility-live-proof",
        HIGH_VOLATILITY_RUNTIME_EXECUTION_ENV,
        "Optional lotus-risk high-volatility live source proof artifact path.",
    ),
    (
        "--risk-drawdown-live-proof",
        RISK_DRAWDOWN_RUNTIME_EXECUTION_ENV,
        "Optional receipt-bound lotus-risk drawdown runtime execution artifact path.",
    ),
    (
        "--performance-underperformance-live-proof",
        PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_ENV,
        "Optional lotus-performance underperformance live source proof artifact path.",
    ),
    (
        "--core-benchmark-assignment-live-proof",
        CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_ENV,
        "Optional receipt-bound Lotus Core benchmark-assignment runtime evidence path.",
    ),
    (
        "--core-portfolio-state-live-proof",
        CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_ENV,
        "Optional receipt-bound Lotus Core portfolio-state runtime evidence path.",
    ),
    (
        "--bond-maturity-live-proof",
        BOND_MATURITY_RUNTIME_EXECUTION_ENV,
        "Optional lotus-core maturity-summary live source proof artifact path.",
    ),
    (
        "--low-income-core-cashflow-live-proof",
        LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV,
        "Optional lotus-core cashflow live source proof artifact path for low-income review.",
    ),
    (
        "--manage-mandate-live-proof",
        MANAGE_MANDATE_RUNTIME_EXECUTION_ENV,
        "Optional lotus-manage portfolio-scoped mandate live source proof artifact path.",
    ),
    (
        "--mandate-restriction-live-proof",
        ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_ENV,
        "Optional lotus-advise mandate/restriction live source proof artifact path.",
    ),
    (
        "--mandate-restriction-source-product-proof",
        MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV,
        "Optional lotus-advise typed mandate/restriction source-product proof artifact path.",
    ),
    (
        "--missing-suitability-live-proof",
        ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_ENV,
        "Optional lotus-advise missing suitability live source proof artifact path.",
    ),
    (
        "--missing-risk-profile-live-proof",
        ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_ENV,
        "Optional lotus-advise missing risk-profile live source proof artifact path.",
    ),
    (
        "--missing-risk-profile-source-product-proof",
        MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV,
        "Optional lotus-advise typed risk-profile source-product proof artifact path.",
    ),
    (
        "--missing-benchmark-live-proof",
        MISSING_BENCHMARK_LIVE_PROOF_ENV,
        "Optional lotus-core missing-benchmark live source proof artifact path.",
    ),
    (
        "--missing-benchmark-performance-readiness-proof",
        PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_ENV,
        "Optional lotus-performance benchmark-readiness proof artifact path for missing-benchmark review.",
    ),
)
