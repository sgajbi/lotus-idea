from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Mapping

from app.application.service_capacity_baseline import build_service_capacity_baseline
from app.application.service_capacity_workload import (
    CapacityWorkloadPlan,
    execute_capacity_recovery,
    execute_capacity_workload,
    execute_postgres_capacity_workload,
)
from app.infrastructure.http_capacity_probe import HttpCapacityProbe
from app.infrastructure.github_capacity_attestation import GitHubCapacityAttestationVerifier
from app.infrastructure.postgres_capacity_probe import PostgresCapacityProbe
from app.ports.capacity_probe import CapacityProbeRequest


SCENARIO_CHOICES = (
    "api",
    "source_ingestion",
    "outbox_delivery",
    "dependency_failure",
    "postgresql",
)
MUTATING_SCENARIOS = frozenset({"source_ingestion", "outbox_delivery", "dependency_failure"})
HEADER_ENV = {
    "Authorization": "LOTUS_IDEA_CAPACITY_AUTHORIZATION",
    "X-Lotus-Trusted-Caller-Context": "LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT",
}
OUTPUT_ENV = "LOTUS_IDEA_SERVICE_CAPACITY_BASELINE"


def build_workload_plans(
    *,
    scenarios: tuple[str, ...],
    request_count: int,
    concurrency: int,
    environment_profile: str,
    allow_mutating_workflows: bool,
    allow_production_mutations: bool,
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
        )
        for scenario in scenarios
        if scenario != "postgresql"
    ]


def _plan(
    *,
    scenario: str,
    request_count: int,
    concurrency: int,
    headers: Mapping[str, str],
) -> CapacityWorkloadPlan:
    if scenario == "api":
        request = _request("GET", "/health/ready", headers, {200})
        return CapacityWorkloadPlan(scenario, (request,) * request_count, concurrency)
    if scenario == "source_ingestion":
        workflow_headers = _workflow_headers(headers, "idea.source-ingestion.run")
        request = _request(
            "POST",
            "/api/v1/source-ingestion/run-once",
            workflow_headers,
            {200},
        )
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
    workflow_headers = _workflow_headers(headers, "idea.source-ingestion.run")
    fault_request = _request(
        "POST",
        "/api/v1/source-ingestion/run-once",
        workflow_headers,
        {200, 502, 503},
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
        dependency_failure_expected=True,
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded Lotus Idea HTTP capacity scenarios and publish source-safe evidence."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--environment-profile",
        required=True,
        choices=("test", "production-like", "production"),
    )
    parser.add_argument("--scenario", action="append", choices=SCENARIO_CHOICES, required=True)
    parser.add_argument("--request-count", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--dependency-recovery-delay-seconds", type=float, default=0.0)
    parser.add_argument("--allow-mutating-workflows", action="store_true")
    parser.add_argument("--allow-production-mutations", action="store_true")
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--postgres-threshold-proof", type=Path)
    parser.add_argument("--verify-postgres-threshold-attestation", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.getenv(OUTPUT_ENV, "output/observability/service-capacity-baseline.json")),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    probe: HttpCapacityProbe | None = None
    try:
        plans = build_workload_plans(
            scenarios=tuple(args.scenario),
            request_count=args.request_count,
            concurrency=args.concurrency,
            environment_profile=args.environment_profile,
            allow_mutating_workflows=args.allow_mutating_workflows,
            allow_production_mutations=args.allow_production_mutations,
        )
        if args.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if args.dependency_recovery_delay_seconds < 0:
            raise ValueError("dependency_recovery_delay_seconds must not be negative")
        probe = HttpCapacityProbe(base_url=args.base_url, timeout_seconds=args.timeout_seconds)
        started_at = time.perf_counter()
        measurements = []
        postgres_max_utilization = None
        for plan in plans:
            if plan.scenario == "dependency_failure" and args.dependency_recovery_delay_seconds:
                fault_only = CapacityWorkloadPlan(
                    scenario=plan.scenario,
                    requests=plan.requests,
                    max_concurrency=plan.max_concurrency,
                    item_count_field=plan.item_count_field,
                    dependency_failure_expected=True,
                )
                measurements.extend(execute_capacity_workload(fault_only, probe=probe))
                time.sleep(args.dependency_recovery_delay_seconds)
                measurements.append(execute_capacity_recovery(plan, probe=probe))
            else:
                measurements.extend(execute_capacity_workload(plan, probe=probe))
        if "postgresql" in args.scenario:
            database_url = os.getenv("LOTUS_IDEA_DATABASE_URL", "").strip()
            if not database_url:
                raise ValueError("LOTUS_IDEA_DATABASE_URL is required for the postgresql scenario")
            postgres_result = execute_postgres_capacity_workload(
                probe=PostgresCapacityProbe(database_url=database_url),
                request_count=args.request_count,
                max_concurrency=args.concurrency,
            )
            measurements.extend(postgres_result.measurements)
            postgres_max_utilization = postgres_result.max_connection_utilization_fraction
        observed_window_seconds = max(time.perf_counter() - started_at, 0.000001)
        threshold_proof = _read_optional_proof(args.postgres_threshold_proof)
        threshold_attestation = None
        if args.verify_postgres_threshold_attestation:
            if args.postgres_threshold_proof is None or threshold_proof is None:
                raise ValueError("attestation verification requires --postgres-threshold-proof")
            if args.environment_profile != "production-like":
                raise ValueError("attested capacity qualification requires production-like profile")
            proof_commit = threshold_proof.get("commitSha")
            if not isinstance(proof_commit, str) or not proof_commit.strip():
                raise ValueError("PostgreSQL threshold proof commitSha must be a non-blank string")
            threshold_attestation = GitHubCapacityAttestationVerifier().verify(
                artifact_path=args.postgres_threshold_proof,
                source_commit_sha=proof_commit,
            )
        artifact = build_service_capacity_baseline(
            measurements=measurements,
            environment_profile=args.environment_profile,
            generated_at_utc=datetime.now(UTC),
            commit_sha=args.commit_sha,
            branch=args.branch,
            run_id=args.run_id,
            observed_window_seconds=observed_window_seconds,
            postgres_threshold_proof=threshold_proof,
            postgres_threshold_attestation=threshold_attestation,
            postgres_max_connection_utilization_fraction=postgres_max_utilization,
        )
        _write_json_atomic(args.output, artifact)
        return 0
    except (OSError, ValueError) as exc:
        print(f"service capacity workload failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if probe is not None:
            probe.close()


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_optional_proof(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PostgreSQL threshold proof must be a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
