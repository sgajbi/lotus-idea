from __future__ import annotations

from collections import deque

import pytest

from app.application.service_capacity_workload import (
    CapacityWorkloadPlan,
    execute_capacity_recovery,
    execute_capacity_workload,
    execute_postgres_capacity_workload,
)
from app.ports.capacity_probe import (
    CapacityProbeRequest,
    CapacityProbeResult,
    PostgresCapacityProbeResult,
)


REQUEST = CapacityProbeRequest(
    method="POST",
    path="/run-once",
    headers={},
    expected_status_codes=frozenset({200}),
)


class StubProbe:
    def __init__(self, results: list[CapacityProbeResult]) -> None:
        self.results = deque(results)

    def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult:
        return self.results.popleft()

    def close(self) -> None:
        pass


class StubPostgresProbe:
    def __init__(self, results: list[PostgresCapacityProbeResult]) -> None:
        self.results = deque(results)

    def execute(self) -> PostgresCapacityProbeResult:
        return self.results.popleft()


def _result(
    *,
    transport_outcome: str = "accepted",
    summary: dict[str, object] | None = None,
) -> CapacityProbeResult:
    return CapacityProbeResult(
        duration_seconds=0.25,
        status_code=200,
        transport_outcome=transport_outcome,
        response_summary=summary or {},
    )


def test_maps_workflow_counts_queue_age_and_blocked_semantics() -> None:
    probe = StubProbe(
        [
            _result(
                summary={
                    "runStatus": "completed",
                    "attemptedCount": 100,
                    "oldestDeliveryReadyAgeSeconds": 12.5,
                    "maxRetryCount": 3,
                }
            ),
            _result(summary={"runStatus": "blocked", "attemptedCount": 0}),
        ]
    )
    plan = CapacityWorkloadPlan(
        scenario="outbox_delivery",
        requests=(REQUEST, REQUEST),
        max_concurrency=1,
        item_count_field="attemptedCount",
        queue_age_field="oldestDeliveryReadyAgeSeconds",
    )

    measurements = execute_capacity_workload(plan, probe=probe)

    assert measurements[0].outcome == "accepted"
    assert measurements[0].item_count == 100
    assert measurements[0].queue_age_seconds == 12.5
    assert measurements[0].retry_count == 3
    assert measurements[1].outcome == "rejected"
    assert measurements[1].item_count == 0


def test_dependency_failure_and_recovery_are_measured_separately() -> None:
    probe = StubProbe(
        [
            _result(transport_outcome="rejected"),
            _result(summary={"runStatus": "blocked"}),
            _result(summary={"runStatus": "completed", "totalCount": 100}),
        ]
    )
    plan = CapacityWorkloadPlan(
        scenario="dependency_failure",
        requests=(REQUEST, REQUEST),
        max_concurrency=1,
        dependency_failure_expected=True,
        recovery_probe=REQUEST,
        item_count_field="totalCount",
    )

    measurements = execute_capacity_workload(plan, probe=probe)

    assert [item.outcome for item in measurements] == ["rejected", "accepted", "accepted"]
    assert [item.recovered for item in measurements] == [None, None, True]
    assert measurements[-1].item_count == 100


def test_failed_recovery_is_not_misrepresented() -> None:
    probe = StubProbe(
        [_result(transport_outcome="rejected"), _result(summary={"runStatus": "blocked"})]
    )
    plan = CapacityWorkloadPlan(
        scenario="dependency_failure",
        requests=(REQUEST,),
        max_concurrency=1,
        dependency_failure_expected=True,
        recovery_probe=REQUEST,
    )

    measurements = execute_capacity_workload(plan, probe=probe)

    assert measurements[-1].outcome == "failed"
    assert measurements[-1].recovered is False


def test_recovery_use_case_requires_explicit_dependency_recovery_probe() -> None:
    plan = CapacityWorkloadPlan(
        scenario="api",
        requests=(REQUEST,),
        max_concurrency=1,
    )

    with pytest.raises(ValueError, match="requires a dependency_failure recovery probe"):
        execute_capacity_recovery(plan, probe=StubProbe([]))


def test_explicit_recovery_use_case_executes_only_recovery_probe() -> None:
    plan = CapacityWorkloadPlan(
        scenario="dependency_failure",
        requests=(REQUEST,),
        max_concurrency=1,
        dependency_failure_expected=True,
        recovery_probe=REQUEST,
    )

    measurement = execute_capacity_recovery(
        plan,
        probe=StubProbe([_result(summary={"runStatus": "completed"})]),
    )

    assert measurement.outcome == "accepted"
    assert measurement.recovered is True


def test_postgres_workload_preserves_query_outcomes_and_max_observed_utilization() -> None:
    result = execute_postgres_capacity_workload(
        probe=StubPostgresProbe(
            [
                PostgresCapacityProbeResult(0.01, "accepted", 0.2),
                PostgresCapacityProbeResult(0.02, "failed", None),
                PostgresCapacityProbeResult(0.03, "accepted", 0.3),
            ]
        ),
        request_count=3,
        max_concurrency=1,
    )

    assert [item.outcome for item in result.measurements] == ["accepted", "failed", "accepted"]
    assert result.max_connection_utilization_fraction == 0.3


@pytest.mark.parametrize(
    ("request_count", "max_concurrency", "message"),
    [
        (0, 1, "request_count must be positive"),
        (1, 0, "max_concurrency must be between"),
        (1, 2, "max_concurrency must be between"),
    ],
)
def test_postgres_workload_rejects_invalid_volume_or_concurrency(
    request_count: int,
    max_concurrency: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        execute_postgres_capacity_workload(
            probe=StubPostgresProbe([]),
            request_count=request_count,
            max_concurrency=max_concurrency,
        )


def test_workload_preserves_timeout_and_conflict_outcomes() -> None:
    plan = CapacityWorkloadPlan(
        scenario="outbox_delivery",
        requests=(REQUEST, REQUEST),
        max_concurrency=1,
    )

    measurements = execute_capacity_workload(
        plan,
        probe=StubProbe(
            [
                _result(transport_outcome="timeout"),
                _result(summary={"runStatus": "conflict"}),
            ]
        ),
    )

    assert [item.outcome for item in measurements] == ["timeout", "conflict"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scenario": "unknown"}, "scenario must use"),
        ({"requests": ()}, "requests must not be empty"),
        ({"max_concurrency": 0}, "max_concurrency must be between"),
        ({"max_concurrency": 2}, "max_concurrency must be between"),
        ({"scenario": "dependency_failure"}, "dependency failure posture must match"),
        ({"recovery_probe": REQUEST}, "recovery_probe is only valid"),
    ],
)
def test_plan_fails_closed_on_invalid_scenario_or_concurrency(
    kwargs: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "scenario": "api",
        "requests": (REQUEST,),
        "max_concurrency": 1,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        CapacityWorkloadPlan(**values)  # type: ignore[arg-type]
