from __future__ import annotations

from dataclasses import replace

from app.application.outbox_delivery_readiness import (
    OutboxDeliveryReadinessSnapshot,
    OutboxDeliveryStatusCounts,
)
from app.application.outbox_supportability_alerts import (
    OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS,
    OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD,
    OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD,
    evaluate_outbox_supportability_alert_posture,
)


def test_outbox_supportability_alerts_remain_quiet_at_thresholds() -> None:
    snapshot = readiness_snapshot(
        delivery_ready_count=OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD,
        retry_deferred_count=OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD,
        oldest_delivery_ready_age_seconds=OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS,
    )

    posture = evaluate_outbox_supportability_alert_posture(snapshot)

    assert posture.healthy is True


def test_outbox_supportability_alerts_detect_each_runtime_failure_family() -> None:
    baseline = readiness_snapshot()

    assert (
        evaluate_outbox_supportability_alert_posture(
            replace(
                baseline,
                status_counts=replace(baseline.status_counts, dead_letter_count=1),
            )
        ).dead_letter_present
        is True
    )
    assert (
        evaluate_outbox_supportability_alert_posture(
            replace(baseline, expired_lease_count=1)
        ).expired_lease_present
        is True
    )
    assert (
        evaluate_outbox_supportability_alert_posture(
            replace(
                baseline,
                delivery_ready_count=OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD + 1,
            )
        ).delivery_backlog_stalled
        is True
    )
    assert (
        evaluate_outbox_supportability_alert_posture(
            replace(
                baseline,
                oldest_delivery_ready_age_seconds=(
                    OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS + 1
                ),
            )
        ).delivery_backlog_stalled
        is True
    )
    assert (
        evaluate_outbox_supportability_alert_posture(
            replace(
                baseline,
                retry_deferred_count=OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD + 1,
            )
        ).retry_pressure
        is True
    )


def readiness_snapshot(
    *,
    delivery_ready_count: int = 0,
    retry_deferred_count: int = 0,
    oldest_delivery_ready_age_seconds: float = 0,
) -> OutboxDeliveryReadinessSnapshot:
    return OutboxDeliveryReadinessSnapshot(
        repository="lotus-idea",
        readiness_status="blocked",
        supportability_status="not_certified",
        certification_ready=False,
        durable_storage_backed=True,
        external_broker_configured=True,
        external_broker_publisher_adapter_present=True,
        delivery_ready_count=delivery_ready_count,
        retry_deferred_count=retry_deferred_count,
        expired_lease_count=0,
        oldest_delivery_ready_age_seconds=oldest_delivery_ready_age_seconds,
        max_retry_count=3,
        status_counts=OutboxDeliveryStatusCounts(
            pending_count=0,
            leased_count=0,
            failed_count=0,
            published_count=0,
            dead_letter_count=0,
        ),
        source_of_truth={},
        configuration_blockers=(),
        certification_blockers=("external_broker_runtime_proof_missing",),
        supported_feature_promoted=False,
    )
