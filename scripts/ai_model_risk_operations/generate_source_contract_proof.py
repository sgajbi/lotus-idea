from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.application.ai_model_risk_operations.source_contract_proof import (  # noqa: E402
    build_ai_model_risk_operations_proof_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload  # noqa: E402
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef] # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_ai_model_risk_operations_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"AI model-risk operations proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0 if payload["aiModelRiskOperationsProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe lotus-idea AI model-risk operations proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
