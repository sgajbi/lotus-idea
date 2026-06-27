from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.application.ai_governance import (
    AIExplanationReadinessSnapshot,
    build_ai_explanation_readiness_snapshot,
)
from app.application.ai_lineage_store_proof import ai_lineage_store_proof_is_valid
from app.application.ai_model_risk_operations_proof import (
    ai_model_risk_operations_proof_is_valid,
)
from app.application.ai_workflow_pack_registration_proof import (
    ai_workflow_pack_registration_proof_is_valid,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    ai_workflow_pack_runtime_execution_proof_is_valid,
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
from app.application.durable_repository_proof import durable_repository_proof_is_valid
from app.application.outbox_broker_proof import outbox_broker_proof_is_valid
from app.application.outbox_delivery_readiness import (
    OutboxDeliveryReadinessSnapshot,
    build_outbox_delivery_readiness_snapshot,
)
from app.application.platform_mesh_onboarding_proof import (
    PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED,
    platform_mesh_onboarding_proof_is_valid,
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
from app.application.runtime_trust_telemetry_proof import (
    RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED,
    runtime_trust_telemetry_proof_is_valid,
)
from app.application.source_ingestion_readiness import (
    SourceIngestionReadinessSnapshot,
    build_source_ingestion_readiness_snapshot,
)
from app.application.workbench_read_path_proof import workbench_read_path_proof_is_valid
from app.ports.idea_repository import OutboxDeliveryRepository

SUPPORTED_FEATURES_PATH = Path("supported-features/supported-features.json")


@dataclass(frozen=True)
class ImplementationProofCapabilityReadiness:
    capability_id: str
    name: str
    readiness_status: str
    supportability_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    supported_feature_promoted: bool

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))


@dataclass(frozen=True)
class ImplementationProofReadinessSnapshot:
    repository: str
    evaluated_at_utc: datetime
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    capability_count: int
    certification_ready_capability_count: int
    blocked_capability_count: int
    supported_feature_count: int
    supported_features_promoted: bool
    overall_blockers: tuple[str, ...]
    source_of_truth: Mapping[str, str]
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "overall_blockers", tuple(self.overall_blockers))
        object.__setattr__(
            self,
            "source_of_truth",
            MappingProxyType(dict(self.source_of_truth)),
        )
        object.__setattr__(self, "capabilities", tuple(self.capabilities))


