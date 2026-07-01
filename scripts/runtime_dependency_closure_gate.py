from __future__ import annotations

import sys
import tomllib
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
RUNTIME_LOCK_PATH = ROOT / "requirements" / "runtime-resolved.lock.txt"


def _read_runtime_roots(pyproject_path: Path) -> list[Requirement]:
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return [Requirement(dependency) for dependency in pyproject["project"]["dependencies"]]


def _read_lockfile(lock_path: Path) -> dict[str, str]:
    locked: dict[str, str] = {}
    for line_number, raw_line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if not requirement.specifier:
            raise ValueError(f"{lock_path}:{line_number}: requirement must pin an exact version")
        exact_versions = [
            specifier.version for specifier in requirement.specifier if specifier.operator == "=="
        ]
        if len(exact_versions) != 1:
            raise ValueError(f"{lock_path}:{line_number}: requirement must pin one exact version")
        locked[canonicalize_name(requirement.name)] = exact_versions[0]
    return locked


def _runtime_dependency_closure(runtime_roots: list[Requirement]) -> dict[str, str]:
    closure: dict[str, str] = {}
    stack: list[tuple[str, tuple[str, ...]]] = [
        (requirement.name, tuple(sorted(requirement.extras))) for requirement in runtime_roots
    ]

    while stack:
        name, active_extras = stack.pop()
        normalized = canonicalize_name(name)
        if normalized in closure:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            closure[normalized] = "<not-installed>"
            continue
        closure[normalized] = distribution.version
        marker_contexts = [{"extra": ""}, *({"extra": extra} for extra in active_extras)]
        for requirement_text in distribution.requires or ():
            requirement = Requirement(requirement_text)
            if requirement.marker is not None and not any(
                requirement.marker.evaluate(context) for context in marker_contexts
            ):
                continue
            stack.append((requirement.name, tuple(sorted(requirement.extras))))

    return closure


def validate_runtime_dependency_closure(
    pyproject_path: Path = PYPROJECT_PATH,
    lock_path: Path = RUNTIME_LOCK_PATH,
) -> list[str]:
    errors: list[str] = []
    runtime_roots = _read_runtime_roots(pyproject_path)
    locked = _read_lockfile(lock_path)
    closure = _runtime_dependency_closure(runtime_roots)
    root_names = {canonicalize_name(requirement.name) for requirement in runtime_roots}

    if set(locked) <= root_names:
        errors.append(
            "runtime-resolved.lock.txt must include transitive runtime dependencies, "
            "not only direct pyproject dependencies"
        )

    for name, installed_version in sorted(closure.items()):
        locked_version = locked.get(name)
        if locked_version is None:
            errors.append(f"runtime-resolved.lock.txt missing runtime dependency `{name}`")
            continue
        if installed_version == "<not-installed>":
            errors.append(f"runtime dependency `{name}` is not installed in the validation venv")
        elif locked_version != installed_version:
            errors.append(
                f"runtime-resolved.lock.txt pins `{name}=={locked_version}` but "
                f"the validation venv has `{installed_version}`"
            )

    return errors


def main() -> int:
    try:
        errors = validate_runtime_dependency_closure()
    except ValueError as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(errors))
        return 1
    print("Runtime dependency closure gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
