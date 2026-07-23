# ruff: noqa: E402
from __future__ import annotations

from pathlib import Path


import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.capacity_evidence_qualification import (
    MINIMUM_LOAD_SOAK_SAMPLES,
    MINIMUM_LOAD_SOAK_SECONDS,
)


EXPECTED_WORKFLOWS = {
    "api",
    "source_ingestion",
    "outbox_delivery",
    "downstream_submission",
    "postgresql",
}
ATTESTATION_ACTION = "actions/attest-build-provenance@0f67c3f4856b2e3261c31976d6725780e5e4c373"


def validate_capacity_attestation_workflows(repository_root: Path) -> list[str]:
    errors = _validate_postgres_capacity_workflow(repository_root)
    errors.extend(validate_dependency_recovery_workflow(repository_root))
    errors.extend(validate_load_soak_workflow(repository_root))
    return errors


def _validate_postgres_capacity_workflow(repository_root: Path) -> list[str]:
    path = repository_root / ".github/workflows/postgres-capacity-evidence.yml"
    if not path.is_file():
        return ["PostgreSQL capacity attestation workflow is missing"]
    workflow = path.read_text(encoding="utf-8")
    required = (
        "workflow_dispatch:",
        "if: github.ref == 'refs/heads/main'",
        "runs-on: [self-hosted, linux, lotus-capacity-evidence]",
        "environment: capacity-production-like",
        "LOTUS_IDEA_DATABASE_URL: ${{ secrets.LOTUS_IDEA_CAPACITY_DATABASE_URL }}",
        "POSTGRES_CAPACITY_CONFIRMATION: SATURATE_DEDICATED_LOTUS_IDEA_POSTGRES",
        "SERVICE_CAPACITY_PROFILE: test",
        "make postgres-capacity-threshold-proof",
        "make postgres-capacity-threshold-proof-gate",
        ATTESTATION_ACTION,
    )
    errors = [
        f"PostgreSQL capacity workflow missing {token!r}"
        for token in required
        if token not in workflow
    ]
    if "schedule:" in workflow:
        errors.append("PostgreSQL saturation workflow must not run on a schedule")
    if "SERVICE_CAPACITY_PROFILE: production" in workflow:
        errors.append("PostgreSQL threshold measurement must remain controlled-test classified")
    proof_gate = workflow.find("make postgres-capacity-threshold-proof-gate")
    attestation = workflow.find(ATTESTATION_ACTION)
    if proof_gate < 0 or proof_gate > attestation:
        errors.append("PostgreSQL threshold proof gate must run before provenance attestation")
    return errors


def validate_dependency_recovery_workflow(repository_root: Path) -> list[str]:
    path = repository_root / ".github/workflows/service-dependency-recovery-evidence.yml"
    if not path.is_file():
        return ["dependency recovery attestation workflow is missing"]
    workflow = path.read_text(encoding="utf-8")
    required = (
        "workflow_dispatch:",
        "github.ref == 'refs/heads/main'",
        "RUN_CONTROLLED_LOTUS_IDEA_DEPENDENCY_RECOVERY",
        "runs-on: [self-hosted, linux, lotus-capacity-evidence]",
        "environment: capacity-production-like",
        "LOTUS_IDEA_CAPACITY_AUTHORIZATION: ${{ secrets.LOTUS_IDEA_CAPACITY_AUTHORIZATION }}",
        "--environment-profile production-like",
        "--scenario dependency_failure",
        "--dependency-recovery-delay-seconds",
        "--allow-mutating-workflows",
        "make service-dependency-recovery-proof-gate",
        ATTESTATION_ACTION,
    )
    errors = [
        f"dependency recovery workflow missing {token!r}"
        for token in required
        if token not in workflow
    ]
    if "schedule:" in workflow:
        errors.append("dependency recovery workflow must not run on a schedule")
    proof_gate = workflow.find("make service-dependency-recovery-proof-gate")
    attestation = workflow.find(ATTESTATION_ACTION)
    if proof_gate < 0 or proof_gate > attestation:
        errors.append("dependency recovery proof gate must run before provenance attestation")
    return errors


def validate_load_soak_workflow(repository_root: Path) -> list[str]:
    path = repository_root / ".github/workflows/service-load-soak-evidence.yml"
    if not path.is_file():
        return ["load soak attestation workflow is missing"]
    workflow = path.read_text(encoding="utf-8")
    required = (
        "workflow_dispatch:",
        "github.ref == 'refs/heads/main'",
        "RUN_CONTROLLED_LOTUS_IDEA_LOAD_SOAK",
        "runs-on: [self-hosted, linux, lotus-capacity-evidence]",
        "environment: capacity-production-like",
        "LOTUS_IDEA_DATABASE_URL: ${{ secrets.LOTUS_IDEA_CAPACITY_DATABASE_URL }}",
        "SERVICE_RESOURCE_METRICS_URL: ${{ vars.LOTUS_IDEA_RESOURCE_METRICS_URL }}",
        "SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE",
        "--environment-profile production-like",
        f"--request-count {MINIMUM_LOAD_SOAK_SAMPLES}",
        "--paced-load-soak",
        f"--minimum-observation-seconds {int(MINIMUM_LOAD_SOAK_SECONDS)}",
        "--downstream-capacity-seed",
        "make service-load-soak-proof-gate",
        "scripts/run_service_resource_baseline.py",
        "--sample-count 61",
        "--sample-interval-seconds 60",
        "resource_pid=$!",
        "load_pid=$!",
        'wait -n "${resource_pid}" "${load_pid}"',
        "make service-resource-proof-gate",
        "subject-path: output/observability/service-resource-baseline.json",
        ATTESTATION_ACTION,
    )
    errors = [
        f"load soak workflow missing {token!r}" for token in required if token not in workflow
    ]
    for scenario in sorted(EXPECTED_WORKFLOWS):
        if workflow.count(f"--scenario {scenario}") != 1:
            errors.append(f"load soak workflow must run scenario {scenario} exactly once")
    if "--scenario dependency_failure" in workflow:
        errors.append("load soak workflow must keep dependency recovery evidence separate")
    if "schedule:" in workflow:
        errors.append("load soak workflow must not run on a schedule")
    load_gate = workflow.find("make service-load-soak-proof-gate")
    resource_gate = workflow.find("make service-resource-proof-gate")
    attestations = [
        index
        for index in range(len(workflow))
        if workflow.startswith("actions/attest-build-provenance@", index)
    ]
    if len(attestations) != 2:
        errors.append("load soak workflow must attest load and resource artifacts separately")
    elif load_gate < 0 or load_gate > attestations[0]:
        errors.append("load soak proof gate must run before provenance attestation")
    elif resource_gate < 0 or resource_gate > attestations[1]:
        errors.append("resource proof gate must run before provenance attestation")
    return errors
