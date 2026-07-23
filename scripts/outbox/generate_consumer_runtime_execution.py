# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.consumer_runtime import (  # noqa: E402
    build_outbox_consumer_runtime_execution_payload,
    outbox_consumer_runtime_execution_is_valid,
)
from app.runtime.proof_artifact_files import read_optional_json_object  # noqa: E402
from scripts.proof_generator_io import write_json_payload  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an outbox downstream-consumer runtime execution proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--advise-intake-runtime-execution-proof", required=True)
    parser.add_argument("--manage-intake-runtime-execution-proof", required=True)
    parser.add_argument("--report-materialization-runtime-execution-proof", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    generated_at_utc = _aware_datetime(args.generated_at_utc)
    payload = build_outbox_consumer_runtime_execution_payload(
        generated_at_utc=generated_at_utc,
        advise_intake_runtime_execution_proof=_required_payload(
            args.advise_intake_runtime_execution_proof,
            "Advise intake runtime execution proof",
        ),
        advise_intake_runtime_execution_proof_ref=_source_safe_ref(
            args.advise_intake_runtime_execution_proof
        ),
        manage_intake_runtime_execution_proof=_required_payload(
            args.manage_intake_runtime_execution_proof,
            "Manage intake runtime execution proof",
        ),
        manage_intake_runtime_execution_proof_ref=_source_safe_ref(
            args.manage_intake_runtime_execution_proof
        ),
        report_materialization_runtime_execution_proof=_required_payload(
            args.report_materialization_runtime_execution_proof,
            "Report materialization runtime execution proof",
        ),
        report_materialization_runtime_execution_proof_ref=_source_safe_ref(
            args.report_materialization_runtime_execution_proof
        ),
    )
    write_json_payload(payload, output=args.output)
    if not outbox_consumer_runtime_execution_is_valid(payload):
        print("outbox consumer runtime execution proof is invalid", file=sys.stderr)
        return 1
    return 0


def _required_payload(path_value: str, artifact_name: str) -> dict[str, Any]:
    payload = read_optional_json_object(Path(path_value), artifact_name=artifact_name)
    if payload is None:
        raise ValueError(f"{artifact_name} is required")
    return payload


def _source_safe_ref(path_value: str) -> str:
    path = Path(path_value)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
