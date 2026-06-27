from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.report_materialization_proof import (  # noqa: E402
    build_report_materialization_proof_payload,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_report_materialization_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            report_root=Path(args.report_root) if args.report_root else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"report materialization proof error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    if payload["reportMaterializationProofValid"]:
        return 0
    proof_checks = payload.get("proofChecks")
    if (
        args.allow_missing_evidence
        and isinstance(proof_checks, dict)
        and proof_checks.get("fileEvidencePresent") is False
    ):
        return 0
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe lotus-idea proof for lotus-report idea evidence "
            "materialization."
        )
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--report-root")
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help=(
            "Write an invalid non-proof artifact and exit 0 when sibling lotus-report "
            "evidence is absent. Contract drift still exits non-zero once required "
            "evidence files are present."
        ),
    )
    return parser


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
