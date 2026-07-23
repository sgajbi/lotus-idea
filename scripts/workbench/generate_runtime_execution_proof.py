# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.workbench.owner_mainline_evidence import OWNER_MAINLINE_EVIDENCE_CONTRACT_REF
from app.application.workbench.runtime_execution import (
    build_gateway_workbench_runtime_execution_proof_payload,
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
        repository_root = Path(__file__).resolve().parents[2]
        workbench_root = Path(args.workbench_root).resolve()
        summary_path = _resolve_evidence_path(workbench_root, args.live_validation_summary)
        shot_index_path = _resolve_evidence_path(workbench_root, args.shot_index)
        owner_mainline_path = (
            repository_root / args.owner_mainline_evidence
            if args.owner_mainline_evidence
            else repository_root / OWNER_MAINLINE_EVIDENCE_CONTRACT_REF
        )
        payload = build_gateway_workbench_runtime_execution_proof_payload(
            generated_at_utc=parse_generated_at_utc(args.generated_at_utc),
            repository_root=repository_root,
            workbench_live_validation_summary=_read_json_object(summary_path),
            workbench_live_validation_summary_ref=_workbench_ref(workbench_root, summary_path),
            workbench_shot_index_text=shot_index_path.read_text(encoding="utf-8"),
            workbench_shot_index_ref=_workbench_ref(workbench_root, shot_index_path),
            owner_mainline_evidence=_read_json_object(owner_mainline_path),
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"gateway/workbench runtime proof error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate RFC-0002 Gateway/Workbench runtime execution proof."
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--workbench-root",
        required=True,
        help="Path to the lotus-workbench checkout that produced the live validation evidence.",
    )
    parser.add_argument(
        "--live-validation-summary",
        default="output/playwright/live-canonical/live-validation-summary.json",
        help="Path to Workbench live-validation-summary.json, relative to --workbench-root by default.",
    )
    parser.add_argument(
        "--shot-index",
        default="output/playwright/live-canonical/SHOT-INDEX.md",
        help="Path to Workbench SHOT-INDEX.md, relative to --workbench-root by default.",
    )
    parser.add_argument(
        "--owner-mainline-evidence",
        default=OWNER_MAINLINE_EVIDENCE_CONTRACT_REF,
        help="Path to the checked-in Slice 11 owner-mainline evidence contract.",
    )
    parser.add_argument("--output", help="Optional JSON output path.")
    return parser


def _resolve_evidence_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def _workbench_ref(workbench_root: Path, path: Path) -> str:
    try:
        return f"lotus-workbench:{path.resolve().relative_to(workbench_root).as_posix()}"
    except ValueError:
        return "lotus-workbench:external-runtime-evidence"


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


if __name__ == "__main__":
    sys.exit(main())
