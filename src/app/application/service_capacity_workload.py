from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
import math
import time
from typing import Callable, Mapping, Sequence

from app.application.service_capacity_baseline import CapacityMeasurement, SCENARIOS
from app.ports.capacity_probe import CapacityProbePort, CapacityProbeRequest, CapacityProbeResult
from app.ports.capacity_probe import PostgresCapacityProbePort


@dataclass(frozen=True)
class CapacityWorkloadPlan:
    scenario: str
    requests: tuple[CapacityProbeRequest, ...]
    max_concurrency: int
    item_count_field: str | None = None
    queue_age_field: str | None = None
    expected_source_failure_class: str | None = None
    recovery_probe: CapacityProbeRequest | None = None

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError("scenario must use the governed capacity vocabulary")
        if not self.requests:
            raise ValueError("capacity workload requests must not be empty")
        if self.max_concurrency <= 0 or self.max_concurrency > len(self.requests):
            raise ValueError("max_concurrency must be between one and request count")
        if (self.expected_source_failure_class is not None) != (
            self.scenario == "dependency_failure"
        ):
            raise ValueError("source failure class must match dependency_failure scenario")
        if self.expected_source_failure_class not in {None, "source_unavailable"}:
            raise ValueError("unsupported source failure class")
        if self.recovery_probe is not None and self.scenario != "dependency_failure":
            raise ValueError("recovery_probe is only valid for dependency_failure")


@dataclass(frozen=True)
class PostgresCapacityWorkloadResult:
    measurements: tuple[CapacityMeasurement, ...]
    max_connection_utilization_fraction: float | None


@dataclass(frozen=True)
class PacedCapacitySoakResult:
    measurements: tuple[CapacityMeasurement, ...]
    observed_window_seconds: float
    postgres_max_connection_utilization_fraction: float | None


STEADY_STATE_SCENARIOS = frozenset(
    {"api", "source_ingestion", "outbox_delivery", "downstream_submission"}
)


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


def execute_postgres_capacity_workload(
    *,
    probe: PostgresCapacityProbePort,
    request_count: int,
    max_concurrency: int,
) -> PostgresCapacityWorkloadResult:
    if request_count <= 0:
        raise ValueError("PostgreSQL request_count must be positive")
    if max_concurrency <= 0 or max_concurrency > request_count:
        raise ValueError("PostgreSQL max_concurrency must be between one and request count")
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        results = list(executor.map(lambda _: probe.execute(), range(request_count)))
    utilization_values = [
        result.connection_utilization_fraction
        for result in results
        if result.connection_utilization_fraction is not None
    ]
    return PostgresCapacityWorkloadResult(
        measurements=tuple(
            CapacityMeasurement(
                scenario="postgresql",
                duration_seconds=result.duration_seconds,
                outcome="accepted" if result.outcome == "accepted" else "failed",
            )
            for result in results
        ),
        max_connection_utilization_fraction=max(utilization_values, default=None),
    )


