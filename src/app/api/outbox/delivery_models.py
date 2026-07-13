from __future__ import annotations

from typing import Mapping

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.outbox.delivery import OutboxDeliveryRunSummary
from app.application.outbox.readiness import (
    OutboxDeliveryReadinessSnapshot,
    OutboxDeliveryStatusCounts,
    outbox_delivery_certification_blockers,
)


class OutboxDeliveryStatusCountsResponse(CamelModel):
    pending_count: int = Field(..., alias="pendingCount")
    leased_count: int = Field(..., alias="leasedCount")
    failed_count: int = Field(..., alias="failedCount")
    published_count: int = Field(..., alias="publishedCount")
    dead_letter_count: int = Field(..., alias="deadLetterCount")
    total_count: int = Field(..., alias="totalCount")

    @classmethod
    def from_domain(
        cls,
        counts: OutboxDeliveryStatusCounts,
    ) -> "OutboxDeliveryStatusCountsResponse":
        return cls(
            pendingCount=counts.pending_count,
            leasedCount=counts.leased_count,
            failedCount=counts.failed_count,
            publishedCount=counts.published_count,
            deadLetterCount=counts.dead_letter_count,
            totalCount=counts.total_count,
        )


class OutboxDeliveryReadinessResponse(CamelModel):
    repository: str
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    external_broker_configured: bool = Field(..., alias="externalBrokerConfigured")
    external_broker_publisher_adapter_present: bool = Field(
        ..., alias="externalBrokerPublisherAdapterPresent"
    )
    delivery_ready_count: int = Field(..., alias="deliveryReadyCount")
    retry_deferred_count: int = Field(..., alias="retryDeferredCount")
    expired_lease_count: int = Field(..., alias="expiredLeaseCount")
    max_retry_count: int = Field(..., alias="maxRetryCount")
    status_counts: OutboxDeliveryStatusCountsResponse = Field(..., alias="statusCounts")
    source_of_truth: Mapping[str, str] = Field(..., alias="sourceOfTruth")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: OutboxDeliveryReadinessSnapshot,
    ) -> "OutboxDeliveryReadinessResponse":
        return cls(
            repository=snapshot.repository,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            durableStorageBacked=snapshot.durable_storage_backed,
            externalBrokerConfigured=snapshot.external_broker_configured,
            externalBrokerPublisherAdapterPresent=(
                snapshot.external_broker_publisher_adapter_present
            ),
            deliveryReadyCount=snapshot.delivery_ready_count,
            retryDeferredCount=snapshot.retry_deferred_count,
            expiredLeaseCount=snapshot.expired_lease_count,
            maxRetryCount=snapshot.max_retry_count,
            statusCounts=OutboxDeliveryStatusCountsResponse.from_domain(snapshot.status_counts),
            sourceOfTruth=dict(snapshot.source_of_truth),
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class OutboxDeliveryRunOnceResponse(CamelModel):
    repository: str
    run_status: str = Field(..., alias="runStatus")
    operator_run_reference: str = Field(..., alias="operatorRunReference")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    external_broker_configured: bool = Field(..., alias="externalBrokerConfigured")
    attempted_count: int = Field(..., alias="attemptedCount")
    published_count: int = Field(..., alias="publishedCount")
    failed_count: int = Field(..., alias="failedCount")
    dead_lettered_count: int = Field(..., alias="deadLetteredCount")
    skipped_count: int = Field(..., alias="skippedCount")
    max_retry_count: int = Field(..., alias="maxRetryCount")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def blocked(
        cls,
        *,
        durable_storage_backed: bool,
        blocker: str,
        max_retry_count: int,
        operator_run_reference: str = "unavailable",
    ) -> "OutboxDeliveryRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="blocked",
            operatorRunReference=operator_run_reference,
            supportabilityStatus="not_certified",
            durableStorageBacked=durable_storage_backed,
            externalBrokerConfigured=False,
            attemptedCount=0,
            publishedCount=0,
            failedCount=0,
            deadLetteredCount=0,
            skippedCount=0,
            maxRetryCount=max_retry_count,
            certificationBlockers=(
                blocker,
                *outbox_delivery_certification_blockers(),
            ),
            supportedFeaturePromoted=False,
        )

    @classmethod
    def from_domain(
        cls,
        summary: OutboxDeliveryRunSummary,
        *,
        durable_storage_backed: bool,
    ) -> "OutboxDeliveryRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus=summary.run_status.value,
            operatorRunReference=summary.operator_run_reference,
            supportabilityStatus="not_certified",
            durableStorageBacked=durable_storage_backed,
            externalBrokerConfigured=True,
            attemptedCount=summary.attempted_count,
            publishedCount=summary.published_count,
            failedCount=summary.failed_count,
            deadLetteredCount=summary.dead_lettered_count,
            skippedCount=summary.skipped_count,
            maxRetryCount=summary.max_retry_count,
            certificationBlockers=outbox_delivery_certification_blockers(),
            supportedFeaturePromoted=False,
        )


__all__ = [
    "OutboxDeliveryReadinessResponse",
    "OutboxDeliveryRunOnceResponse",
    "OutboxDeliveryStatusCountsResponse",
]
