from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping, cast

from app.application.ai_governance import (
    AIExplanationReadinessSnapshot,
    build_ai_explanation_readiness_snapshot,
)
from app.application.data_mesh_readiness import (
    DataMeshReadinessSnapshot,
    REPOSITORY_ROOT,
    build_data_mesh_readiness_snapshot,
)
from app.application.downstream_realization_readiness import (
    DownstreamRealizationReadinessSnapshot,
    build_downstream_realization_readiness_snapshot,
)
from app.application.implementation_proof_consumption import (
    apply_available_proofs_from_scope,
    source_ingestion_runtime_execution_is_registered_and_current,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_capability_updates import build_capability_readiness
from app.application.opportunity_archetype_contracts import OPPORTUNITY_ARCHETYPE_CONTRACT_PATH
from app.application.opportunity_archetype_readiness import (
    build_opportunity_archetype_scenario_readiness,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED,
    REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS,
    REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS,
)
from app.application.outbox.readiness import (
    OutboxDeliveryReadinessSnapshot,
    build_outbox_delivery_readiness_snapshot,
)
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    ReviewQueueReadinessSnapshot,
    build_review_queue_readiness_snapshot,
)
from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryPreview,
    build_runtime_trust_telemetry_preview,
)
from app.application.source_ingestion_readiness import (
    SourceIngestionReadinessSnapshot,
    build_source_ingestion_readiness_snapshot,
)
from app.application.supported_feature_promotion import (
    SupportedFeaturePromotionEvaluation,
    evaluate_supported_feature_promotion,
)
from app.ports.idea_repository import OutboxDeliveryRepository

SUPPORTED_FEATURES_PATH = Path("supported-features/supported-features.json")


