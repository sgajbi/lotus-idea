from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from app.application.ai_governance import build_ai_explanation_readiness_snapshot
from app.application.data_mesh_readiness import (
    REPOSITORY_ROOT,
    build_data_mesh_readiness_snapshot,
)
from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    build_review_queue_readiness_snapshot,
)
from app.application.source_ingestion_readiness import (
    build_source_ingestion_readiness_snapshot,
)
from app.ports.idea_repository import CandidateSnapshotRepository

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
    repository: CandidateSnapshotRepository,
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
    supported_feature_count = _supported_feature_count(repository_root / SUPPORTED_FEATURES_PATH)

    capabilities = (
        _capability(
            "source-ingestion",
            "Source-owned high-cash signal ingestion",
            readiness_status=source_ingestion.run_once_configuration_status,
            supportability_status=source_ingestion.certification_status,
            evidence_refs=(
                "src/app/application/source_ingestion.py",
                "scripts/run_source_ingestion_worker.py",
                "docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
                "make source-ingestion-worker-check",
            ),
            blockers=(
                *source_ingestion.configuration_blockers,
                *source_ingestion.certification_blockers,
            ),
        ),
        _capability(
            "advisor-review-queue",
            "Deterministic advisor review queue",
            readiness_status=review_queue.readiness_status,
            supportability_status=review_queue.supportability_status,
            evidence_refs=(
                "src/app/application/review_queue.py",
                "GET /api/v1/review-queues/advisor",
                "GET /api/v1/review-queues/advisor/readiness",
                "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
            ),
            blockers=review_queue.certification_blockers,
        ),
        _capability(
            "ai-explanation",
            "AI-assisted explanation governance",
            readiness_status=ai_explanation.readiness_status,
            supportability_status=ai_explanation.supportability_status,
            evidence_refs=(
                "src/app/application/ai_governance.py",
                "POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
                "GET /api/v1/ai-explanations/readiness",
            ),
            blockers=ai_explanation.certification_blockers,
        ),
        _capability(
            "data-mesh-certification",
            "Data-mesh producer and consumer certification",
            readiness_status=data_mesh.lifecycle_status,
            supportability_status=data_mesh.certification_status,
            evidence_refs=(
                "contracts/domain-data-products/lotus-idea-products.v1.json",
                "contracts/domain-data-products/lotus-idea-consumers.v1.json",
                "contracts/trust-telemetry/idea-candidate.telemetry.v1.json",
                "GET /api/v1/data-mesh/readiness",
            ),
            blockers=data_mesh.blockers,
        ),
        _capability(
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
        ),
        _capability(
            "downstream-realization",
            "Advise, Manage, Report, Render, and Archive realization",
            readiness_status="planned",
            supportability_status="not_certified",
            evidence_refs=(
                "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
                "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
                "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
            ),
            blockers=(
                "advise_proposal_creation_adapter_missing",
                "manage_action_register_adapter_missing",
                "report_render_archive_materialization_missing",
                "downstream_live_contract_proof_missing",
            ),
        ),
        _capability(
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
            blockers=(
                ()
                if supported_feature_count
                else ("no_supported_features_promoted",)
            ),
            supported_feature_promoted=bool(supported_feature_count),
        ),
    )

    overall_blockers = tuple(
        dict.fromkeys(
            blocker for capability in capabilities for blocker in capability.blockers
        )
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


def _supported_feature_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", ())
    if not isinstance(features, list):
        raise ValueError("supported features must be a list")
    return len(features)
