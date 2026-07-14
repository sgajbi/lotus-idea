from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application.data_mesh.platform_catalog_source_contract import (  # noqa: E402
    build_platform_mesh_onboarding_proof_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload  # noqa: E402
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        payload = build_platform_mesh_onboarding_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            platform_root=Path(args.platform_root) if args.platform_root else None,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"platform mesh onboarding proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    proof_checks = payload.get("proofChecks")
    if (
        args.allow_missing_evidence
        and isinstance(proof_checks, dict)
        and proof_checks.get("fileEvidencePresent") is False
    ):
        return 0
    return 0 if payload["platformMeshOnboardingProofValid"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea platform mesh onboarding proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--platform-root")
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help=(
            "Write an invalid non-proof artifact and exit 0 when sibling "
            "platform evidence is absent; contract drift still exits non-zero "
            "once required evidence files are present."
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
