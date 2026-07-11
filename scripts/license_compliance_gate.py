from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, cast

try:
    from scripts.license_compliance_policy import (
        POLICY_PATH,
        ROOT,
        render_third_party_notice,
        validate_license_policy,
        validate_release_license_evidence,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from license_compliance_policy import (  # type: ignore[no-redef]
        POLICY_PATH,
        ROOT,
        render_third_party_notice,
        validate_license_policy,
        validate_release_license_evidence,
    )

__all__ = [
    "POLICY_PATH",
    "ROOT",
    "render_third_party_notice",
    "validate_license_policy",
    "validate_release_license_evidence",
]


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Lotus Idea license/IP compliance.")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--write-notice", action="store_true")
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--sbom", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.policy if args.policy.is_absolute() else ROOT / args.policy
    payload = _load_json_object(path)
    if args.write_notice:
        notice_path = ROOT / str(payload["notice_path"])
        notice_path.write_text(render_third_party_notice(payload), encoding="utf-8")
    errors = validate_license_policy(payload)
    if (args.release_manifest is None) != (args.sbom is None):
        errors.append("release manifest and SBOM must be supplied together")
    elif args.release_manifest is not None and args.sbom is not None:
        errors.extend(
            validate_release_license_evidence(
                payload,
                _load_json_object(args.release_manifest),
                _load_json_object(args.sbom),
            )
        )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("License compliance gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
