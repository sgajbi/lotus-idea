from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.proof_evidence import EvidenceClass


class ProofArtifactEffect(StrEnum):
    BLOCKER_CLEARING = "blocker_clearing"
    SUPPORTING_EVIDENCE = "supporting_evidence"


class ProofArtifactClassificationStatus(StrEnum):
    CLASSIFIED = "classified"
    PENDING_CORRECTION = "pending_correction"


@dataclass(frozen=True)
class ImplementationProofArtifactSpec:
    cli_flag: str
    payload_argument: str | None
    ref_argument: str
    evidence_class: EvidenceClass | None
    effect: ProofArtifactEffect
    inventory_label: str
    tracking_issue: int
    status: ProofArtifactClassificationStatus = ProofArtifactClassificationStatus.CLASSIFIED

    def __post_init__(self) -> None:
        if self.status is ProofArtifactClassificationStatus.CLASSIFIED:
            if self.evidence_class is None:
                raise ValueError("classified proof artifacts require an evidence class")
        elif self.evidence_class is not None:
            raise ValueError("pending proof artifacts must not declare a completed evidence class")


def proof_artifact_spec_for_payload_argument(
    payload_argument: str,
) -> ImplementationProofArtifactSpec | None:
    matches = tuple(
        spec
        for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS
        if spec.payload_argument == payload_argument
    )
    return matches[0] if len(matches) == 1 else None


def proof_artifact_spec_for_ref_argument(
    ref_argument: str,
) -> ImplementationProofArtifactSpec | None:
    matches = tuple(
        spec for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS if spec.ref_argument == ref_argument
    )
    return matches[0] if len(matches) == 1 else None


def proof_artifact_effect_matches_payload(
    payload_argument: str,
    expected_effect: ProofArtifactEffect,
) -> bool:
    return _proof_artifact_effect_matches(
        proof_artifact_spec_for_payload_argument(payload_argument),
        expected_effect,
    )


def proof_artifact_effect_matches_ref(
    ref_argument: str,
    expected_effect: ProofArtifactEffect,
) -> bool:
    return _proof_artifact_effect_matches(
        proof_artifact_spec_for_ref_argument(ref_argument),
        expected_effect,
    )


def _proof_artifact_effect_matches(
    spec: ImplementationProofArtifactSpec | None,
    expected_effect: ProofArtifactEffect,
) -> bool:
    return bool(
        spec
        and spec.status is ProofArtifactClassificationStatus.CLASSIFIED
        and spec.effect is expected_effect
    )


def _classified(
    cli_flag: str,
    payload_argument: str,
    evidence_class: EvidenceClass,
    effect: ProofArtifactEffect,
    inventory_label: str,
    tracking_issue: int,
) -> ImplementationProofArtifactSpec:
    return ImplementationProofArtifactSpec(
        cli_flag=cli_flag,
        payload_argument=payload_argument,
        ref_argument=f"{payload_argument}_ref",
        evidence_class=evidence_class,
        effect=effect,
        inventory_label=inventory_label,
        tracking_issue=tracking_issue,
    )


SUPPORTING = ProofArtifactEffect.SUPPORTING_EVIDENCE
CLEARING = ProofArtifactEffect.BLOCKER_CLEARING

