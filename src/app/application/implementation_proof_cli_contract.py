from __future__ import annotations

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_model_risk_operations_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
)
from app.application.ai_workflow_pack_registration_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.core_benchmark_assignment_live_proof import (
    CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_ENV,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE_PROOF_ENV,
    MANAGE_ACTION_ROUTE_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.gateway_workbench_discovery_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV,
)
from app.application.gateway_workbench_operational_proof import (
    GATEWAY_WORKBENCH_OPERATIONAL_PROOF_ENV,
)
from app.application.high_volatility_live_proof import HIGH_VOLATILITY_LIVE_PROOF_ENV
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV,
)
from app.application.manage_mandate_live_proof import MANAGE_MANDATE_LIVE_PROOF_ENV
from app.application.mesh_policy_proof import MESH_POLICY_PROOF_ENV
from app.application.missing_suitability_live_proof import MISSING_SUITABILITY_LIVE_PROOF_ENV
from app.application.outbox_broker_proof import OUTBOX_BROKER_PROOF_ENV
from app.application.outbox_consumer_runtime_proof import (
    OUTBOX_CONSUMER_RUNTIME_PROOF_ENV,
)
from app.application.outbox_platform_mesh_event_publication_proof import (
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
)
from app.application.platform_mesh_onboarding_proof import (
    PLATFORM_MESH_ONBOARDING_PROOF_ENV,
)
from app.application.performance_underperformance_live_proof import (
    PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_ENV,
)
from app.application.report_intake_route_proof import REPORT_INTAKE_ROUTE_PROOF_ENV
from app.application.report_materialization_proof import REPORT_MATERIALIZATION_PROOF_ENV
from app.application.risk_concentration_live_proof import RISK_CONCENTRATION_LIVE_PROOF_ENV
from app.application.risk_drawdown_live_proof import RISK_DRAWDOWN_LIVE_PROOF_ENV
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.application.workbench_read_path_proof import WORKBENCH_READ_PATH_PROOF_ENV

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
        "--ai-workflow-pack-registration-proof",
        AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
        "Optional lotus-ai idea workflow-pack registration proof artifact path.",
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
        "--report-intake-route-proof",
        REPORT_INTAKE_ROUTE_PROOF_ENV,
        "Optional lotus-report idea evidence intake route proof artifact path.",
    ),
    (
        "--report-materialization-proof",
        REPORT_MATERIALIZATION_PROOF_ENV,
        "Optional lotus-report idea evidence materialization proof artifact path.",
    ),
    (
        "--mesh-policy-proof",
        MESH_POLICY_PROOF_ENV,
        "Optional repo-owned mesh SLO, access, and evidence policy proof artifact path.",
    ),
    (
        "--workbench-read-path-proof",
        WORKBENCH_READ_PATH_PROOF_ENV,
        "Optional bounded Workbench read-path proof artifact path.",
    ),
    (
        "--gateway-workbench-operational-proof",
        GATEWAY_WORKBENCH_OPERATIONAL_PROOF_ENV,
        "Optional bounded Gateway/Workbench operational proof artifact path.",
    ),
    (
        "--gateway-workbench-discovery-proof",
        GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV,
        "Optional bounded Gateway/Workbench discovery proof artifact path.",
    ),
    (
        "--outbox-broker-proof",
        OUTBOX_BROKER_PROOF_ENV,
        "Optional bounded outbox broker runtime proof artifact path.",
    ),
    (
        "--outbox-consumer-runtime-proof",
        OUTBOX_CONSUMER_RUNTIME_PROOF_ENV,
        "Optional bounded outbox downstream consumer runtime proof artifact path.",
    ),
    (
        "--outbox-platform-mesh-event-publication-proof",
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV,
        "Optional bounded outbox platform mesh event publication proof artifact path.",
    ),
    (
        "--platform-mesh-onboarding-proof",
        PLATFORM_MESH_ONBOARDING_PROOF_ENV,
        "Optional platform source-manifest and catalog onboarding proof artifact path.",
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
        "--missing-suitability-live-proof",
        MISSING_SUITABILITY_LIVE_PROOF_ENV,
        "Optional lotus-advise missing suitability live source proof artifact path.",
    ),
)
