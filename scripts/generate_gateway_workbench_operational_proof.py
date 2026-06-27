from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

from app.application.gateway_workbench_operational_proof import (
    build_gateway_workbench_operational_proof_payload,
)


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        workbench_read_path_proof = _read_json_object(
            Path(args.workbench_read_path_proof),
            artifact_name="workbench read-path proof",
        )
        payload = build_gateway_workbench_operational_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            workbench_read_path_proof=workbench_read_path_proof,
            workbench_read_path_proof_ref=_source_safe_artifact_ref(
                Path(args.workbench_read_path_proof),
                artifact_name="workbench read-path proof artifact",
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Gateway/Workbench operational proof error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if payload["gatewayWorkbenchOperationalProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea Gateway/Workbench operational proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument(
        "--workbench-read-path-proof",
        required=True,
        help="Validated Workbench read-path proof artifact to consume.",
    )
    parser.add_argument("--output")
    return parser


def _read_json_object(path: Path, *, artifact_name: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_name} must be a JSON object")
    return payload


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


def _source_safe_artifact_ref(path: Path, *, artifact_name: str) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return artifact_name


if __name__ == "__main__":
    sys.exit(main())