def build_implementation_proof_readiness_snapshot(
    *,
    evaluated_at_utc: datetime,
    repository: OutboxDeliveryRepository,
    durable_storage_backed: bool,
    source_ingestion_runtime_execution: Mapping[str, object] | None = None,
    source_ingestion_runtime_execution_ref: str | None = None,
    source_ingestion_scheduled_worker_source_contract_ref: str | None = None,
    source_ingestion_scheduled_worker_deployment_evidence_ref: str | None = None,
    durable_repository_proof: Mapping[str, object] | None = None,
    durable_repository_proof_ref: str | None = None,
    runtime_trust_telemetry_test_execution: Mapping[str, object] | None = None,
    runtime_trust_telemetry_test_execution_ref: str | None = None,
    ai_lineage_store_proof: Mapping[str, object] | None = None,
    ai_lineage_store_proof_ref: str | None = None,
    ai_model_risk_operations_proof: Mapping[str, object] | None = None,
    ai_model_risk_operations_proof_ref: str | None = None,
    operator_workflows_operations_proof: Mapping[str, object] | None = None,
    operator_workflows_operations_proof_ref: str | None = None,
    ai_workflow_pack_registration_proof: Mapping[str, object] | None = None,
    ai_workflow_pack_registration_proof_ref: str | None = None,
    ai_workflow_pack_runtime_execution_proof: Mapping[str, object] | None = None,
    ai_workflow_pack_runtime_execution_proof_ref: str | None = None,
    advise_proposal_route_proof: Mapping[str, object] | None = None,
    advise_proposal_route_proof_ref: str | None = None,
    advise_intake_runtime_execution_proof: Mapping[str, object] | None = None,
    advise_intake_runtime_execution_proof_ref: str | None = None,
    manage_intake_runtime_execution_proof: Mapping[str, object] | None = None,
    manage_intake_runtime_execution_proof_ref: str | None = None,
    manage_action_route_proof: Mapping[str, object] | None = None,
    manage_action_route_proof_ref: str | None = None,
    report_intake_route_source_contract_proof: Mapping[str, object] | None = None,
    report_intake_route_source_contract_proof_ref: str | None = None,
    report_materialization_source_contract_proof: Mapping[str, object] | None = None,
    report_materialization_source_contract_proof_ref: str | None = None,
    report_materialization_runtime_execution_proof: Mapping[str, object] | None = None,
    report_materialization_runtime_execution_proof_ref: str | None = None,
    mesh_policy_source_contract_proof: Mapping[str, object] | None = None,
    mesh_policy_source_contract_proof_ref: str | None = None,
    outbox_broker_source_contract_proof: Mapping[str, object] | None = None,
    outbox_broker_source_contract_proof_ref: str | None = None,
    outbox_consumer_contract_proof: Mapping[str, object] | None = None,
    outbox_consumer_contract_proof_ref: str | None = None,
    outbox_platform_mesh_event_source_contract_proof: Mapping[str, object] | None = None,
    outbox_platform_mesh_event_source_contract_proof_ref: str | None = None,
    platform_catalog_source_contract_proof: Mapping[str, object] | None = None,
    platform_catalog_source_contract_proof_ref: str | None = None,
    workbench_read_path_source_contract_proof: Mapping[str, object] | None = None,
    workbench_read_path_source_contract_proof_ref: str | None = None,
    gateway_workbench_contract_proof: Mapping[str, object] | None = None,
    gateway_workbench_contract_proof_ref: str | None = None,
    gateway_workbench_discovery_contract_proof: Mapping[str, object] | None = None,
    gateway_workbench_discovery_contract_proof_ref: str | None = None,
    risk_concentration_live_proof: Mapping[str, object] | None = None,
    risk_concentration_live_proof_ref: str | None = None,
    high_volatility_live_proof: Mapping[str, object] | None = None,
    high_volatility_live_proof_ref: str | None = None,
    risk_drawdown_live_proof: Mapping[str, object] | None = None,
    risk_drawdown_live_proof_ref: str | None = None,
    performance_underperformance_live_proof: Mapping[str, object] | None = None,
    performance_underperformance_live_proof_ref: str | None = None,
    core_benchmark_assignment_live_proof: Mapping[str, object] | None = None,
    core_benchmark_assignment_live_proof_ref: str | None = None,
    core_portfolio_state_live_proof: Mapping[str, object] | None = None,
    core_portfolio_state_live_proof_ref: str | None = None,
    bond_maturity_live_proof: Mapping[str, object] | None = None,
    bond_maturity_live_proof_ref: str | None = None,
    low_income_core_cashflow_live_proof: Mapping[str, object] | None = None,
    low_income_core_cashflow_live_proof_ref: str | None = None,
    manage_mandate_live_proof: Mapping[str, object] | None = None,
    manage_mandate_live_proof_ref: str | None = None,
    mandate_restriction_live_proof: Mapping[str, object] | None = None,
    mandate_restriction_live_proof_ref: str | None = None,
    mandate_restriction_source_product_proof: Mapping[str, object] | None = None,
    mandate_restriction_source_product_proof_ref: str | None = None,
    missing_suitability_live_proof: Mapping[str, object] | None = None,
    missing_suitability_live_proof_ref: str | None = None,
    missing_risk_profile_source_product_proof: Mapping[str, object] | None = None,
    missing_risk_profile_source_product_proof_ref: str | None = None,
    missing_risk_profile_live_proof: Mapping[str, object] | None = None,
    missing_risk_profile_live_proof_ref: str | None = None,
    missing_benchmark_live_proof: Mapping[str, object] | None = None,
    missing_benchmark_live_proof_ref: str | None = None,
    missing_benchmark_performance_readiness_proof: Mapping[str, object] | None = None,
    missing_benchmark_performance_readiness_proof_ref: str | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> ImplementationProofReadinessSnapshot:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")
    source_ingestion = build_source_ingestion_readiness_snapshot(
        repository_root=repository_root,
        evaluated_at_utc=evaluated_at_utc,
        runtime_execution_proof_ref=source_ingestion_runtime_execution_ref,
    )
    review_queue = build_review_queue_readiness_snapshot(
        BuildReviewQueueFromRepositoryCommand(evaluated_at_utc=evaluated_at_utc),
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    ai_explanation = build_ai_explanation_readiness_snapshot()
    data_mesh = build_data_mesh_readiness_snapshot(repository_root=repository_root)
    runtime_trust_telemetry = build_runtime_trust_telemetry_preview(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        generated_at_utc=evaluated_at_utc,
    )
    downstream_realization = build_downstream_realization_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        evaluated_at_utc=evaluated_at_utc,
        advise_intake_runtime_execution_proof=advise_intake_runtime_execution_proof,
        advise_intake_runtime_execution_proof_ref=advise_intake_runtime_execution_proof_ref,
        manage_intake_runtime_execution_proof=manage_intake_runtime_execution_proof,
        manage_intake_runtime_execution_proof_ref=manage_intake_runtime_execution_proof_ref,
        report_materialization_runtime_execution_proof=(
            report_materialization_runtime_execution_proof
        ),
        report_materialization_runtime_execution_proof_ref=(
            report_materialization_runtime_execution_proof_ref
        ),
    )
    outbox_delivery = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    opportunity_archetype_scenario = build_opportunity_archetype_scenario_readiness(
        repository_root=repository_root,
    )
    supported_feature_evaluation = evaluate_supported_feature_promotion(
        repository_root / SUPPORTED_FEATURES_PATH,
        evaluated_at_utc=evaluated_at_utc,
    )
    capabilities = _build_capabilities_with_available_proofs(locals())
    return _readiness_snapshot(evaluated_at_utc, supported_feature_evaluation, capabilities)


def _readiness_snapshot(
    evaluated_at_utc: datetime,
    supported_feature_evaluation: SupportedFeaturePromotionEvaluation,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
) -> ImplementationProofReadinessSnapshot:
    overall_blockers = tuple(
        dict.fromkeys(blocker for capability in capabilities for blocker in capability.blockers)
    )
    certification_ready = not overall_blockers
    return ImplementationProofReadinessSnapshot(
        repository="lotus-idea",
        evaluated_at_utc=evaluated_at_utc,
        readiness_status=("ready" if certification_ready else "blocked"),
        supportability_status=("supported" if certification_ready else "not_certified"),
        certification_ready=certification_ready,
        capability_count=len(capabilities),
        certification_ready_capability_count=sum(
            1 for capability in capabilities if capability.certification_ready
        ),
        blocked_capability_count=sum(
            1 for capability in capabilities if not capability.certification_ready
        ),
        supported_feature_count=supported_feature_evaluation.promoted_feature_count,
        supported_features_promoted=supported_feature_evaluation.supported_features_promoted,
        overall_blockers=overall_blockers,
        source_of_truth={
            "rfc": "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-enterprise-opportunity-intelligence-operating-layer.md",
            "demo_claims": "docs/demo/demo-claims.md",
            "supported_features": "supported-features/supported-features.json",
            "endpoint_certification": "docs/operations/endpoint-certification-ledger.json",
            "opportunity_archetypes": str(OPPORTUNITY_ARCHETYPE_CONTRACT_PATH.as_posix()),
        },
        capabilities=capabilities,
    )


def _build_capabilities_with_available_proofs(
    scope: Mapping[str, object],
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    source_ingestion_runtime_execution_current = (
        source_ingestion_runtime_execution_is_registered_and_current(
            cast(Mapping[str, object] | None, scope["source_ingestion_runtime_execution"]),
            evaluated_at_utc=cast(datetime, scope["evaluated_at_utc"]),
            proof_ref=cast(str | None, scope["source_ingestion_runtime_execution_ref"]),
            repository_root=cast(Path, scope["repository_root"]),
        )
    )
    capabilities = _build_base_capabilities(
        source_ingestion=cast(SourceIngestionReadinessSnapshot, scope["source_ingestion"]),
        source_ingestion_runtime_execution_current=source_ingestion_runtime_execution_current,
        source_ingestion_runtime_execution_ref=cast(
            str | None, scope["source_ingestion_runtime_execution_ref"]
        ),
        source_ingestion_scheduled_worker_source_contract_ref=cast(
            str | None,
            scope["source_ingestion_scheduled_worker_source_contract_ref"],
        ),
        source_ingestion_scheduled_worker_deployment_evidence_ref=cast(
            str | None,
            scope["source_ingestion_scheduled_worker_deployment_evidence_ref"],
        ),
        review_queue=cast(ReviewQueueReadinessSnapshot, scope["review_queue"]),
        ai_explanation=cast(AIExplanationReadinessSnapshot, scope["ai_explanation"]),
        data_mesh=cast(DataMeshReadinessSnapshot, scope["data_mesh"]),
        runtime_trust_telemetry=cast(
            RuntimeTrustTelemetryPreview, scope["runtime_trust_telemetry"]
        ),
        outbox_delivery=cast(OutboxDeliveryReadinessSnapshot, scope["outbox_delivery"]),
        opportunity_archetype_scenario=cast(
            ImplementationProofCapabilityReadiness,
            scope["opportunity_archetype_scenario"],
        ),
        downstream_realization=cast(
            DownstreamRealizationReadinessSnapshot,
            scope["downstream_realization"],
        ),
        supported_feature_evaluation=cast(
            SupportedFeaturePromotionEvaluation,
            scope["supported_feature_evaluation"],
        ),
    )
    proof_scope = dict(scope)
    proof_scope["source_ingestion_runtime_execution_current"] = (
        source_ingestion_runtime_execution_current
    )
    return apply_available_proofs_from_scope(capabilities=capabilities, scope=proof_scope)


def _build_base_capabilities(
    *,
    source_ingestion: SourceIngestionReadinessSnapshot,
    source_ingestion_runtime_execution_current: bool,
    source_ingestion_runtime_execution_ref: str | None,
    source_ingestion_scheduled_worker_source_contract_ref: str | None,
    source_ingestion_scheduled_worker_deployment_evidence_ref: str | None,
    review_queue: ReviewQueueReadinessSnapshot,
    ai_explanation: AIExplanationReadinessSnapshot,
    data_mesh: DataMeshReadinessSnapshot,
    runtime_trust_telemetry: RuntimeTrustTelemetryPreview,
    outbox_delivery: OutboxDeliveryReadinessSnapshot,
    opportunity_archetype_scenario: ImplementationProofCapabilityReadiness,
    downstream_realization: DownstreamRealizationReadinessSnapshot,
    supported_feature_evaluation: SupportedFeaturePromotionEvaluation,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    return (
        _source_ingestion_capability(
            source_ingestion,
            live_proof_current=source_ingestion_runtime_execution_current,
            live_proof_ref=source_ingestion_runtime_execution_ref,
            scheduled_worker_source_contract_ref=(
                source_ingestion_scheduled_worker_source_contract_ref
            ),
            scheduled_worker_deployment_evidence_ref=(
                source_ingestion_scheduled_worker_deployment_evidence_ref
            ),
        ),
        _review_queue_capability(review_queue),
        _ai_explanation_capability(ai_explanation),
        _data_mesh_capability(data_mesh),
        _runtime_trust_telemetry_capability(runtime_trust_telemetry),
        _outbox_delivery_capability(outbox_delivery),
        _operator_workflows_operations_capability(),
        _workbench_product_capability(),
        opportunity_archetype_scenario,
        _downstream_realization_capability(downstream_realization),
        _supported_feature_capability(supported_feature_evaluation),
    )


def _source_ingestion_capability(
    snapshot: SourceIngestionReadinessSnapshot,
    *,
    live_proof_current: bool,
    live_proof_ref: str | None,
    scheduled_worker_source_contract_ref: str | None,
    scheduled_worker_deployment_evidence_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    evidence_refs = [
        "src/app/application/source_ingestion.py",
        "scripts/run_source_ingestion_worker.py",
        "scripts/run_scheduled_source_ingestion_worker.py",
        "scripts/source_ingestion/generate_runtime_execution.py",
        "scripts/source_ingestion_scheduler/generate_source_contract.py",
        "scripts/source_ingestion_scheduler/generate_deployment_evidence.py",
        "docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
        "make source-ingestion-worker-check",
        "make source-ingestion-scheduled-worker-check",
        "make source-ingestion-runtime-execution-contract-gate",
        "GET /api/v1/source-ingestion/readiness",
        "POST /api/v1/source-ingestion/run-once",
    ]
    if live_proof_current and live_proof_ref:
        evidence_refs.append(live_proof_ref)
    if snapshot.scheduled_worker_source_contract_valid and scheduled_worker_source_contract_ref:
        evidence_refs.append(scheduled_worker_source_contract_ref)
    if (
        snapshot.scheduled_worker_deployment_evidence_valid
        and scheduled_worker_deployment_evidence_ref
    ):
        evidence_refs.append(scheduled_worker_deployment_evidence_ref)
    return build_capability_readiness(
        "source-ingestion",
        "Source-owned high-cash signal ingestion",
        readiness_status=snapshot.run_once_configuration_status,
        supportability_status=snapshot.certification_status,
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        blockers=tuple(
            dict.fromkeys(
                (
                    *snapshot.configuration_blockers,
                    *_source_ingestion_certification_blockers(
                        snapshot,
                        live_proof_current=live_proof_current,
                    ),
                )
            )
        ),
    )


def _source_ingestion_certification_blockers(
    snapshot: SourceIngestionReadinessSnapshot,
    *,
    live_proof_current: bool,
) -> tuple[str, ...]:
    blockers = [
        blocker
        for blocker in snapshot.certification_blockers
        if not live_proof_current or blocker != "live_core_source_proof_missing"
    ]
    if not live_proof_current and "live_core_source_proof_missing" not in blockers:
        blockers.insert(0, "live_core_source_proof_missing")
    return tuple(blockers)


def _review_queue_capability(
    snapshot: ReviewQueueReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "advisor-review-queue",
        "Deterministic advisor review queue",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=(
            "src/app/application/review_queue.py",
            "GET /api/v1/review-queues/advisor",
            "GET /api/v1/review-queues/advisor/readiness",
            "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
        ),
        blockers=snapshot.certification_blockers,
    )


def _ai_explanation_capability(
    snapshot: AIExplanationReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "ai-explanation",
        "AI-assisted explanation governance",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=(
            "src/app/application/ai_governance.py",
            "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json",
            "make ai-model-risk-ops-contract-gate",
            "make ai-model-risk-operations-proof-contract-gate",
            "make ai-workflow-pack-registration-proof-contract-gate",
            "make ai-workflow-pack-runtime-execution-proof-contract-gate",
            "POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
            "GET /api/v1/ai-explanations/readiness",
        ),
        blockers=snapshot.certification_blockers,
    )


def _data_mesh_capability(
    snapshot: DataMeshReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "data-mesh-certification",
        "Data-mesh producer and consumer certification",
        readiness_status=snapshot.lifecycle_status,
        supportability_status=snapshot.certification_status,
        evidence_refs=(
            "contracts/domain-data-products/lotus-idea-products.v1.json",
            "contracts/domain-data-products/lotus-idea-consumers.v1.json",
            "contracts/trust-telemetry/idea-candidate.telemetry.v1.json",
            "GET /api/v1/data-mesh/readiness",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-preview",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot",
            "make runtime-trust-telemetry-preview-check",
            "make runtime-trust-telemetry-snapshot-check",
        ),
        blockers=snapshot.blockers,
    )


def _runtime_trust_telemetry_capability(
    snapshot: RuntimeTrustTelemetryPreview,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "runtime-trust-telemetry-preview",
        "Source-safe runtime trust telemetry preview",
        readiness_status=("ready" if snapshot.certification_ready else "blocked"),
        supportability_status=snapshot.certification_status,
        evidence_refs=(
            "src/app/application/runtime_trust_telemetry/telemetry.py",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-preview",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot",
            "scripts/runtime_trust_telemetry/generate_preview.py",
            "scripts/runtime_trust_telemetry/generate_snapshot.py",
            "make runtime-trust-telemetry-preview-check",
            "make runtime-trust-telemetry-snapshot-check",
        ),
        blockers=snapshot.certification_blockers,
    )


def _outbox_delivery_capability(
    snapshot: OutboxDeliveryReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "outbox-delivery",
        "Internal outbox delivery foundation",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=(
            "src/app/application/outbox/delivery.py",
            "src/app/application/outbox/readiness.py",
            "src/app/ports/outbox/publisher.py",
            "src/app/infrastructure/outbox/publisher.py",
            "contracts/outbox-events/lotus-idea-outbox-events.v1.json",
            "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
            "make outbox-event-contract-gate",
            "make outbox-consumer-contract-gate",
            "make outbox-broker-source-contract-proof-gate",
            "make outbox-consumer-contract-proof-contract-gate",
            "make outbox-platform-mesh-event-source-contract-proof-gate",
            "GET /api/v1/outbox-delivery/readiness",
            "POST /api/v1/outbox-delivery/run-once",
        ),
        blockers=(
            *snapshot.configuration_blockers,
            *snapshot.certification_blockers,
        ),
    )


def _operator_workflows_operations_capability() -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "operator-workflows-operations",
        "Non-AI operator workflow operations",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS,
        blockers=(
            *OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED,
            *REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS,
        ),
    )


def _workbench_product_capability() -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "workbench-product-proof",
        "Workbench product realization",
        readiness_status="planned",
        supportability_status="not_certified",
        evidence_refs=(
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md",
            "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
            "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
        ),
        blockers=(
            "workbench_panel_missing",
            "workbench_gateway_bff_consumption_proof_missing",
            "browser_accessibility_proof_missing",
            "canonical_demo_runtime_proof_missing",
        ),
    )


def _downstream_realization_capability(
    snapshot: DownstreamRealizationReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    contract_evidence_refs = tuple(
        dict.fromkeys(
            evidence_ref
            for contract in snapshot.downstream_contracts
            for evidence_ref in contract.evidence_refs
        )
    )
    return build_capability_readiness(
        "downstream-realization",
        "Advise, Manage, Report, Render, and Archive realization",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    "GET /api/v1/downstream-realization/readiness",
                    "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
                    "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
                    "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
                    "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
                    "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
                    *contract_evidence_refs,
                )
            )
        ),
        blockers=snapshot.blockers,
    )


def _supported_feature_capability(
    evaluation: SupportedFeaturePromotionEvaluation,
) -> ImplementationProofCapabilityReadiness:
    return build_capability_readiness(
        "supported-feature-promotion",
        "Implementation-backed supported-feature promotion",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=(
            evaluation.source_ref,
            "docs/demo/demo-claims.md",
            "wiki/Supported-Features.md",
            "wiki/Demo-Readiness.md",
        ),
        blockers=evaluation.blocker_codes,
        supported_feature_promoted=evaluation.supported_features_promoted,
    )
