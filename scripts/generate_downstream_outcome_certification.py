# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_outcome_certification import (  # noqa: E402
    build_downstream_outcome_certification_payload,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_downstream_outcome_certification_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            repository_root=Path.cwd(),
            advise_intake_runtime_execution_proof=_read_json_object(
                Path(args.advise_intake_runtime_execution_proof)
            ),
            advise_intake_runtime_execution_proof_ref=(
                args.advise_intake_runtime_execution_proof_ref
            ),
            manage_intake_runtime_execution_proof=_read_json_object(
                Path(args.manage_intake_runtime_execution_proof)
            ),
            manage_intake_runtime_execution_proof_ref=(
                args.manage_intake_runtime_execution_proof_ref
            ),
            report_materialization_runtime_execution_proof=_read_json_object(
                Path(args.report_materialization_runtime_execution_proof)
            ),
            report_materialization_runtime_execution_proof_ref=(
                args.report_materialization_runtime_execution_proof_ref
            ),
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"downstream outcome certification proof error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate RFC-0002 downstream outcome certification aggregate proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--advise-intake-runtime-execution-proof", required=True)
    parser.add_argument(
        "--advise-intake-runtime-execution-proof-ref",
        default="output/downstream/advise-intake-runtime-execution-proof.json",
    )
    parser.add_argument("--manage-intake-runtime-execution-proof", required=True)
    parser.add_argument(
        "--manage-intake-runtime-execution-proof-ref",
        default="output/downstream/manage-intake-runtime-execution-proof.json",
    )
    parser.add_argument("--report-materialization-runtime-execution-proof", required=True)
    parser.add_argument(
        "--report-materialization-runtime-execution-proof-ref",
        default="output/report/materialization-runtime-execution-proof.json",
    )
    parser.add_argument("--output", help="Optional JSON output path.")
    return parser


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


if __name__ == "__main__":
    sys.exit(main())
