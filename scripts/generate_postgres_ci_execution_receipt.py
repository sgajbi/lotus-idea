# ruff: noqa: E402
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.ai_lineage_store_proof.ci_receipt import (
    build_postgres_ci_execution_receipt,
)
from app.domain.proof_evidence import ci_execution_receipt_is_well_formed

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = build_postgres_ci_execution_receipt(
            test_report_path=Path(args.test_report),
            repository=args.repository,
            workflow_path=args.workflow_path,
            workflow_name=args.workflow_name,
            job_name=args.job_name,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            source_commit_sha=args.source_commit_sha,
            source_ref=args.source_ref,
            conclusion=args.conclusion,
            completed_at_utc=_aware_datetime(args.completed_at_utc),
            artifact_sha256=args.artifact_sha256,
        )
    except ValueError as exc:
        print(f"PostgreSQL CI execution receipt error: {exc}", file=sys.stderr)
        return 2
    if not ci_execution_receipt_is_well_formed(receipt):
        print("PostgreSQL CI execution receipt failed structural validation", file=sys.stderr)
        return 2
    write_json_payload(asdict(receipt), output=args.output)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bind the governed PostgreSQL test result to GitHub CI execution identity."
    )
    parser.add_argument("--test-report", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-path", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--source-commit-sha", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--conclusion", required=True)
    parser.add_argument("--completed-at-utc", required=True)
    parser.add_argument("--artifact-sha256")
    parser.add_argument("--output", required=True)
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--completed-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
