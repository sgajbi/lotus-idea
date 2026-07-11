from __future__ import annotations

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Mapping

from app.application.service_capacity_baseline import (
    CapacityMeasurement,
    SCENARIOS,
    build_service_capacity_baseline,
)
from app.application.capacity_evidence_qualification import (
    DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    LOAD_SOAK_SIGNER_WORKFLOW,
    POSTGRES_CAPACITY_SIGNER_WORKFLOW,
    RESOURCE_SIGNER_WORKFLOW,
    VerifiedArtifactAttestation,
    MINIMUM_LOAD_SOAK_SAMPLES,
    MINIMUM_LOAD_SOAK_SECONDS,
)
from app.application.service_capacity_workload import (
    CapacityWorkloadPlan,
    STEADY_STATE_SCENARIOS,
    execute_capacity_recovery,
    execute_capacity_workload,
    execute_paced_capacity_soak,
    execute_postgres_capacity_workload,
)
from app.infrastructure.http_capacity_probe import HttpCapacityProbe
from app.infrastructure.github_capacity_attestation import GitHubCapacityAttestationVerifier
from app.infrastructure.capacity_artifact_io import (
    read_optional_capacity_proof as _read_optional_proof,
    read_optional_json_object as _read_optional_json_object,
    read_optional_resource_baseline as _read_optional_resource_baseline,
    write_json_atomic as _write_json_atomic,
)
from app.infrastructure.postgres_capacity_probe import PostgresCapacityProbe
from app.infrastructure.service_capacity_workload_inputs import (
    required_database_url,
    verify_optional_cost_attribution_attestation,
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
OUTPUT_ENV = "LOTUS_IDEA_SERVICE_CAPACITY_BASELINE"


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
    parser.add_argument("--paced-load-soak", action="store_true")
    parser.add_argument(
        "--minimum-observation-seconds",
        type=float,
        default=MINIMUM_LOAD_SOAK_SECONDS,
    )
    parser.add_argument("--allow-mutating-workflows", action="store_true")
    parser.add_argument("--allow-production-mutations", action="store_true")
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--postgres-threshold-proof", type=Path)
    parser.add_argument("--dependency-recovery-proof", type=Path)
    parser.add_argument("--load-soak-proof", type=Path)
    parser.add_argument("--downstream-capacity-seed", type=Path)
    parser.add_argument("--resource-baseline", type=Path)
    parser.add_argument("--cost-attribution-artifact", type=Path)
    parser.add_argument("--verify-postgres-threshold-attestation", action="store_true")
    parser.add_argument("--verify-dependency-recovery-attestation", action="store_true")
    parser.add_argument("--verify-load-soak-attestation", action="store_true")
    parser.add_argument("--verify-resource-attestation", action="store_true")
    parser.add_argument("--verify-cost-attribution-attestation", action="store_true")
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
        downstream_capacity_seed = _read_optional_json_object(
            args.downstream_capacity_seed, name="downstream capacity seed"
        )
        plans = build_workload_plans(
            scenarios=tuple(args.scenario),
            request_count=args.request_count,
            concurrency=args.concurrency,
            environment_profile=args.environment_profile,
            allow_mutating_workflows=args.allow_mutating_workflows,
            allow_production_mutations=args.allow_production_mutations,
            downstream_submission_path=_downstream_submission_path(
                seed=downstream_capacity_seed,
                commit_sha=args.commit_sha,
                branch=args.branch,
                environment_path=os.getenv(DOWNSTREAM_PATH_ENV, "").strip() or None,
            ),
        )
        if args.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if args.dependency_recovery_delay_seconds < 0:
            raise ValueError("dependency_recovery_delay_seconds must not be negative")
        probe = HttpCapacityProbe(base_url=args.base_url, timeout_seconds=args.timeout_seconds)
        measurements, observed_window_seconds, postgres_max_utilization = _execute_measurements(
            args=args, plans=plans, probe=probe
        )
        threshold_proof = _read_optional_proof(args.postgres_threshold_proof)
        threshold_attestation = _verify_optional_attestation(
            verification_requested=args.verify_postgres_threshold_attestation,
            artifact_path=args.postgres_threshold_proof,
            proof=threshold_proof,
            environment_profile=args.environment_profile,
            signer_workflow=POSTGRES_CAPACITY_SIGNER_WORKFLOW,
            proof_name="PostgreSQL threshold proof",
        )
        dependency_recovery_proof = _read_optional_proof(args.dependency_recovery_proof)
        dependency_recovery_attestation = _verify_optional_attestation(
            verification_requested=args.verify_dependency_recovery_attestation,
            artifact_path=args.dependency_recovery_proof,
            proof=dependency_recovery_proof,
            environment_profile=args.environment_profile,
            signer_workflow=DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
            proof_name="dependency recovery proof",
        )
        load_soak_proof = _read_optional_proof(args.load_soak_proof)
        load_soak_attestation = _verify_optional_attestation(
            verification_requested=args.verify_load_soak_attestation,
            artifact_path=args.load_soak_proof,
            proof=load_soak_proof,
            environment_profile=args.environment_profile,
            signer_workflow=LOAD_SOAK_SIGNER_WORKFLOW,
            proof_name="load soak proof",
        )
        resource_baseline = _read_optional_resource_baseline(args.resource_baseline)
        resource_attestation = _verify_optional_attestation(
            verification_requested=args.verify_resource_attestation,
            artifact_path=args.resource_baseline,
            proof=resource_baseline,
            environment_profile=args.environment_profile,
            signer_workflow=RESOURCE_SIGNER_WORKFLOW,
            proof_name="resource baseline proof",
        )
        cost_attribution_artifact = _read_optional_json_object(
            args.cost_attribution_artifact, name="platform cost-attribution artifact"
        )
        cost_attribution_attestation = verify_optional_cost_attribution_attestation(
            verification_requested=args.verify_cost_attribution_attestation,
            artifact_path=args.cost_attribution_artifact,
            artifact=cost_attribution_artifact,
            environment_profile=args.environment_profile,
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
            dependency_recovery_proof=dependency_recovery_proof,
            dependency_recovery_attestation=dependency_recovery_attestation,
            load_soak_proof=load_soak_proof,
            load_soak_attestation=load_soak_attestation,
            resource_baseline=resource_baseline,
            resource_attestation=resource_attestation,
            cost_attribution_artifact=cost_attribution_artifact,
            cost_attribution_attestation=cost_attribution_attestation,
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


def _execute_measurements(
    *,
    args: argparse.Namespace,
    plans: list[CapacityWorkloadPlan],
    probe: HttpCapacityProbe,
) -> tuple[list[CapacityMeasurement], float, float | None]:
    if args.paced_load_soak:
        validate_paced_load_soak_request(
            scenarios=tuple(args.scenario),
            environment_profile=args.environment_profile,
            request_count=args.request_count,
            minimum_observation_seconds=args.minimum_observation_seconds,
        )
        paced_result = execute_paced_capacity_soak(
            plans=plans,
            http_probe=probe,
            postgres_probe=PostgresCapacityProbe(database_url=required_database_url()),
            postgres_request_count=args.request_count,
            minimum_observation_seconds=args.minimum_observation_seconds,
        )
        return (
            list(paced_result.measurements),
            paced_result.observed_window_seconds,
            paced_result.postgres_max_connection_utilization_fraction,
        )

    started_at = time.perf_counter()
    measurements: list[CapacityMeasurement] = []
    for plan in plans:
        if plan.scenario == "dependency_failure" and args.dependency_recovery_delay_seconds:
            fault_only = CapacityWorkloadPlan(
                scenario=plan.scenario,
                requests=plan.requests,
                max_concurrency=plan.max_concurrency,
                item_count_field=plan.item_count_field,
                expected_source_failure_class=plan.expected_source_failure_class,
            )
            measurements.extend(execute_capacity_workload(fault_only, probe=probe))
            time.sleep(args.dependency_recovery_delay_seconds)
            measurements.append(execute_capacity_recovery(plan, probe=probe))
        else:
            measurements.extend(execute_capacity_workload(plan, probe=probe))
    postgres_max_utilization = None
    if "postgresql" in args.scenario:
        postgres_result = execute_postgres_capacity_workload(
            probe=PostgresCapacityProbe(database_url=required_database_url()),
            request_count=args.request_count,
            max_concurrency=args.concurrency,
        )
        measurements.extend(postgres_result.measurements)
        postgres_max_utilization = postgres_result.max_connection_utilization_fraction
    return (
        measurements,
        max(time.perf_counter() - started_at, 0.000001),
        postgres_max_utilization,
    )


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


def _verify_optional_attestation(
    *,
    verification_requested: bool,
    artifact_path: Path | None,
    proof: dict[str, object] | None,
    environment_profile: str,
    signer_workflow: str,
    proof_name: str,
) -> VerifiedArtifactAttestation | None:
    if not verification_requested:
        return None
    if artifact_path is None or proof is None:
        raise ValueError(f"attestation verification requires {proof_name}")
    if environment_profile != "production-like":
        raise ValueError("attested capacity qualification requires production-like profile")
    proof_commit = proof.get("commitSha")
    if not isinstance(proof_commit, str) or not proof_commit.strip():
        raise ValueError(f"{proof_name} commitSha must be a non-blank string")
    return GitHubCapacityAttestationVerifier(signer_workflow=signer_workflow).verify(
        artifact_path=artifact_path,
        source_commit_sha=proof_commit,
    )


def _downstream_submission_path(
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


if __name__ == "__main__":
    raise SystemExit(main())
