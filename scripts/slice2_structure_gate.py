from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from architecture_boundary_gate import validate_architecture_boundaries

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCUMENTATION_FRAGMENTS = {
    "README.md": (
        "foundation-only",
        "no externally supported product feature is promoted",
    ),
    "REPOSITORY-ENGINEERING-CONTEXT.md": (
        "No externally supported product feature is promoted yet.",
        "make slice2-structure-gate",
    ),
    "docs/rfcs/README.md": (
        "currently in foundation state",
        "Slice 2 structure gate",
    ),
    "wiki/Supported-Features.md": (
        "Current posture: no business feature is supported yet.",
        "`current_posture` | `foundation_only`",
    ),
    "wiki/Validation-and-CI.md": (
        "make slice2-structure-gate",
        "RFC-0002 Slice 2",
    ),
}


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_supported_features(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = root / "supported-features" / "supported-features.json"
    if not path.exists():
        return None, [f"Missing {_relative(root, path)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"{_relative(root, path)} is invalid JSON: {exc.msg}"]
    if not isinstance(payload, dict):
        return None, [f"{_relative(root, path)} must contain a JSON object"]
    return payload, []


def _validate_supported_feature_posture(root: Path) -> list[str]:
    payload, errors = _load_supported_features(root)
    if payload is None:
        return errors
    if payload.get("current_posture") != "foundation_only":
        errors.append(
            "supported-features current_posture must remain `foundation_only` for Slice 2"
        )
    features = payload.get("features")
    if features != []:
        errors.append("supported-features features[] must remain empty for Slice 2")
    planned_capabilities = payload.get("planned_capabilities")
    if not isinstance(planned_capabilities, list) or not planned_capabilities:
        errors.append("supported-features planned_capabilities[] must remain populated")
    else:
        for index, capability in enumerate(planned_capabilities):
            if not isinstance(capability, dict):
                errors.append(f"planned_capabilities[{index}] must be an object")
                continue
            if capability.get("status") != "planned":
                errors.append(f"planned_capabilities[{index}].status must remain `planned`")
    return errors


def _validate_documentation_truth(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, fragments in REQUIRED_DOCUMENTATION_FRAGMENTS.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"Missing {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path} must contain `{fragment}`")
    return errors


def _validate_architecture_truth(
    architecture_violations: list[dict[str, str]] | None = None,
) -> list[str]:
    violations = (
        validate_architecture_boundaries()
        if architecture_violations is None
        else architecture_violations
    )
    return [
        (
            f"{violation['path']} imports {violation['import']} across the "
            f"{violation['layer']} boundary"
        )
        for violation in violations
    ]


def validate_slice2_structure(
    root: Path = ROOT,
    *,
    architecture_violations: list[dict[str, str]] | None = None,
) -> list[str]:
    root = root.resolve()
    return [
        *_validate_supported_feature_posture(root),
        *_validate_documentation_truth(root),
        *_validate_architecture_truth(architecture_violations),
    ]


def main() -> int:
    errors = validate_slice2_structure(ROOT)
    if errors:
        print("\n".join(errors))
        return 1
    print("Slice 2 structure gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