def build_implementation_proof_readiness_snapshot(
    *,
    evaluated_at_utc: datetime,
    repository: OutboxDeliveryRepository,
    durable_storage_backed: bool,
    source_ingestion_live_proof_ref: str | None = None,
    source_ingestion_scheduled_worker_proof_ref: str | None = None,
    durable_repository_proof: Mapping[str, object] | None = None,
    durable_repository_proof_ref: str | None = None,
    runtime_trust_telemetry_proof: Mapping[str, object] | None = None,
    runtime_trust_telemetry_proof_ref: str | None = None,
    ai_lineage_store_proof: Mapping[str, object] | None = None,
    ai_lineage_store_proof_ref: str | None = None,
    ai_model_risk_operations_proof: Mapping[str, object] | None = None,
    ai_model_risk_operations_proof_ref: str | None = None,
    ai_workflow_pack_registration_proof: Mapping[str, object] | None = None,
    ai_workflow_pack_registration_proof_ref: str | None = None,
    ai_workflow_pack_runtime_execution_proof: Mapping[str, object] | None = None,
    ai_workflow_pack_runtime_execution_proof_ref: str | None = None,
    report_intake_route_proof: Mapping[str, object] | None = None,
    report_intake_route_proof_ref: str | None = None,
    outbox_broker_proof: Mapping[str, object] | None = None,
    outbox_broker_proof_ref: str | None = None,
    platform_mesh_onboarding_proof: Mapping[str, object] | None = None,
    platform_mesh_onboarding_proof_ref: str | None = None,
    workbench_read_path_proof: Mapping[str, object] | None = None,
    workbench_read_path_proof_ref: str | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> ImplementationProofReadinessSnapshot:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")

    source_ingestion = build_source_ingestion_readiness_snapshot(
        repository_root=repository_root,
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
        report_intake_route_proof=report_intake_route_proof,
        report_intake_route_proof_ref=report_intake_route_proof_ref,
    )
    outbox_delivery = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    supported_feature_count = _supported_feature_count(repository_root / SUPPORTED_FEATURES_PATH)

    capabilities: tuple[ImplementationProofCapabilityReadiness, ...] = (
        _source_ingestion_capability(
            source_ingestion,
            live_proof_ref=source_ingestion_live_proof_ref,
            scheduled_worker_proof_ref=source_ingestion_scheduled_worker_proof_ref,
        ),
        _review_queue_capability(review_queue),
        _ai_explanation_capability(ai_explanation),
        _data_mesh_capability(data_mesh),
        _runtime_trust_telemetry_capability(runtime_trust_telemetry),
        _outbox_delivery_capability(outbox_delivery),
        _workbench_product_capability(),
        _downstream_realization_capability(downstream_realization),
        _supported_feature_capability(supported_feature_count),
    )
    capabilities = _apply_available_proofs(
        capabilities=capabilities,
        durable_repository_proof=durable_repository_proof,
        durable_repository_proof_ref=durable_repository_proof_ref,
        runtime_trust_telemetry_proof=runtime_trust_telemetry_proof,
        runtime_trust_telemetry_proof_ref=runtime_trust_telemetry_proof_ref,
        ai_lineage_store_proof=ai_lineage_store_proof,
        ai_lineage_store_proof_ref=ai_lineage_store_proof_ref,
        ai_model_risk_operations_proof=ai_model_risk_operations_proof,
        ai_model_risk_operations_proof_ref=ai_model_risk_operations_proof_ref,
        ai_workflow_pack_registration_proof=ai_workflow_pack_registration_proof,
        ai_workflow_pack_registration_proof_ref=ai_workflow_pack_registration_proof_ref,
        ai_workflow_pack_runtime_execution_proof=ai_workflow_pack_runtime_execution_proof,
        ai_workflow_pack_runtime_execution_proof_ref=ai_workflow_pack_runtime_execution_proof_ref,
        outbox_broker_proof=outbox_broker_proof,
        outbox_broker_proof_ref=outbox_broker_proof_ref,
        platform_mesh_onboarding_proof=platform_mesh_onboarding_proof,
        platform_mesh_onboarding_proof_ref=platform_mesh_onboarding_proof_ref,
        workbench_read_path_proof=workbench_read_path_proof,
        workbench_read_path_proof_ref=workbench_read_path_proof_ref,
    )

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
        supported_feature_count=supported_feature_count,
        supported_features_promoted=bool(supported_feature_count),
        overall_blockers=overall_blockers,
        source_of_truth={
            "rfc": "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-enterprise-opportunity-intelligence-operating-layer.md",
            "demo_claims": "docs/demo/demo-claims.md",
            "supported_features": "supported-features/supported-features.json",
            "endpoint_certification": "docs/operations/endpoint-certification-ledger.json",
        },
        capabilities=capabilities,
    )


def _apply_available_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    durable_repository_proof: Mapping[str, object] | None,
    durable_repository_proof_ref: str | None,
    runtime_trust_telemetry_proof: Mapping[str, object] | None,
    runtime_trust_telemetry_proof_ref: str | None,
    ai_lineage_store_proof: Mapping[str, object] | None,
    ai_lineage_store_proof_ref: str | None,
    ai_model_risk_operations_proof: Mapping[str, object] | None,
    ai_model_risk_operations_proof_ref: str | None,
    ai_workflow_pack_registration_proof: Mapping[str, object] | None,
    ai_workflow_pack_registration_proof_ref: str | None,
    ai_workflow_pack_runtime_execution_proof: Mapping[str, object] | None,
    ai_workflow_pack_runtime_execution_proof_ref: str | None,
    outbox_broker_proof: Mapping[str, object] | None,
    outbox_broker_proof_ref: str | None,
    platform_mesh_onboarding_proof: Mapping[str, object] | None,
    platform_mesh_onboarding_proof_ref: str | None,
    workbench_read_path_proof: Mapping[str, object] | None,
    workbench_read_path_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if durable_repository_proof and durable_repository_proof_is_valid(durable_repository_proof):
        capabilities = tuple(
            _apply_durable_repository_proof(capability, durable_repository_proof_ref)
            for capability in capabilities
        )
    if runtime_trust_telemetry_proof and runtime_trust_telemetry_proof_is_valid(
        runtime_trust_telemetry_proof
    ):
        capabilities = tuple(
            _apply_runtime_trust_telemetry_proof(
                capability,
                runtime_trust_telemetry_proof_ref,
            )
            for capability in capabilities
        )
    if ai_lineage_store_proof and ai_lineage_store_proof_is_valid(ai_lineage_store_proof):
        capabilities = tuple(
            _apply_ai_lineage_store_proof(capability, ai_lineage_store_proof_ref)
            for capability in capabilities
        )
    if ai_model_risk_operations_proof and ai_model_risk_operations_proof_is_valid(
        ai_model_risk_operations_proof
    ):
        capabilities = tuple(
            _apply_ai_model_risk_operations_proof(
                capability,
                ai_model_risk_operations_proof_ref,
            )
            for capability in capabilities
        )
    if ai_workflow_pack_registration_proof and ai_workflow_pack_registration_proof_is_valid(
        ai_workflow_pack_registration_proof
    ):
        capabilities = tuple(
            _apply_ai_workflow_pack_registration_proof(
                capability,
                ai_workflow_pack_registration_proof_ref,
            )
            for capability in capabilities
        )
    if (
        ai_workflow_pack_runtime_execution_proof
        and ai_workflow_pack_runtime_execution_proof_is_valid(
            ai_workflow_pack_runtime_execution_proof
        )
    ):
        capabilities = tuple(
            _apply_ai_workflow_pack_runtime_execution_proof(
                capability,
                ai_workflow_pack_runtime_execution_proof_ref,
            )
            for capability in capabilities
        )
    if outbox_broker_proof and outbox_broker_proof_is_valid(outbox_broker_proof):
        capabilities = tuple(
            _apply_outbox_broker_proof(capability, outbox_broker_proof_ref)
            for capability in capabilities
        )
    if platform_mesh_onboarding_proof and platform_mesh_onboarding_proof_is_valid(
        platform_mesh_onboarding_proof
    ):
        capabilities = tuple(
            _apply_platform_mesh_onboarding_proof(
                capability,
                platform_mesh_onboarding_proof_ref,
            )
            for capability in capabilities
        )
    if workbench_read_path_proof and workbench_read_path_proof_is_valid(workbench_read_path_proof):
        capabilities = tuple(
            _apply_workbench_read_path_proof(capability, workbench_read_path_proof_ref)
            for capability in capabilities
        )
    return capabilities


