# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import sys
import time


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)
from app.application.service_capacity_baseline import (
    CapacityMeasurement,
    build_service_capacity_baseline,
)
from app.application.capacity_evidence_qualification import (
    DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    LOAD_SOAK_SIGNER_WORKFLOW,
    POSTGRES_CAPACITY_SIGNER_WORKFLOW,
    RESOURCE_SIGNER_WORKFLOW,
    VerifiedArtifactAttestation,
    MINIMUM_LOAD_SOAK_SECONDS,
)
from app.application.service_capacity_workload import (
    CapacityWorkloadPlan,
    execute_capacity_recovery,
    execute_capacity_workload,
    execute_paced_capacity_soak,
    execute_postgres_capacity_workload,
)
from app.application.service_capacity_workload_cli import (
    DOWNSTREAM_PATH_ENV,
    SCENARIO_CHOICES,
    build_workload_plans,
    downstream_submission_path as _downstream_submission_path,
    validate_paced_load_soak_request,
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


OUTPUT_ENV = "LOTUS_IDEA_SERVICE_CAPACITY_BASELINE"


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
        _validate_cli_timing(args)
        plans = _build_workload_plans_from_args(args)
        probe = HttpCapacityProbe(base_url=args.base_url, timeout_seconds=args.timeout_seconds)
        measurements, observed_window_seconds, postgres_max_utilization = _execute_measurements(
            args=args, plans=plans, probe=probe
        )
        artifact = _build_capacity_baseline_artifact(
            args=args,
            measurements=measurements,
            observed_window_seconds=observed_window_seconds,
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


def _validate_cli_timing(args: argparse.Namespace) -> None:
    if args.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if args.dependency_recovery_delay_seconds < 0:
        raise ValueError("dependency_recovery_delay_seconds must not be negative")


def _build_workload_plans_from_args(args: argparse.Namespace) -> list[CapacityWorkloadPlan]:
    downstream_capacity_seed = _read_optional_json_object(
        args.downstream_capacity_seed, name="downstream capacity seed"
    )
    return build_workload_plans(
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


def _build_capacity_baseline_artifact(
    *,
    args: argparse.Namespace,
    measurements: list[CapacityMeasurement],
    observed_window_seconds: float,
    postgres_max_connection_utilization_fraction: float | None,
) -> dict[str, object]:
    threshold_proof, threshold_attestation = _read_and_verify_optional_proof(
        verification_requested=args.verify_postgres_threshold_attestation,
        artifact_path=args.postgres_threshold_proof,
        environment_profile=args.environment_profile,
        signer_workflow=POSTGRES_CAPACITY_SIGNER_WORKFLOW,
        proof_name="PostgreSQL threshold proof",
    )
    dependency_recovery_proof, dependency_recovery_attestation = _read_and_verify_optional_proof(
        verification_requested=args.verify_dependency_recovery_attestation,
        artifact_path=args.dependency_recovery_proof,
        environment_profile=args.environment_profile,
        signer_workflow=DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
        proof_name="dependency recovery proof",
    )
    load_soak_proof, load_soak_attestation = _read_and_verify_optional_proof(
        verification_requested=args.verify_load_soak_attestation,
        artifact_path=args.load_soak_proof,
        environment_profile=args.environment_profile,
        signer_workflow=LOAD_SOAK_SIGNER_WORKFLOW,
        proof_name="load soak proof",
    )
    resource_baseline, resource_attestation = _read_and_verify_resource_baseline(
        args=args,
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
    return build_service_capacity_baseline(
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
        postgres_max_connection_utilization_fraction=postgres_max_connection_utilization_fraction,
    )


def _read_and_verify_optional_proof(
    *,
    verification_requested: bool,
    artifact_path: Path | None,
    environment_profile: str,
    signer_workflow: str,
    proof_name: str,
) -> tuple[dict[str, object] | None, VerifiedArtifactAttestation | None]:
    proof = _read_optional_proof(artifact_path)
    return proof, _verify_optional_attestation(
        verification_requested=verification_requested,
        artifact_path=artifact_path,
        proof=proof,
        environment_profile=environment_profile,
        signer_workflow=signer_workflow,
        proof_name=proof_name,
    )


def _read_and_verify_resource_baseline(
    *, args: argparse.Namespace
) -> tuple[dict[str, object] | None, VerifiedArtifactAttestation | None]:
    resource_baseline = _read_optional_resource_baseline(args.resource_baseline)
    return resource_baseline, _verify_optional_attestation(
        verification_requested=args.verify_resource_attestation,
        artifact_path=args.resource_baseline,
        proof=resource_baseline,
        environment_profile=args.environment_profile,
        signer_workflow=RESOURCE_SIGNER_WORKFLOW,
        proof_name="resource baseline proof",
    )


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
    return measurements, max(time.perf_counter() - started_at, 0.000001), postgres_max_utilization


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


if __name__ == "__main__":
    raise SystemExit(main())
