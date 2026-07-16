from __future__ import annotations

from typing import Protocol

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.source_ingestion import (
    HighCashSourceIngestionBatchResult,
    HighCashSourceIngestionDecision,
)
from app.application.source_ingestion_readiness import (
    SourceIngestionReadinessSnapshot,
    build_source_ingestion_readiness_snapshot,
)


class SourceIngestionRunOnceRuntimeView(Protocol):
    @property
    def configured_manifest_available(self) -> bool: ...

    @property
    def core_base_url_configured(self) -> bool: ...

    @property
    def core_query_base_url_configured(self) -> bool: ...

    @property
    def core_query_control_plane_base_url_configured(self) -> bool: ...


class SourceIngestionReadinessResponse(CamelModel):
    repository: str
    source_authority: str = Field(..., alias="sourceAuthority")
    opportunity_family: str = Field(..., alias="opportunityFamily")
    manifest_schema_version: str = Field(..., alias="manifestSchemaVersion")
    example_manifest_path: str = Field(..., alias="exampleManifestPath")
    example_manifest_available: bool = Field(..., alias="exampleManifestAvailable")
    configured_manifest_available: bool = Field(..., alias="configuredManifestAvailable")
    configured_live_proof_available: bool = Field(..., alias="configuredLiveProofAvailable")
    live_core_source_proof_valid: bool = Field(..., alias="liveCoreSourceProofValid")
    configured_scheduled_worker_source_contract_available: bool = Field(
        ..., alias="configuredScheduledWorkerSourceContractAvailable"
    )
    scheduled_worker_source_contract_valid: bool = Field(
        ..., alias="scheduledWorkerSourceContractValid"
    )
    configured_scheduled_worker_deployment_evidence_available: bool = Field(
        ..., alias="configuredScheduledWorkerDeploymentEvidenceAvailable"
    )
    scheduled_worker_deployment_evidence_valid: bool = Field(
        ..., alias="scheduledWorkerDeploymentEvidenceValid"
    )
    core_base_url_configured: bool = Field(..., alias="coreBaseUrlConfigured")
    core_query_base_url_configured: bool = Field(..., alias="coreQueryBaseUrlConfigured")
    core_query_control_plane_base_url_configured: bool = Field(
        ..., alias="coreQueryControlPlaneBaseUrlConfigured"
    )
    durable_repository_configured: bool = Field(..., alias="durableRepositoryConfigured")
    run_once_configuration_status: str = Field(..., alias="runOnceConfigurationStatus")
    run_once_configured: bool = Field(..., alias="runOnceConfigured")
    certification_status: str = Field(..., alias="certificationStatus")
    live_source_certified: bool = Field(..., alias="liveSourceCertified")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: SourceIngestionReadinessSnapshot,
    ) -> "SourceIngestionReadinessResponse":
        return cls(
            repository=snapshot.repository,
            sourceAuthority=snapshot.source_authority,
            opportunityFamily=snapshot.opportunity_family,
            manifestSchemaVersion=snapshot.manifest_schema_version,
            exampleManifestPath=snapshot.example_manifest_path,
            exampleManifestAvailable=snapshot.example_manifest_available,
            configuredManifestAvailable=snapshot.configured_manifest_available,
            configuredLiveProofAvailable=snapshot.configured_live_proof_available,
            liveCoreSourceProofValid=snapshot.live_core_source_proof_valid,
            configuredScheduledWorkerSourceContractAvailable=(
                snapshot.configured_scheduled_worker_source_contract_available
            ),
            scheduledWorkerSourceContractValid=snapshot.scheduled_worker_source_contract_valid,
            configuredScheduledWorkerDeploymentEvidenceAvailable=(
                snapshot.configured_scheduled_worker_deployment_evidence_available
            ),
            scheduledWorkerDeploymentEvidenceValid=(
                snapshot.scheduled_worker_deployment_evidence_valid
            ),
            coreBaseUrlConfigured=snapshot.core_base_url_configured,
            coreQueryBaseUrlConfigured=snapshot.core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=(
                snapshot.core_query_control_plane_base_url_configured
            ),
            durableRepositoryConfigured=snapshot.durable_repository_configured,
            runOnceConfigurationStatus=snapshot.run_once_configuration_status,
            runOnceConfigured=snapshot.run_once_configured,
            certificationStatus=snapshot.certification_status,
            liveSourceCertified=snapshot.live_source_certified,
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class SourceIngestionRunOnceResponse(CamelModel):
    repository: str
    run_status: str = Field(..., alias="runStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    source_authority: str = Field(..., alias="sourceAuthority")
    opportunity_family: str = Field(..., alias="opportunityFamily")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    configured_manifest_available: bool = Field(..., alias="configuredManifestAvailable")
    core_base_url_configured: bool = Field(..., alias="coreBaseUrlConfigured")
    core_query_base_url_configured: bool = Field(..., alias="coreQueryBaseUrlConfigured")
    core_query_control_plane_base_url_configured: bool = Field(
        ..., alias="coreQueryControlPlaneBaseUrlConfigured"
    )
    total_count: int = Field(..., alias="totalCount")
    decision_counts: dict[str, int] = Field(..., alias="decisionCounts")
    source_failure_counts: dict[str, int] = Field(..., alias="sourceFailureCounts")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    live_source_certified: bool = Field(False, alias="liveSourceCertified")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def blocked(
        cls,
        *,
        blocker: str,
        durable_storage_backed: bool,
        configured_manifest_available: bool = False,
        core_base_url_configured: bool = False,
        core_query_base_url_configured: bool = False,
        core_query_control_plane_base_url_configured: bool = False,
    ) -> "SourceIngestionRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="blocked",
            supportabilityStatus="not_certified",
            sourceAuthority="lotus-core",
            opportunityFamily="high_cash",
            durableStorageBacked=durable_storage_backed,
            configuredManifestAvailable=configured_manifest_available,
            coreBaseUrlConfigured=core_base_url_configured,
            coreQueryBaseUrlConfigured=core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=core_query_control_plane_base_url_configured,
            totalCount=0,
            decisionCounts=_empty_decision_counts(),
            sourceFailureCounts=_empty_source_failure_counts(),
            configurationBlockers=(blocker,),
            certificationBlockers=_source_ingestion_certification_blockers(),
            liveSourceCertified=False,
            supportedFeaturePromoted=False,
        )

    @classmethod
    def from_domain(
        cls,
        result: HighCashSourceIngestionBatchResult,
        *,
        runtime: SourceIngestionRunOnceRuntimeView,
        durable_storage_backed: bool,
    ) -> "SourceIngestionRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="completed",
            supportabilityStatus="not_certified",
            sourceAuthority=result.source_authority,
            opportunityFamily="high_cash",
            durableStorageBacked=durable_storage_backed,
            configuredManifestAvailable=runtime.configured_manifest_available,
            coreBaseUrlConfigured=runtime.core_base_url_configured,
            coreQueryBaseUrlConfigured=runtime.core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=(
                runtime.core_query_control_plane_base_url_configured
            ),
            totalCount=result.total_count,
            decisionCounts=result.decision_counts(),
            sourceFailureCounts=result.source_failure_counts(),
            configurationBlockers=(),
            certificationBlockers=_source_ingestion_certification_blockers(),
            liveSourceCertified=False,
            supportedFeaturePromoted=False,
        )


def _empty_decision_counts() -> dict[str, int]:
    return {decision.value: 0 for decision in HighCashSourceIngestionDecision}


def _empty_source_failure_counts() -> dict[str, int]:
    return {
        "source_unavailable": 0,
        "entitlement_denied": 0,
        "other_blocked": 0,
    }


def _source_ingestion_certification_blockers() -> tuple[str, ...]:
    snapshot = build_source_ingestion_readiness_snapshot()
    return (*snapshot.certification_blockers, "supported_feature_promotion_missing")
