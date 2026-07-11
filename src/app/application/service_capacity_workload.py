from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Mapping

from app.application.service_capacity_baseline import CapacityMeasurement, SCENARIOS
from app.ports.capacity_probe import CapacityProbePort, CapacityProbeRequest, CapacityProbeResult


@dataclass(frozen=True)
class CapacityWorkloadPlan:
    scenario: str
    requests: tuple[CapacityProbeRequest, ...]
    max_concurrency: int
    item_count_field: str | None = None
    queue_age_field: str | None = None
    dependency_failure_expected: bool = False
    recovery_probe: CapacityProbeRequest | None = None

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError("scenario must use the governed capacity vocabulary")
        if not self.requests:
            raise ValueError("capacity workload requests must not be empty")
        if self.max_concurrency <= 0 or self.max_concurrency > len(self.requests):
            raise ValueError("max_concurrency must be between one and request count")
        if self.dependency_failure_expected != (self.scenario == "dependency_failure"):
            raise ValueError("dependency failure posture must match dependency_failure scenario")
        if self.recovery_probe is not None and self.scenario != "dependency_failure":
            raise ValueError("recovery_probe is only valid for dependency_failure")


def execute_capacity_workload(
    plan: CapacityWorkloadPlan,
    *,
    probe: CapacityProbePort,
) -> list[CapacityMeasurement]:
    with ThreadPoolExecutor(max_workers=plan.max_concurrency) as executor:
        results = list(executor.map(probe.execute, plan.requests))
    measurements = [_measurement(plan, result) for result in results]
    if plan.recovery_probe is not None:
        recovery = probe.execute(plan.recovery_probe)
        measurements.append(_recovery_measurement(plan, recovery))
    return measurements


def execute_capacity_recovery(
    plan: CapacityWorkloadPlan,
    *,
    probe: CapacityProbePort,
) -> CapacityMeasurement:
    if plan.scenario != "dependency_failure" or plan.recovery_probe is None:
        raise ValueError("capacity recovery requires a dependency_failure recovery probe")
    return _recovery_measurement(plan, probe.execute(plan.recovery_probe))


def _measurement(
    plan: CapacityWorkloadPlan,
    result: CapacityProbeResult,
) -> CapacityMeasurement:
    summary = result.response_summary
    run_status = summary.get("runStatus")
    outcome = _measurement_outcome(
        transport_outcome=result.transport_outcome,
        run_status=run_status if isinstance(run_status, str) else None,
        dependency_failure_expected=plan.dependency_failure_expected,
    )
    return CapacityMeasurement(
        scenario=plan.scenario,
        duration_seconds=result.duration_seconds,
        outcome=outcome,
        item_count=_bounded_int(_summary_value(summary, plan.item_count_field), default=1),
        queue_age_seconds=_bounded_float(_summary_value(summary, plan.queue_age_field)),
        retry_count=_bounded_int(summary.get("maxRetryCount"), default=0),
        recovered=None,
    )


def _recovery_measurement(
    plan: CapacityWorkloadPlan,
    result: CapacityProbeResult,
) -> CapacityMeasurement:
    summary = result.response_summary
    accepted = result.transport_outcome == "accepted" and summary.get("runStatus") not in {
        "blocked",
        "conflict",
    }
    return CapacityMeasurement(
        scenario=plan.scenario,
        duration_seconds=result.duration_seconds,
        outcome="accepted" if accepted else "failed",
        item_count=_bounded_int(_summary_value(summary, plan.item_count_field), default=1),
        retry_count=_bounded_int(summary.get("maxRetryCount"), default=0),
        recovered=accepted,
    )


def _measurement_outcome(
    *,
    transport_outcome: str,
    run_status: str | None,
    dependency_failure_expected: bool,
) -> str:
    if transport_outcome == "timeout":
        return "timeout"
    if transport_outcome != "accepted":
        return "accepted" if dependency_failure_expected else "rejected"
    if run_status == "conflict":
        return "conflict"
    if run_status == "blocked":
        return "accepted" if dependency_failure_expected else "rejected"
    return "accepted"


def _bounded_int(value: object, *, default: int) -> int:
    return (
        value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default
    )


def _summary_value(summary: Mapping[str, object], key: str | None) -> object:
    return None if key is None else summary.get(key)


def _bounded_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return float(value)
