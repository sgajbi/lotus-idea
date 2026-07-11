from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from app.application.capacity_evidence_qualification import validate_resource_proof


def validate_artifact(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("resource proof must be a JSON object")
    validate_resource_proof(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a production-like Lotus Idea process-resource proof artifact"
    )
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        validate_artifact(args.artifact)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Service resource proof gate failed: {exc}", file=sys.stderr)
        return 1
    print("Service resource proof gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
