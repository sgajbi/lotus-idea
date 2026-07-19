# ruff: noqa: E402
from __future__ import annotations

import argparse
import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.source_ingestion_scheduler import (
    build_scheduled_worker_deployment_evidence_payload,
    scheduled_worker_deployment_evidence_is_valid,
)
from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_scheduled_worker_deployment_evidence_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            source_commit_sha=args.source_commit_sha,
            image_digest=args.image_digest,
            target_environment=args.target_environment,
            environment_class=args.environment_class,
            controller_workflow=args.controller_workflow,
            controller_run_id=args.controller_run_id,
            controller_run_attempt=args.controller_run_attempt,
            deployment_actor=args.deployment_actor,
            workload_identity=args.workload_identity,
            rollout_completed_at_utc=parse_generated_at_utc(args.rollout_completed_at_utc),
            scheduler_configuration_digest=args.scheduler_configuration_digest,
            source_contract_digest=args.source_contract_digest,
        )
    except ValueError as exc:
        print(f"scheduled worker deployment-evidence error: {exc}", file=sys.stderr)
        return 2
    if not scheduled_worker_deployment_evidence_is_valid(payload):
        print(
            "scheduled worker deployment-evidence error: receipt failed contract validation",
            file=sys.stderr,
        )
        return 2
    write_json_payload(payload, output=args.output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate closed scheduled-worker deployment evidence from observed "
            "release-controller facts."
        )
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--source-commit-sha", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--target-environment", required=True)
    parser.add_argument(
        "--environment-class",
        choices=("development", "test", "staging", "production"),
        required=True,
    )
    parser.add_argument("--controller-workflow", required=True)
    parser.add_argument("--controller-run-id", required=True)
    parser.add_argument("--controller-run-attempt", type=int, required=True)
    parser.add_argument("--deployment-actor", required=True)
    parser.add_argument("--workload-identity", required=True)
    parser.add_argument("--rollout-completed-at-utc", required=True)
    parser.add_argument("--scheduler-configuration-digest", required=True)
    parser.add_argument("--source-contract-digest", required=True)
    parser.add_argument("--output")
    return parser


if __name__ == "__main__":
    sys.exit(main())