def execute_paced_capacity_soak(
    *,
    plans: Sequence[CapacityWorkloadPlan],
    http_probe: CapacityProbePort,
    postgres_probe: PostgresCapacityProbePort,
    postgres_request_count: int,
    minimum_observation_seconds: float,
    monotonic: Callable[[], float] = time.perf_counter,
    sleeper: Callable[[float], None] = time.sleep,
) -> PacedCapacitySoakResult:
    indexed = {plan.scenario: plan for plan in plans}
    if len(indexed) != len(plans) or set(indexed) != STEADY_STATE_SCENARIOS:
        raise ValueError("paced soak requires each governed steady-state HTTP scenario exactly once")
    if minimum_observation_seconds <= 0:
        raise ValueError("minimum_observation_seconds must be positive")
    request_counts = {len(plan.requests) for plan in plans}
    if len(request_counts) != 1:
        raise ValueError("paced soak HTTP scenarios must use the same request count")
    request_count = request_counts.pop()
    if postgres_request_count != request_count:
        raise ValueError("paced soak PostgreSQL and HTTP request counts must match")
    concurrency_values = {plan.max_concurrency for plan in plans}
    if len(concurrency_values) != 1:
        raise ValueError("paced soak HTTP scenarios must use the same concurrency")
    concurrency = concurrency_values.pop()
    rounds = math.ceil(request_count / concurrency)
    if rounds < 2:
        raise ValueError("paced soak requires at least two observation rounds")

    started_at = monotonic()
    measurements: list[CapacityMeasurement] = []
    postgres_remaining = postgres_request_count
    max_postgres_utilization: float | None = None
    for round_index in range(rounds):
        target_offset = minimum_observation_seconds * round_index / (rounds - 1)
        delay = target_offset - (monotonic() - started_at)
        if delay > 0:
            sleeper(delay)
        observed_offset = max(monotonic() - started_at, 0.0)
        for plan in plans:
            start = round_index * plan.max_concurrency
            requests = plan.requests[start : start + plan.max_concurrency]
            if not requests:
                continue
            batch = replace(plan, requests=requests, max_concurrency=len(requests))
            measurements.extend(
                replace(item, observed_offset_seconds=observed_offset)
                for item in execute_capacity_workload(batch, probe=http_probe)
            )
        postgres_batch_size = min(
            concurrency, postgres_remaining
        )
        if postgres_batch_size:
            postgres_result = execute_postgres_capacity_workload(
                probe=postgres_probe,
                request_count=postgres_batch_size,
                max_concurrency=postgres_batch_size,
            )
            measurements.extend(
                replace(item, observed_offset_seconds=observed_offset)
                for item in postgres_result.measurements
            )
            observed_utilization = postgres_result.max_connection_utilization_fraction
            if observed_utilization is not None:
                max_postgres_utilization = max(
                    max_postgres_utilization or 0.0, observed_utilization
                )
            postgres_remaining -= postgres_batch_size
    observed_window_seconds = monotonic() - started_at
    if observed_window_seconds < minimum_observation_seconds:
        raise ValueError("paced soak clock did not observe the minimum window")
    return PacedCapacitySoakResult(
        measurements=tuple(measurements),
        observed_window_seconds=observed_window_seconds,
        postgres_max_connection_utilization_fraction=max_postgres_utilization,
    )


def _measurement(
    plan: CapacityWorkloadPlan,
    result: CapacityProbeResult,
) -> CapacityMeasurement:
    summary = result.response_summary
    run_status = summary.get("runStatus")
    outcome = _measurement_outcome(
        transport_outcome=result.transport_outcome,
        run_status=run_status if isinstance(run_status, str) else None,
        response_summary=summary,
        expected_source_failure_class=plan.expected_source_failure_class,
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
    accepted = (
        result.transport_outcome == "accepted"
        and summary.get("runStatus") in {"completed", "replayed"}
        and _source_failure_counts(summary)
        == {
            "entitlement_denied": 0,
            "other_blocked": 0,
            "source_unavailable": 0,
        }
    )
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
    response_summary: Mapping[str, object],
    expected_source_failure_class: str | None,
) -> str:
    if transport_outcome == "timeout":
        return "timeout"
    if transport_outcome != "accepted":
        return "rejected"
    if run_status == "conflict":
        return "conflict"
    if expected_source_failure_class is not None:
        return (
            "accepted"
            if _is_expected_source_failure(
                response_summary, expected_source_failure_class=expected_source_failure_class
            )
            else "rejected"
        )
    if run_status == "blocked":
        return "rejected"
    return "accepted"


def _is_expected_source_failure(
    summary: Mapping[str, object], *, expected_source_failure_class: str
) -> bool:
    counts = _source_failure_counts(summary)
    if counts is not None:
        return (
            counts[expected_source_failure_class] > 0
            and sum(counts.values()) == counts[expected_source_failure_class]
        )
    expected_problem_code = {
        "source_unavailable": "source_dependency_unavailable",
    }[expected_source_failure_class]
    return summary.get("code") == expected_problem_code


def _source_failure_counts(summary: Mapping[str, object]) -> dict[str, int] | None:
    value = summary.get("sourceFailureCounts")
    expected = {"source_unavailable", "entitlement_denied", "other_blocked"}
    if not isinstance(value, dict) or set(value) != expected:
        return None
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in value.values()
    ):
        return None
    return {failure_class: value[failure_class] for failure_class in sorted(expected)}


def _bounded_int(value: object, *, default: int) -> int:
    return (
        value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default
    )


def _summary_value(summary: Mapping[str, object], key: str | None) -> object:
    return None if key is None else summary.get(key)


def _bounded_float(measurement: object) -> float | None:
    if (
        isinstance(measurement, bool)
        or not isinstance(measurement, (int, float))
        or measurement < 0
    ):
        return None
    return float(measurement)
