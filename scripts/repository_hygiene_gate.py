from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROHIBITED_EXACT_PATHS = {
    ".coverage",
    ".env",
    "coverage.xml",
}

PROHIBITED_PATH_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
}

PROHIBITED_SUFFIXES = {
    ".db",
    ".egg-info",
    ".log",
    ".pyc",
    ".pyo",
}

REQUIRED_BOUNDED_MODULE_PATHS = {
    "scripts/data_lifecycle/__init__.py",
    "scripts/data_lifecycle/run_scheduled_review.py",
    "scripts/data_lifecycle/scheduled_review_proof_gate.py",
    "scripts/data_lifecycle/seed_scheduled_review_fixture.py",
    "src/app/api/data_lifecycle/__init__.py",
    "src/app/api/data_lifecycle/models.py",
    "src/app/application/data_lifecycle/__init__.py",
    "src/app/application/data_lifecycle/authority_verification.py",
    "src/app/domain/data_lifecycle/__init__.py",
    "src/app/domain/data_lifecycle/authority.py",
    "src/app/domain/data_lifecycle/schedule.py",
    "src/app/infrastructure/data_lifecycle/__init__.py",
    "src/app/infrastructure/data_lifecycle/authority_key_source.py",
    "src/app/infrastructure/data_lifecycle/postgres_policy.py",
    "src/app/infrastructure/data_lifecycle/postgres_redaction.py",
    "src/app/infrastructure/data_lifecycle/postgres_schedule.py",
    "src/app/integration/data_lifecycle/__init__.py",
    "src/app/integration/data_lifecycle/authority_contract.py",
    "src/app/ports/data_lifecycle/__init__.py",
    "src/app/ports/data_lifecycle/authority.py",
    "src/app/runtime/data_lifecycle/__init__.py",
    "src/app/runtime/data_lifecycle/authority_state.py",
    "tests/unit/data_lifecycle/test_authority_verification.py",
    "tests/unit/data_lifecycle/test_policy.py",
    "tests/unit/data_lifecycle/test_schedule.py",
}

PROHIBITED_LEGACY_MODULE_PATHS = {
    "scripts/run_scheduled_data_lifecycle_review.py",
    "scripts/scheduled_data_lifecycle_review_proof_gate.py",
    "scripts/seed_scheduled_data_lifecycle_fixture.py",
    "src/app/api/data_lifecycle.py",
    "src/app/api/data_lifecycle_models.py",
    "src/app/application/data_lifecycle.py",
    "src/app/application/lifecycle_authority_verification.py",
    "src/app/domain/data_lifecycle.py",
    "src/app/domain/data_lifecycle_schedule.py",
    "src/app/domain/lifecycle_authority.py",
    "src/app/infrastructure/http_lifecycle_authority_keys.py",
    "src/app/infrastructure/postgres_data_lifecycle.py",
    "src/app/infrastructure/postgres_data_lifecycle_redaction.py",
    "src/app/infrastructure/postgres_data_lifecycle_schedule.py",
    "src/app/integration/lifecycle_authority_contract.py",
    "src/app/ports/data_lifecycle.py",
    "src/app/ports/lifecycle_authority.py",
    "src/app/runtime/lifecycle_authority_state.py",
    "tests/unit/test_data_lifecycle.py",
    "tests/unit/test_data_lifecycle_schedule.py",
    "tests/unit/test_lifecycle_authority_verification.py",
}

EXECUTABLE_PATH_PREFIXES = (
    ".github/workflows/",
    "contracts/",
    "migrations/",
    "scripts/",
    "src/",
    "tests/",
)
RFC_COUPLED_EXECUTABLE_NAME = re.compile(r"(^|[/_-])(rfc|slice)[-_]?\d", re.IGNORECASE)


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


def find_executable_naming_violations(tracked_paths: list[str]) -> list[str]:
    return sorted(
        f"{path}: executable artifact must be named for its capability, not an RFC or slice"
        for tracked_path in tracked_paths
        if (path := _normalise(tracked_path)).startswith(EXECUTABLE_PATH_PREFIXES)
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
