from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path

from app.application.gateway_workbench_discovery_proof import (
    build_gateway_workbench_discovery_proof_payload,
)

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        platform_mesh_onboarding_proof = _read_json_object(
            Path(args.platform_mesh_onboarding_proof),
            artifact_name="platform mesh onboarding proof",
        )
        workbench_read_path_proof = _read_json_object(
            Path(args.workbench_read_path_proof),
            artifact_name="workbench read-path proof",
        )
        gateway_workbench_operational_proof = _read_json_object(
            Path(args.gateway_workbench_operational_proof),
            artifact_name="Gateway/Workbench operational proof",
        )
        payload = build_gateway_workbench_discovery_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
            platform_root=Path(args.platform_root),
            platform_mesh_onboarding_proof=platform_mesh_onboarding_proof,
            workbench_read_path_proof=workbench_read_path_proof,
            gateway_workbench_operational_proof=gateway_workbench_operational_proof,
            platform_mesh_onboarding_proof_ref=_source_safe_artifact_ref(
                Path(args.platform_mesh_onboarding_proof),
                artifact_name="platform mesh onboarding proof artifact",
            ),
            workbench_read_path_proof_ref=_source_safe_artifact_ref(
                Path(args.workbench_read_path_proof),
                artifact_name="workbench read-path proof artifact",
            ),
            gateway_workbench_operational_proof_ref=_source_safe_artifact_ref(
                Path(args.gateway_workbench_operational_proof),
                artifact_name="Gateway/Workbench operational proof artifact",
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Gateway/Workbench discovery proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    if payload["gatewayWorkbenchDiscoveryProofValid"] or args.allow_missing_evidence:
        return 0
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-safe lotus-idea Gateway/Workbench discovery proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--platform-root", default=str(ROOT.parent / "lotus-platform"))
    parser.add_argument("--platform-mesh-onboarding-proof", required=True)
    parser.add_argument("--workbench-read-path-proof", required=True)
    parser.add_argument("--gateway-workbench-operational-proof", required=True)
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help="Write an invalid non-proof artifact without failing the command.",
    )
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
