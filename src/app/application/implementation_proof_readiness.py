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
from app.application.data_mesh_readiness import (
    DataMeshReadinessSnapshot,
    REPOSITORY_ROOT,
    build_data_mesh_readiness_snapshot,
)
from app.application.downstream_realization_readiness import (
    DownstreamRealizationReadinessSnapshot,
    build_downstream_realization_readiness_snapshot,
)
from app.application.outbox_delivery_readiness import (
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
    )
    outbox_delivery = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    supported_feature_count = _supported_feature_count(repository_root / SUPPORTED_FEATURES_PATH)

    capabilities = (
        _source_ingestion_capability(source_ingestion),
        _review_queue_capability(review_queue),
        _ai_explanation_capability(ai_explanation),
        _data_mesh_capability(data_mesh),
        _runtime_trust_telemetry_capability(runtime_trust_telemetry),
        _outbox_delivery_capability(outbox_delivery),
        _workbench_product_capability(),
        _downstream_realization_capability(downstream_realization),
        _supported_feature_capability(supported_feature_count),
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


def _source_ingestion_capability(
    snapshot: SourceIngestionReadinessSnapshot,
) -> ImplementationProofCapabilityReadiness:
    return _capability(
        "source-ingestion",
        "Source-owned high-cash signal ingestion",
        readiness_status=snapshot.run_once_configuration_status,
        supportability_status=snapshot.certification_status,
        evidence_refs=(
            "src/app/application/source_ingestion.py",
            "scripts/run_source_ingestion_worker.py",
            "docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
            "make source-ingestion-worker-check",
        ),
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
    return _capability(
        "downstream-realization",
        "Advise, Manage, Report, Render, and Archive realization",
        readiness_status=snapshot.readiness_status,
        supportability_status=snapshot.supportability_status,
        evidence_refs=(
            "GET /api/v1/downstream-realization/readiness",
            "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
            "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
            "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
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
