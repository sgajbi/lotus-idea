from __future__ import annotations

import pytest

from app.domain.capacity_posture import (
    CapacityPosture,
    PostgresCapacityPosture,
    decide_nonessential_workload_capacity,
    evaluate_postgres_capacity_posture,
)


@pytest.mark.parametrize(
    ("utilization", "expected"),
    [
        (0.0, CapacityPosture.NORMAL),
        (0.6999, CapacityPosture.NORMAL),
        (0.7, CapacityPosture.WARNING),
        (0.8999, CapacityPosture.WARNING),
        (0.9, CapacityPosture.SHED),
        (1.0, CapacityPosture.SHED),
        (None, CapacityPosture.UNAVAILABLE),
    ],
)
def test_capacity_posture_uses_exact_code_owned_thresholds(
    utilization: float | None,
    expected: CapacityPosture,
) -> None:
    posture = evaluate_postgres_capacity_posture(utilization)

    assert posture.posture is expected
    assert posture.connection_utilization_fraction == utilization
    assert posture.collection_succeeded is (utilization is not None)


@pytest.mark.parametrize(
    ("posture", "allowed", "blocker"),
    [
        (CapacityPosture.NORMAL, True, None),
        (CapacityPosture.WARNING, True, None),
        (CapacityPosture.SHED, False, "postgres_capacity_shed_active"),
        (CapacityPosture.UNAVAILABLE, False, "postgres_capacity_posture_unavailable"),
    ],
)
def test_nonessential_workload_policy_preserves_warning_and_fails_closed(
    posture: CapacityPosture,
    allowed: bool,
    blocker: str | None,
) -> None:
    snapshot = PostgresCapacityPosture(
        posture=posture,
        connection_utilization_fraction=(None if posture is CapacityPosture.UNAVAILABLE else 0.5),
        collection_succeeded=posture is not CapacityPosture.UNAVAILABLE,
    )

    decision = decide_nonessential_workload_capacity(snapshot)

    assert decision.allowed is allowed
    assert decision.posture is posture
    assert decision.blocker == blocker


@pytest.mark.parametrize(
    ("utilization", "collected", "message"),
    [
        (-0.01, True, "between zero and one"),
        (1.01, True, "between zero and one"),
        (None, True, "must match utilization availability"),
        (0.5, False, "must match utilization availability"),
    ],
)
def test_capacity_posture_rejects_inconsistent_or_out_of_range_snapshots(
    utilization: float | None,
    collected: bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PostgresCapacityPosture(
            posture=CapacityPosture.NORMAL,
            connection_utilization_fraction=utilization,
            collection_succeeded=collected,
        )
