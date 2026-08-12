from __future__ import annotations

import os
import re
import secrets
from typing import Mapping

from app.application.capacity_evidence_qualification import (
    MINIMUM_LOAD_SOAK_SAMPLES,
    MINIMUM_LOAD_SOAK_SECONDS,
)
from app.application.service_capacity_baseline import SCENARIOS
from app.application.service_capacity_workload import (
    CapacityWorkloadPlan,
    STEADY_STATE_SCENARIOS,
)
from app.ports.capacity_probe import CapacityProbeRequest


SCENARIO_CHOICES = SCENARIOS
MUTATING_SCENARIOS = frozenset(
    {"source_ingestion", "outbox_delivery", "downstream_submission", "dependency_failure"}
)
DOWNSTREAM_PATH_ENV = "LOTUS_IDEA_CAPACITY_DOWNSTREAM_PATH"
DOWNSTREAM_PATH_PATTERN = re.compile(
    r"^/api/v1/(?:conversion-intents|report-evidence-packs)/[A-Za-z0-9._-]{1,100}/"
    r"downstream-submissions$"
)
HEADER_ENV = {
    "Authorization": "LOTUS_IDEA_CAPACITY_AUTHORIZATION",
    "X-Lotus-Trusted-Caller-Context": "LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT",
}


def build_workload_plans(
    *,
    scenarios: tuple[str, ...],
    request_count: int,
    concurrency: int,
    environment_profile: str,
    allow_mutating_workflows: bool,
    allow_production_mutations: bool,
    downstream_submission_path: str | None = None,
) -> list[CapacityWorkloadPlan]:
    if not scenarios:
        raise ValueError("at least one scenario is required")
    if any(scenario not in SCENARIO_CHOICES for scenario in scenarios):
        raise ValueError("scenario must use the governed workload vocabulary")
    if len(set(scenarios)) != len(scenarios):
        raise ValueError("scenarios must not contain duplicates")
    if request_count <= 0 or request_count > 10_000:
        raise ValueError("request_count must be between 1 and 10000")
    if concurrency <= 0 or concurrency > request_count or concurrency > 100:
        raise ValueError("concurrency must be between 1 and min(request_count, 100)")
    mutating = MUTATING_SCENARIOS.intersection(scenarios)
    if mutating and not allow_mutating_workflows:
        raise ValueError("mutating scenarios require --allow-mutating-workflows")
    if mutating and environment_profile == "production" and not allow_production_mutations:
        raise ValueError("production mutations require --allow-production-mutations")

    headers = _base_headers()
    return [
        _plan(
            scenario=scenario,
            request_count=request_count,
            concurrency=concurrency,
            headers=headers,
            downstream_submission_path=downstream_submission_path,
        )
        for scenario in scenarios
        if scenario != "postgresql"
    ]


def validate_paced_load_soak_request(
    *,
    scenarios: tuple[str, ...],
    environment_profile: str,
    request_count: int,
    minimum_observation_seconds: float,
) -> None:
    expected = {*STEADY_STATE_SCENARIOS, "postgresql"}
    if set(scenarios) != expected or len(scenarios) != len(expected):
        raise ValueError("paced load soak requires all five steady-state scenarios exactly once")
    if environment_profile != "production-like":
        raise ValueError("paced load soak requires the production-like environment profile")
    if request_count < MINIMUM_LOAD_SOAK_SAMPLES:
        raise ValueError("paced load soak does not meet the minimum sample count")
    if minimum_observation_seconds < MINIMUM_LOAD_SOAK_SECONDS:
        raise ValueError("paced load soak does not meet the minimum observation window")


def downstream_submission_path(
    *,
    seed: dict[str, object] | None,
    commit_sha: str,
    branch: str,
    environment_path: str | None,
) -> str | None:
    if seed is None:
        return environment_path
    required = {
        "schemaVersion": "lotus-idea.downstream-capacity-seed.v1",
        "proofScope": "synthetic_downstream_capacity_resource_seed",
        "claimPosture": "seed_only_not_capacity_evidence",
        "syntheticResource": True,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
        "commitSha": commit_sha,
        "branch": branch,
    }
    if any(seed.get(key) != expected for key, expected in required.items()):
        raise ValueError("downstream capacity seed provenance is invalid")
    path = seed.get("downstreamSubmissionPath")
    if not isinstance(path, str) or not DOWNSTREAM_PATH_PATTERN.fullmatch(path):
        raise ValueError("downstream capacity seed path is invalid")
    return path


def _plan(
    *,
    scenario: str,
    request_count: int,
    concurrency: int,
    headers: Mapping[str, str],
    downstream_submission_path: str | None,
) -> CapacityWorkloadPlan:
    if scenario == "api":
        request = _request("GET", "/health/ready", headers, {200})
        return CapacityWorkloadPlan(scenario, (request,) * request_count, concurrency)
    if scenario == "source_ingestion":
        workflow_headers = _workflow_headers(headers, "idea.source-ingestion.run")
        request = _request("POST", "/api/v1/source-ingestion/run-once", workflow_headers, {200})
        return CapacityWorkloadPlan(
            scenario,
            (request,) * request_count,
            concurrency,
            item_count_field="totalCount",
        )
    if scenario == "outbox_delivery":
        workflow_headers = _workflow_headers(headers, "idea.outbox-delivery.run")
        requests = tuple(
            _request(
                "POST",
                "/api/v1/outbox-delivery/run-once?limit=100&maxRetryCount=3",
                {**workflow_headers, "Idempotency-Key": f"capacity-{secrets.token_hex(16)}"},
                {200},
            )
            for _ in range(request_count)
        )
        return CapacityWorkloadPlan(
            scenario,
            requests,
            concurrency,
            item_count_field="attemptedCount",
        )
    if scenario == "downstream_submission":
        if downstream_submission_path is None or not DOWNSTREAM_PATH_PATTERN.fullmatch(
            downstream_submission_path
        ):
            raise ValueError(
                "downstream_submission requires a governed pre-seeded synthetic resource path"
            )
        workflow_headers = _workflow_headers(headers, "idea.downstream-realization.submit")
        requests = tuple(
            _request(
                "POST",
                downstream_submission_path,
                {**workflow_headers, "Idempotency-Key": f"capacity-{secrets.token_hex(16)}"},
                {200},
            )
            for _ in range(request_count)
        )
        return CapacityWorkloadPlan(scenario, requests, concurrency)

    workflow_headers = _workflow_headers(headers, "idea.source-ingestion.run")
    fault_request = _request(
        "POST",
        "/api/v1/source-ingestion/run-once",
        workflow_headers,
        {200, 502},
    )
    recovery_request = _request(
        "POST",
        "/api/v1/source-ingestion/run-once",
        workflow_headers,
        {200},
    )
    return CapacityWorkloadPlan(
        scenario,
        (fault_request,) * request_count,
        concurrency,
        item_count_field="totalCount",
        expected_source_failure_class="source_unavailable",
        recovery_probe=recovery_request,
    )


def _base_headers() -> dict[str, str]:
    return {
        header: value
        for header, env_name in HEADER_ENV.items()
        if (value := os.getenv(env_name, "").strip())
    }


def _workflow_headers(headers: Mapping[str, str], capability: str) -> dict[str, str]:
    return {
        **headers,
        "X-Caller-Subject": "capacity-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": capability,
    }


def _request(
    method: str,
    path: str,
    headers: Mapping[str, str],
    expected_status_codes: set[int],
) -> CapacityProbeRequest:
    return CapacityProbeRequest(
        method=method,
        path=path,
        headers=dict(headers),
        expected_status_codes=frozenset(expected_status_codes),
    )