def _capability(
    capability_id: str,
    name: str,
    *,
    readiness_status: str,
    supportability_status: str,
    evidence_refs: tuple[str, ...],
    blockers: tuple[str, ...],
    supported_feature_promoted: bool = False,
) -> ImplementationProofCapabilityReadiness:
    return ImplementationProofCapabilityReadiness(
        capability_id=capability_id,
        name=name,
        readiness_status=readiness_status,
        supportability_status=supportability_status,
        evidence_refs=evidence_refs,
        blockers=blockers,
        supported_feature_promoted=supported_feature_promoted,
    )


def _apply_durable_repository_proof(
    capability: ImplementationProofCapabilityReadiness,
    durable_repository_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if "durable_repository_not_configured" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if durable_repository_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, durable_repository_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "durable_repository_not_configured"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_runtime_trust_telemetry_proof(
    capability: ImplementationProofCapabilityReadiness,
    runtime_trust_telemetry_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    blockers_to_clear = set(RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED)
    if not blockers_to_clear.intersection(capability.blockers):
        return capability
    evidence_refs = capability.evidence_refs
    if runtime_trust_telemetry_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, runtime_trust_telemetry_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_workbench_read_path_proof(
    capability: ImplementationProofCapabilityReadiness,
    workbench_read_path_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if "workbench_gateway_bff_consumption_proof_missing" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if workbench_read_path_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, workbench_read_path_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "workbench_gateway_bff_consumption_proof_missing"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_lineage_store_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_lineage_store_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "certified_ai_lineage_store_missing" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_lineage_store_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, ai_lineage_store_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "certified_ai_lineage_store_missing"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_model_risk_operations_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_model_risk_operations_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    blockers_to_clear = {
        "model_risk_operations_dashboard_not_certified",
        "model_risk_operations_alerts_not_certified",
    }
    evidence_refs = capability.evidence_refs
    if ai_model_risk_operations_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, ai_model_risk_operations_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_workflow_pack_registration_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_workflow_pack_registration_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "workflow_pack_runtime_contract_not_certified" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_workflow_pack_registration_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, ai_workflow_pack_registration_proof_ref))
        )
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "workflow_pack_runtime_contract_not_certified"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_ai_workflow_pack_runtime_execution_proof(
    capability: ImplementationProofCapabilityReadiness,
    ai_workflow_pack_runtime_execution_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "ai-explanation":
        return capability
    if "lotus_ai_runtime_execution_missing" not in capability.blockers:
        return capability
    evidence_refs = capability.evidence_refs
    if ai_workflow_pack_runtime_execution_proof_ref:
        evidence_refs = tuple(
            dict.fromkeys((*evidence_refs, ai_workflow_pack_runtime_execution_proof_ref))
        )
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker
            for blocker in capability.blockers
            if blocker != "lotus_ai_runtime_execution_missing"
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_outbox_broker_proof(
    capability: ImplementationProofCapabilityReadiness,
    outbox_broker_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id != "outbox-delivery":
        return capability
    blockers_to_clear = {
        "outbox_broker_not_configured",
        "external_broker_runtime_proof_missing",
    }
    if not blockers_to_clear.intersection(capability.blockers):
        return capability
    evidence_refs = capability.evidence_refs
    if outbox_broker_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, outbox_broker_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _apply_platform_mesh_onboarding_proof(
    capability: ImplementationProofCapabilityReadiness,
    platform_mesh_onboarding_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    if capability.capability_id not in {
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
    }:
        return capability
    blockers_to_clear = set(PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED)
    if not blockers_to_clear.intersection(capability.blockers):
        return capability
    evidence_refs = capability.evidence_refs
    if platform_mesh_onboarding_proof_ref:
        evidence_refs = tuple(dict.fromkeys((*evidence_refs, platform_mesh_onboarding_proof_ref)))
    return _capability(
        capability.capability_id,
        capability.name,
        readiness_status=capability.readiness_status,
        supportability_status=capability.supportability_status,
        evidence_refs=evidence_refs,
        blockers=tuple(
            blocker for blocker in capability.blockers if blocker not in blockers_to_clear
        ),
        supported_feature_promoted=capability.supported_feature_promoted,
    )


def _source_ingestion_capability(
    snapshot: SourceIngestionReadinessSnapshot,
    *,
    live_proof_ref: str | None,
    scheduled_worker_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    evidence_refs = [
        "src/app/application/source_ingestion.py",
        "scripts/run_source_ingestion_worker.py",
        "scripts/run_scheduled_source_ingestion_worker.py",
        "scripts/generate_source_ingestion_live_proof.py",
        "scripts/generate_scheduled_source_ingestion_worker_proof.py",
        "docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
        "make source-ingestion-worker-check",
        "make source-ingestion-scheduled-worker-check",
        "make source-ingestion-live-proof-contract-gate",
        "GET /api/v1/source-ingestion/readiness",
        "POST /api/v1/source-ingestion/run-once",
    ]
    if snapshot.live_core_source_proof_valid and live_proof_ref:
        evidence_refs.append(live_proof_ref)
    if snapshot.scheduled_worker_deploy_proof_valid and scheduled_worker_proof_ref:
        evidence_refs.append(scheduled_worker_proof_ref)
    return _capability(
        "source-ingestion",
        "Source-owned high-cash signal ingestion",
        readiness_status=snapshot.run_once_configuration_status,
        supportability_status=snapshot.certification_status,
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        blockers=(
            *snapshot.configuration_blockers,
            *snapshot.certification_blockers,
        ),
    )


def _review_queue_capability(
    snapshot: ReviewQueueReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return _capability(
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
    return _capability(
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
    return _capability(
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
    return _capability(
        "runtime-trust-telemetry-preview",
        "Source-safe runtime trust telemetry preview",
        readiness_status=("ready" if snapshot.certification_ready else "blocked"),
        supportability_status=snapshot.certification_status,
        evidence_refs=(
            "src/app/application/runtime_trust_telemetry.py",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-preview",
            "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot",
            "scripts/generate_runtime_trust_telemetry_preview.py",
            "scripts/generate_runtime_trust_telemetry_snapshot.py",
            "make runtime-trust-telemetry-preview-check",
            "make runtime-trust-telemetry-snapshot-check",
        ),
        blockers=snapshot.certification_blockers,
    )


def _outbox_delivery_capability(
    snapshot: OutboxDeliveryReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return _capability(
        "outbox-delivery",
        "Internal outbox delivery foundation",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=(
            "src/app/application/outbox_delivery.py",
            "src/app/application/outbox_delivery_readiness.py",
            "src/app/ports/outbox_publisher.py",
            "src/app/infrastructure/outbox_publisher.py",
            "make outbox-broker-proof-contract-gate",
            "GET /api/v1/outbox-delivery/readiness",
            "POST /api/v1/outbox-delivery/run-once",
        ),
        blockers=(
            *snapshot.configuration_blockers,
            *snapshot.certification_blockers,
        ),
    )


def _workbench_product_capability() -> ImplementationProofCapabilityReadiness:
    return _capability(
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
    return _capability(
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
    supported_feature_count: int,
) -> ImplementationProofCapabilityReadiness:
    return _capability(
        "supported-feature-promotion",
        "Implementation-backed supported-feature promotion",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=(
            "supported-features/supported-features.json",
            "docs/demo/demo-claims.md",
            "wiki/Supported-Features.md",
            "wiki/Demo-Readiness.md",
        ),
        blockers=(() if supported_feature_count else ("no_supported_features_promoted",)),
        supported_feature_promoted=bool(supported_feature_count),
    )


def _supported_feature_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", ())
    if not isinstance(features, list):
        raise ValueError("supported features must be a list")
    return len(features)
