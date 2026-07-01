from __future__ import annotations

import argparse
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from scripts.runtime_dependency_closure_gate import (
    DEPENDENCY_GRAPH_REQUIREMENTS_PATH,
    PYPROJECT_PATH,
    RUNTIME_LOCK_PATH,
    _read_lockfile,
    _read_runtime_roots,
    _runtime_dependency_closure,
)


def runtime_lock_lines_from_closure(closure: dict[str, str]) -> list[str]:
    return [f"{name}=={version}" for name, version in sorted(closure.items())]


def current_runtime_lock_lines(pyproject_path: Path = PYPROJECT_PATH) -> list[str]:
    runtime_roots = _read_runtime_roots(pyproject_path)
    closure = _runtime_dependency_closure(runtime_roots)
    missing = sorted(name for name, version in closure.items() if version == "<not-installed>")
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"runtime dependencies are not installed in the active venv: {joined}")
    return runtime_lock_lines_from_closure(closure)


def validate_runtime_lock_text(
    expected_lines: list[str],
    runtime_lock_path: Path = RUNTIME_LOCK_PATH,
    dependency_graph_path: Path = DEPENDENCY_GRAPH_REQUIREMENTS_PATH,
) -> list[str]:
    expected_locked = _lock_lines_to_mapping(expected_lines)
    errors: list[str] = []
    runtime_locked = _read_lockfile(runtime_lock_path)
    dependency_graph_locked = _read_lockfile(dependency_graph_path)
    if runtime_locked != expected_locked:
        errors.append(
            "requirements/runtime-resolved.lock.txt is stale; run `make dependency-refresh`"
        )
    if dependency_graph_locked != expected_locked:
        errors.append("requirements/requirements.txt is stale; run `make dependency-refresh`")
    if runtime_locked != dependency_graph_locked:
        errors.append(
            "requirements/requirements.txt must mirror requirements/runtime-resolved.lock.txt"
        )
    return errors


def _lock_lines_to_mapping(lines: list[str]) -> dict[str, str]:
    locked: dict[str, str] = {}
    for line_number, line in enumerate(lines, 1):
        requirement = Requirement(line)
        exact_versions = [
            specifier.version for specifier in requirement.specifier if specifier.operator == "=="
        ]
        if len(exact_versions) != 1:
            raise ValueError(f"line {line_number}: requirement must pin one exact version")
        locked[canonicalize_name(requirement.name)] = exact_versions[0]
    return locked


def write_runtime_dependency_locks(
    lines: list[str],
    runtime_lock_path: Path = RUNTIME_LOCK_PATH,
    dependency_graph_path: Path = DEPENDENCY_GRAPH_REQUIREMENTS_PATH,
) -> None:
    text = "\n".join(lines) + "\n"
    runtime_lock_path.write_text(text, encoding="utf-8")
    dependency_graph_path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the resolved runtime dependency lock and GitHub Dependency Graph mirror "
            "from the active validation environment."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that runtime dependency locks already match the active environment.",
    )
    args = parser.parse_args(argv)

    try:
        lines = current_runtime_lock_lines()
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if args.check:
        errors = validate_runtime_lock_text(lines)
        if errors:
            print("\n".join(errors))
            return 1
        print("Runtime dependency lock refresh check passed")
        return 0

    write_runtime_dependency_locks(lines)
    print(
        "Updated requirements/runtime-resolved.lock.txt and requirements/requirements.txt "
        "from the active runtime dependency closure"
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
