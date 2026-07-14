from __future__ import annotations

from app.application.bond_maturity_live_proof import BOND_MATURITY_LIVE_PROOF_ENV
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
from app.application.core_benchmark_assignment_live_proof import (
    CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_ENV,
)
from app.application.core_portfolio_state_live_proof import (
    CORE_PORTFOLIO_STATE_LIVE_PROOF_ENV,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE_PROOF_ENV,
    MANAGE_ACTION_ROUTE_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV,
)
from app.application.workbench.contract_proof import (
    GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV,
)
from app.application.high_volatility_live_proof import HIGH_VOLATILITY_LIVE_PROOF_ENV
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
)
from app.application.manage_mandate_live_proof import MANAGE_MANDATE_LIVE_PROOF_ENV
from app.application.mandate_restriction_live_proof import MANDATE_RESTRICTION_LIVE_PROOF_ENV
from app.application.mandate_restriction_source_product_proof import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV,
)
from app.application.mesh_policy_proof import MESH_POLICY_PROOF_ENV
from app.application.missing_benchmark_live_proof import MISSING_BENCHMARK_LIVE_PROOF_ENV
from app.application.missing_benchmark_performance_readiness_proof import (
    MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_ENV,
)
from app.application.missing_suitability_live_proof import MISSING_SUITABILITY_LIVE_PROOF_ENV
from app.application.missing_risk_profile_live_proof import (
    MISSING_RISK_PROFILE_LIVE_PROOF_ENV,
)
from app.application.missing_risk_profile_source_product_proof import (
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
)
from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.outbox.consumer_contract_proof import (
    OUTBOX_CONSUMER_CONTRACT_PROOF_ENV,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    PLATFORM_CATALOG_SOURCE_CONTRACT_ENV,
)
from app.application.performance_underperformance_live_proof import (
    PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_ENV,
)
from app.application.report.intake_route_source_contract import (
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
)
from app.application.report.materialization_source_contract import (
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV,
)
from app.application.risk_concentration_live_proof import RISK_CONCENTRATION_LIVE_PROOF_ENV
from app.application.risk_drawdown_live_proof import RISK_DRAWDOWN_LIVE_PROOF_ENV
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
)

PROOF_ARTIFACT_ARGS: tuple[tuple[str, str, str], ...] = (
    (
        "--durable-repository-proof",
        DURABLE_REPOSITORY_PROOF_ENV,
        "Optional durable PostgreSQL repository proof artifact path.",
    ),
    (
        "--runtime-trust-telemetry-proof",
        RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
        "Optional runtime trust telemetry candidate snapshot proof artifact path.",
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
        "--advise-proposal-route-proof",
        ADVISE_PROPOSAL_ROUTE_PROOF_ENV,
        "Optional lotus-advise idea proposal route proof artifact path.",
    ),
    (
        "--manage-action-route-proof",
        MANAGE_ACTION_ROUTE_PROOF_ENV,
        "Optional lotus-manage idea action route proof artifact path.",
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
        "--mesh-policy-proof",
        MESH_POLICY_PROOF_ENV,
        "Optional repo-owned mesh SLO, access, and evidence policy proof artifact path.",
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
        "--outbox-consumer-contract-proof",
        OUTBOX_CONSUMER_CONTRACT_PROOF_ENV,
        "Optional bounded outbox downstream consumer contract proof artifact path.",
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
        RISK_CONCENTRATION_LIVE_PROOF_ENV,
        "Optional lotus-risk concentration live source proof artifact path.",
    ),
    (
        "--high-volatility-live-proof",
        HIGH_VOLATILITY_LIVE_PROOF_ENV,
        "Optional lotus-risk high-volatility live source proof artifact path.",
    ),
    (
        "--risk-drawdown-live-proof",
        RISK_DRAWDOWN_LIVE_PROOF_ENV,
        "Optional lotus-risk drawdown live source proof artifact path.",
    ),
    (
        "--performance-underperformance-live-proof",
        PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_ENV,
        "Optional lotus-performance underperformance live source proof artifact path.",
    ),
    (
        "--core-benchmark-assignment-live-proof",
        CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_ENV,
        "Optional lotus-core benchmark assignment live source proof artifact path.",
    ),
    (
        "--core-portfolio-state-live-proof",
        CORE_PORTFOLIO_STATE_LIVE_PROOF_ENV,
        "Optional lotus-core portfolio-state live source proof artifact path.",
    ),
    (
        "--bond-maturity-live-proof",
        BOND_MATURITY_LIVE_PROOF_ENV,
        "Optional lotus-core maturity-summary live source proof artifact path.",
    ),
    (
        "--low-income-core-cashflow-live-proof",
        LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
        "Optional lotus-core cashflow live source proof artifact path for low-income review.",
    ),
    (
        "--manage-mandate-live-proof",
        MANAGE_MANDATE_LIVE_PROOF_ENV,
        "Optional lotus-manage portfolio-scoped mandate live source proof artifact path.",
    ),
    (
        "--mandate-restriction-live-proof",
        MANDATE_RESTRICTION_LIVE_PROOF_ENV,
        "Optional lotus-advise mandate/restriction live source proof artifact path.",
    ),
    (
        "--mandate-restriction-source-product-proof",
        MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV,
        "Optional lotus-advise typed mandate/restriction source-product proof artifact path.",
    ),
    (
        "--missing-suitability-live-proof",
        MISSING_SUITABILITY_LIVE_PROOF_ENV,
        "Optional lotus-advise missing suitability live source proof artifact path.",
    ),
    (
        "--missing-risk-profile-live-proof",
        MISSING_RISK_PROFILE_LIVE_PROOF_ENV,
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
        MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_ENV,
        "Optional lotus-performance benchmark-readiness proof artifact path for missing-benchmark review.",
    ),
)