IMPLEMENTATION_PROOF_ARTIFACT_SPECS = (
    _classified(
        "--source-ingestion-runtime-execution",
        "source_ingestion_runtime_execution",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Source-ingestion runtime execution",
        456,
    ),
    ImplementationProofArtifactSpec(
        cli_flag="--source-ingestion-scheduled-worker-source-contract",
        payload_argument=None,
        ref_argument="source_ingestion_scheduled_worker_source_contract_ref",
        evidence_class=EvidenceClass.SOURCE_CONTRACT,
        effect=SUPPORTING,
        inventory_label="Scheduled source-ingestion worker source contract",
        tracking_issue=508,
    ),
    ImplementationProofArtifactSpec(
        cli_flag="--source-ingestion-scheduled-worker-deployment-evidence",
        payload_argument=None,
        ref_argument="source_ingestion_scheduled_worker_deployment_evidence_ref",
        evidence_class=EvidenceClass.DEPLOYMENT,
        effect=CLEARING,
        inventory_label="Scheduled source-ingestion worker deployment evidence",
        tracking_issue=508,
    ),
    _classified(
        "--durable-repository-proof",
        "durable_repository_proof",
        EvidenceClass.CI_EXECUTION,
        CLEARING,
        "Durable repository",
        401,
    ),
    _classified(
        "--runtime-trust-telemetry-test-execution",
        "runtime_trust_telemetry_test_execution",
        EvidenceClass.TEST_EXECUTION,
        SUPPORTING,
        "Runtime trust telemetry test execution",
        452,
    ),
    _classified(
        "--ai-lineage-store-proof",
        "ai_lineage_store_proof",
        EvidenceClass.CI_EXECUTION,
        CLEARING,
        "AI lineage store",
        396,
    ),
    _classified(
        "--ai-model-risk-operations-proof",
        "ai_model_risk_operations_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "AI model-risk dashboard and alert source",
        411,
    ),
    _classified(
        "--operator-workflows-operations-proof",
        "operator_workflows_operations_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Operator-workflows dashboard and alert source",
        412,
    ),
    _classified(
        "--ai-workflow-pack-registration-proof",
        "ai_workflow_pack_registration_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "AI workflow-pack registration source contract",
        428,
    ),
    _classified(
        "--ai-workflow-pack-runtime-execution-proof",
        "ai_workflow_pack_runtime_execution_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "AI workflow execution",
        392,
    ),
    _classified(
        "--advise-proposal-route-source-contract-proof",
        "advise_proposal_route_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Advise and Manage route source contracts",
        449,
    ),
    _classified(
        "--advise-intake-runtime-execution-proof",
        "advise_intake_runtime_execution_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Advise idea-intake runtime execution",
        688,
    ),
    _classified(
        "--manage-action-route-source-contract-proof",
        "manage_action_route_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Advise and Manage route source contracts",
        449,
    ),
    _classified(
        "--manage-intake-runtime-execution-proof",
        "manage_intake_runtime_execution_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Manage idea action-intake runtime execution",
        689,
    ),
    _classified(
        "--report-intake-route-source-contract-proof",
        "report_intake_route_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Report intake route source contract",
        437,
    ),
    _classified(
        "--report-materialization-source-contract-proof",
        "report_materialization_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Report materialization source contract",
        438,
    ),
    _classified(
        "--report-materialization-runtime-execution-proof",
        "report_materialization_runtime_execution_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Report materialization runtime execution",
        690,
    ),
    _classified(
        "--mesh-policy-source-contract-proof",
        "mesh_policy_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Mesh policy source contract",
        444,
    ),
    _classified(
        "--workbench-read-path-source-contract-proof",
        "workbench_read_path_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Workbench read-path source contract",
        434,
    ),
    _classified(
        "--gateway-workbench-contract-proof",
        "gateway_workbench_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Gateway/Workbench contract",
        406,
    ),
    _classified(
        "--gateway-workbench-discovery-contract-proof",
        "gateway_workbench_discovery_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Gateway/Workbench discovery contract",
        408,
    ),
    _classified(
        "--outbox-broker-source-contract-proof",
        "outbox_broker_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Outbox broker source contract",
        419,
    ),
    _classified(
        "--outbox-broker-runtime-execution-proof",
        "outbox_broker_runtime_execution_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Outbox broker runtime execution",
        694,
    ),
    _classified(
        "--outbox-consumer-contract-proof",
        "outbox_consumer_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Outbox consumer source contract",
        404,
    ),
    _classified(
        "--outbox-platform-mesh-event-source-contract-proof",
        "outbox_platform_mesh_event_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        SUPPORTING,
        "Platform-mesh event source contract",
        422,
    ),
    _classified(
        "--platform-catalog-source-contract-proof",
        "platform_catalog_source_contract_proof",
        EvidenceClass.SOURCE_CONTRACT,
        CLEARING,
        "Platform catalog source contract",
        443,
    ),
    _classified(
        "--risk-concentration-live-proof",
        "risk_concentration_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Risk concentration runtime execution",
        462,
    ),
    _classified(
        "--high-volatility-live-proof",
        "high_volatility_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "High-volatility runtime execution",
        465,
    ),
    _classified(
        "--risk-drawdown-live-proof",
        "risk_drawdown_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Risk drawdown runtime execution",
        466,
    ),
    _classified(
        "--performance-underperformance-live-proof",
        "performance_underperformance_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Performance underperformance runtime execution",
        469,
    ),
    _classified(
        "--core-benchmark-assignment-live-proof",
        "core_benchmark_assignment_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Core benchmark-assignment runtime execution",
        476,
    ),
    _classified(
        "--core-portfolio-state-live-proof",
        "core_portfolio_state_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Core portfolio-state runtime execution",
        479,
    ),
    _classified(
        "--bond-maturity-live-proof",
        "bond_maturity_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Core bond-maturity runtime execution",
        482,
    ),
    _classified(
        "--low-income-core-cashflow-live-proof",
        "low_income_core_cashflow_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Core low-income cashflow runtime execution",
        485,
    ),
    _classified(
        "--manage-mandate-live-proof",
        "manage_mandate_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Manage mandate-health runtime execution",
        488,
    ),
    _classified(
        "--mandate-restriction-live-proof",
        "mandate_restriction_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Advise mandate/restriction runtime execution",
        492,
    ),
    _classified(
        "--mandate-restriction-source-product-proof",
        "mandate_restriction_source_product_proof",
        EvidenceClass.SOURCE_CONTRACT,
        CLEARING,
        "Advise mandate/restriction source-product contract",
        507,
    ),
    _classified(
        "--missing-suitability-live-proof",
        "missing_suitability_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Advise missing-suitability runtime execution",
        495,
    ),
    _classified(
        "--missing-risk-profile-live-proof",
        "missing_risk_profile_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Advise missing-risk-profile runtime execution",
        496,
    ),
    _classified(
        "--missing-risk-profile-source-product-proof",
        "missing_risk_profile_source_product_proof",
        EvidenceClass.SOURCE_CONTRACT,
        CLEARING,
        "Advise missing-risk-profile source-product contract",
        507,
    ),
    _classified(
        "--missing-benchmark-live-proof",
        "missing_benchmark_live_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Core missing-benchmark runtime execution",
        499,
    ),
    _classified(
        "--missing-benchmark-performance-readiness-proof",
        "missing_benchmark_performance_readiness_proof",
        EvidenceClass.RUNTIME_EXECUTION,
        CLEARING,
        "Performance benchmark-readiness runtime execution",
        500,
    ),
)
