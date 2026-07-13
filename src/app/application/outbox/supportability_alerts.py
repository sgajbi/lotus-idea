from __future__ import annotations

from dataclasses import dataclass

from app.application.outbox.readiness import OutboxDeliveryReadinessSnapshot

OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD = 100
OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS = 900
OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD = 50


@dataclass(frozen=True)
class OutboxSupportabilityAlertPosture:
    dead_letter_present: bool
    expired_lease_present: bool
    delivery_backlog_stalled: bool
    retry_pressure: bool

    @property
    def healthy(self) -> bool:
        return not any(
            (
                self.dead_letter_present,
                self.expired_lease_present,
                self.delivery_backlog_stalled,
                self.retry_pressure,
            )
        )


def evaluate_outbox_supportability_alert_posture(
    snapshot: OutboxDeliveryReadinessSnapshot,
) -> OutboxSupportabilityAlertPosture:
    return OutboxSupportabilityAlertPosture(
        dead_letter_present=snapshot.status_counts.dead_letter_count > 0,
        expired_lease_present=snapshot.expired_lease_count > 0,
        delivery_backlog_stalled=(
            snapshot.delivery_ready_count > OUTBOX_DELIVERY_READY_COUNT_ALERT_THRESHOLD
            or snapshot.oldest_delivery_ready_age_seconds
            > OUTBOX_DELIVERY_OLDEST_READY_AGE_ALERT_SECONDS
        ),
        retry_pressure=(
            snapshot.retry_deferred_count > OUTBOX_DELIVERY_RETRY_DEFERRED_ALERT_THRESHOLD
        ),
    )
