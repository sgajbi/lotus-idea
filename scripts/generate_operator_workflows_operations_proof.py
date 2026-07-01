from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

from app.application.operator_workflows_operations_proof import (
    build_operator_workflows_operations_proof_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate source-safe lotus-idea operator workflows operations proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        payload = build_operator_workflows_operations_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"operator workflows operations proof error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if payload["operatorWorkflowsOperationsProofValid"] else 1


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
