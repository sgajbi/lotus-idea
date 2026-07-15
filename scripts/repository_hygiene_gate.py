from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

try:
    from scripts.repository_hygiene.policy import (
        PROHIBITED_EXACT_PATHS,
        PROHIBITED_LEGACY_MODULE_PATHS,
        PROHIBITED_PATH_PARTS,
        PROHIBITED_SUFFIXES,
        REQUIRED_BOUNDED_MODULE_PATHS,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from repository_hygiene.policy import (  # type: ignore[import-not-found,no-redef]
        PROHIBITED_EXACT_PATHS,
        PROHIBITED_LEGACY_MODULE_PATHS,
        PROHIBITED_PATH_PARTS,
        PROHIBITED_SUFFIXES,
        REQUIRED_BOUNDED_MODULE_PATHS,
    )
EXECUTABLE_PATH_PREFIXES = (
    ".github/workflows/",
    "migrations/",
    "scripts/",
    "src/",
    "tests/",
)
RFC_COUPLED_EXECUTABLE_NAME = re.compile(r"(^|[/_-])(rfc|slice)[-_]?\d", re.IGNORECASE)
RFC_TRACKING_EXECUTABLE_PATHS: frozenset[str] = frozenset()


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=False,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _normalise(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def find_repository_hygiene_violations(tracked_paths: list[str]) -> list[str]:
    violations: list[str] = []
    for tracked_path in tracked_paths:
        normalised = _normalise(tracked_path)
        parts = set(normalised.split("/"))
        suffixes = Path(normalised).suffixes

        if normalised in PROHIBITED_EXACT_PATHS:
            violations.append(f"{normalised}: generated or local-only artifact must not be tracked")
            continue
        if parts & PROHIBITED_PATH_PARTS:
            violations.append(
                f"{normalised}: generated or dependency directory content must not be tracked"
            )
            continue
        if any(suffix in PROHIBITED_SUFFIXES for suffix in suffixes):
            violations.append(
                f"{normalised}: generated or local-only file type must not be tracked"
            )

    return sorted(violations)


def find_bounded_module_placement_violations(tracked_paths: list[str]) -> list[str]:
    normalised_paths = {_normalise(path) for path in tracked_paths}
    violations = [
        f"{path}: required bounded-module path is missing"
        for path in REQUIRED_BOUNDED_MODULE_PATHS - normalised_paths
    ]
    violations.extend(
        f"{path}: legacy flat-module path must not be reintroduced"
        for path in PROHIBITED_LEGACY_MODULE_PATHS & normalised_paths
    )
    return sorted(violations)


def find_executable_naming_violations(
    tracked_paths: list[str],
    *,
    rfc_tracking_paths: frozenset[str] = RFC_TRACKING_EXECUTABLE_PATHS,
) -> list[str]:
    return sorted(
        f"{path}: executable artifact must be named for its capability, not an RFC or slice"
        for tracked_path in tracked_paths
        if (path := _normalise(tracked_path)).startswith(EXECUTABLE_PATH_PREFIXES)
        and path not in rfc_tracking_paths
        and RFC_COUPLED_EXECUTABLE_NAME.search(path)
    )


def main() -> int:
    tracked_paths = _tracked_paths()
    violations = [
        *find_repository_hygiene_violations(tracked_paths),
        *find_bounded_module_placement_violations(tracked_paths),
        *find_executable_naming_violations(tracked_paths),
    ]
    if violations:
        print("Repository hygiene gate failed:")
        print("\n".join(violations))
        return 1

    print("Repository hygiene gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
