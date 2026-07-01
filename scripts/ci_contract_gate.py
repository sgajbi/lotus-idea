from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(Path(__file__).resolve().parent))
from ci_contract_gate_expectations import (  # noqa: E402
    GENERATED_READINESS_ARTIFACTS,
    PASSED_READINESS_ARTIFACTS,
    REQUIRED_LINT_TARGETS,
    REQUIRED_READINESS_WIRING,
    REQUIRED_TEST_SELECTORS,
    SCRIPT_TARGET_EXPECTATIONS,
    TEST_TARGET_EXPECTATIONS,
)
from ci_e2e_contract import validate_e2e_suite  # noqa: E402
from ci_release_evidence_contract import (  # noqa: E402
    validate_dependency_governance,
    validate_dockerfile_runtime,
    validate_release_evidence_targets,
)
from ci_workflow_contract_expectations import (  # noqa: E402
    PROHIBITED_WORKFLOW_PATTERNS,
    WORKFLOW_EXPECTATIONS,
)
from security_tab_governance_contract import validate_security_tab_governance_files  # noqa: E402

MAKEFILE_PATH = ROOT / "Makefile"
DOCKERFILE_PATH = ROOT / "Dockerfile"
PYPROJECT_PATH = ROOT / "pyproject.toml"
CI_TOOLING_LOCK_PATH = ROOT / "requirements" / "ci-tooling.lock.txt"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
E2E_TESTS_DIR = ROOT / "tests" / "e2e"
ACTION_USE_RE = re.compile(r"uses:\s+(?P<action>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<ref>[^ \t#]+)")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PINNED_ACTIONS: dict[str, tuple[str, str]] = {
    "actions/checkout": ("9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0", "v7.0.0"),
    "actions/setup-python": ("a309ff8b426b58ec0e2a45f0f869d46889d02405", "v6.2.0"),
    "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7.0.1"),
    "actions/download-artifact": ("3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", "v8.0.1"),
    "docker/setup-buildx-action": ("d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5", "v4.1.0"),
    "reviewdog/action-actionlint": ("6fb7acc99f4a1008869fa8a0f09cfca740837d9d", "v1.72.0"),
}

REQUIRED_TARGETS = (
    *REQUIRED_LINT_TARGETS,
    "postgres-integration-gate",
    "duplicate-implementation-inventory",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "test-unit",
    "test-integration",
    "test-e2e",
    "test-unit-coverage",
    "test-integration-coverage",
    "test-e2e-coverage",
    "test-coverage",
    "coverage-gate",
    "security-audit",
    "ci-release",
    "docker-build",
    "container-runtime-smoke",
    "release-sbom",
    "container-image-scan",
    "implementation-proof-readiness-check",
    "runtime-trust-telemetry-snapshot-check",
)
REQUIRED_LINT_CALLS = tuple(f"$(MAKE) {target}" for target in REQUIRED_LINT_TARGETS)
REQUIRED_CHECK_DEPS = (
    "lint",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "migration-contract-gate",
    "migration-execution-gate",
    "supported-features-gate",
    "endpoint-certification-gate",
    "test",
)
REQUIRED_CI_DEPS = (
    "lint",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "migration-contract-gate",
    "migration-execution-gate",
    "supported-features-gate",
    "endpoint-certification-gate",
    "test-integration",
    "test-e2e",
    "test-coverage",
    "security-audit",
)
REQUIRED_CI_RELEASE_DEPS = (
    "ci",
    "implementation-proof-readiness-check",
    "runtime-trust-telemetry-snapshot-check",
    "postgres-integration-gate",
    "docker-build",
    "container-runtime-smoke",
    "container-image-scan",
    "release-sbom",
)
READINESS_TARGET = "Makefile implementation-proof-readiness-check target"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _target_block(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:.*?(?=^\S|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(makefile)
    return match.group(0) if match else ""


def _target_deps(makefile: str, target: str) -> set[str]:
    match = re.search(rf"^{re.escape(target)}:\s*(?P<deps>.*)$", makefile, re.MULTILINE)
    if not match:
        return set()
    return {dependency.strip() for dependency in match.group("deps").split() if dependency.strip()}


def _validate_implementation_proof_readiness_target(makefile: str) -> list[str]:
    errors: list[str] = []
    target_block = _target_block(makefile, "implementation-proof-readiness-check")
    for marker, description in GENERATED_READINESS_ARTIFACTS:
        if marker not in target_block:
            errors.append(f"{READINESS_TARGET} must generate {description}")
    for marker, description in PASSED_READINESS_ARTIFACTS:
        if marker not in target_block:
            errors.append(
                f"{READINESS_TARGET} must pass the {description} into readiness generation"
            )
    for marker, requirement in REQUIRED_READINESS_WIRING:
        if marker not in target_block:
            errors.append(f"{READINESS_TARGET} must {requirement}")
    if target_block.count("--allow-missing-evidence") < 6:
        errors.append(
            f"{READINESS_TARGET} must keep all cross-repo proof generators CI-stable when "
            "sibling evidence is absent"
        )
    return errors


def _validate_required_makefile_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    for target in REQUIRED_TARGETS:
        if not re.search(rf"^{re.escape(target)}:", makefile, re.MULTILINE):
            errors.append(f"Makefile missing required target `{target}`")
    for selector, error in REQUIRED_TEST_SELECTORS.items():
        if selector not in makefile:
            errors.append(error)
    return errors


def _validate_aggregate_makefile_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    lint_block = _target_block(makefile, "lint")
    for call in REQUIRED_LINT_CALLS:
        if call not in lint_block:
            errors.append(f"Makefile lint target must call `{call}`")
    if "$(MAKE) implementation-proof-readiness-check" in lint_block:
        errors.append(
            "Makefile lint target must not call artifact-producing "
            "`$(MAKE) implementation-proof-readiness-check`; use `make ci-release` "
            "or the explicit readiness command for generated proof evidence"
        )
    if "$(MAKE) runtime-trust-telemetry-snapshot-check" in lint_block:
        errors.append(
            "Makefile lint target must not call artifact-producing "
            "`$(MAKE) runtime-trust-telemetry-snapshot-check`; use `make ci-release` "
            "or the explicit snapshot command for generated proof evidence"
        )
    check_deps = _target_deps(makefile, "check")
    for dependency in REQUIRED_CHECK_DEPS:
        if dependency not in check_deps:
            errors.append(f"Makefile check target missing `{dependency}`")
    ci_deps = _target_deps(makefile, "ci")
    for dependency in REQUIRED_CI_DEPS:
        if dependency not in ci_deps:
            errors.append(f"Makefile ci target missing `{dependency}`")
    ci_release_deps = _target_deps(makefile, "ci-release")
    for dependency in REQUIRED_CI_RELEASE_DEPS:
        if dependency not in ci_release_deps:
            errors.append(f"Makefile ci-release target missing `{dependency}`")
    return errors


def _validate_test_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    for target, expected_command in TEST_TARGET_EXPECTATIONS.items():
        if expected_command not in _target_block(makefile, target):
            errors.append(f"Makefile {target} target must run `{expected_command}`")

    coverage_block = _target_block(makefile, "test-coverage")
    for target in ("test-unit-coverage", "test-integration-coverage", "test-e2e-coverage"):
        if target not in coverage_block:
            errors.append(f"Makefile test-coverage target must call `{target}`")
    if "$(MAKE) coverage-gate" not in coverage_block:
        errors.append("Makefile test-coverage target must call `$(MAKE) coverage-gate`")
    coverage_gate_block = _target_block(makefile, "coverage-gate")
    expected_gate_command = (
        "$(VENV_PYTHON) scripts/coverage_gate.py --coverage-dir $(COVERAGE_DATA_DIR)"
    )
    if expected_gate_command not in coverage_gate_block:
        errors.append(f"Makefile coverage-gate target must run `{expected_gate_command}`")
    return errors


def _validate_security_audit_target(makefile: str) -> list[str]:
    errors: list[str] = []
    security_audit = _target_block(makefile, "security-audit")
    if "-m pip_audit" not in security_audit:
        errors.append("Makefile security-audit target must run pip-audit")
    if "requirements/runtime-resolved.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit resolved runtime lock")
    if "requirements/shared-runtime.lock.txt" in security_audit:
        errors.append("Makefile security-audit target must not audit direct-only runtime lock")
    if "requirements/ci-tooling.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit CI tooling lock")
    return errors


def _validate_install_target(makefile: str) -> list[str]:
    errors: list[str] = []
    install = _target_block(makefile, "install")
    expected_command = (
        "$(VENV_PYTHON) -m pip install --constraint "
        'requirements/runtime-resolved.lock.txt -e ".[dev]"'
    )
    if expected_command not in install:
        errors.append(
            "Makefile install target must constrain dev installation with "
            "`requirements/runtime-resolved.lock.txt`"
        )
    return errors


def _validate_script_targets(makefile: str) -> list[str]:
    errors: list[str] = []
    for target, script in SCRIPT_TARGET_EXPECTATIONS.items():
        if script not in _target_block(makefile, target):
            errors.append(f"Makefile {target} target must run `{script}`")
    return errors


def _validate_support_targets(makefile: str) -> list[str]:
    errors = _validate_implementation_proof_readiness_target(makefile)
    runtime_preview_check = _target_block(makefile, "runtime-trust-telemetry-preview-check")
    if "scripts/generate_runtime_trust_telemetry_preview.py" not in runtime_preview_check:
        errors.append(
            "Makefile runtime-trust-telemetry-preview-check target must run "
            "`scripts/generate_runtime_trust_telemetry_preview.py`"
        )
    runtime_snapshot_check = _target_block(makefile, "runtime-trust-telemetry-snapshot-check")
    if "scripts/generate_runtime_trust_telemetry_snapshot.py" not in runtime_snapshot_check:
        errors.append(
            "Makefile runtime-trust-telemetry-snapshot-check target must run "
            "`scripts/generate_runtime_trust_telemetry_snapshot.py`"
        )
    clean_block = _target_block(makefile, "clean")
    if "scripts/clean_generated_artifacts.py" not in clean_block:
        errors.append("Makefile clean target must run `scripts/clean_generated_artifacts.py`")
    return errors


def validate_makefile(makefile: str) -> list[str]:
    return [
        *_validate_required_makefile_targets(makefile),
        *_validate_aggregate_makefile_targets(makefile),
        *_validate_test_targets(makefile),
        *_validate_install_target(makefile),
        *_validate_security_audit_target(makefile),
        *validate_release_evidence_targets(makefile),
        *_validate_script_targets(makefile),
        *_validate_support_targets(makefile),
    ]


def validate_workflows(workflows_dir: Path) -> list[str]:
    errors: list[str] = []
    for workflow_name, required_fragments in WORKFLOW_EXPECTATIONS.items():
        workflow_path = workflows_dir / workflow_name
        if not workflow_path.exists():
            errors.append(f"Missing workflow `{workflow_name}`")
            continue
        content = _read(workflow_path)
        for fragment in required_fragments:
            if fragment not in content:
                errors.append(f"{workflow_name} missing `{fragment}`")
        for prohibited in PROHIBITED_WORKFLOW_PATTERNS.get(workflow_name, ()):
            if prohibited in content:
                errors.append(f"{workflow_name} must not contain `{prohibited}`")
        errors.extend(_validate_job_timeouts(workflow_name, content))
        errors.extend(_validate_action_pins(workflow_name, content))
    return errors


def _validate_action_pins(workflow_name: str, workflow: str) -> list[str]:
    errors: list[str] = []
    for line_number, line in enumerate(workflow.splitlines(), start=1):
        match = ACTION_USE_RE.search(line)
        if not match:
            continue

        action = match.group("action")
        ref = match.group("ref")
        if not FULL_SHA_RE.fullmatch(ref):
            errors.append(
                f"{workflow_name}:{line_number}: {action} must use an immutable "
                "40-character SHA pin, not a floating tag or branch"
            )
            continue

        expected = PINNED_ACTIONS.get(action)
        if expected is None:
            continue

        expected_sha, expected_version = expected
        if ref != expected_sha:
            errors.append(
                f"{workflow_name}:{line_number}: {action} must pin {expected_sha} "
                f"for verified {expected_version}"
            )
        if f"# {expected_version}" not in line:
            errors.append(
                f"{workflow_name}:{line_number}: {action} SHA pin must carry "
                f"`# {expected_version}` provenance"
            )
    return errors


def _validate_job_timeouts(workflow_name: str, workflow: str) -> list[str]:
    errors: list[str] = []
    job_blocks = _job_blocks(workflow)
    if not job_blocks:
        return [f"{workflow_name} must define at least one parseable job"]
    for job_name, job_block in job_blocks.items():
        timeout_match = re.search(r"^    timeout-minutes:\s*(?P<value>\d+)\s*$", job_block, re.M)
        if not timeout_match:
            errors.append(f"{workflow_name} job `{job_name}` missing timeout-minutes")
            continue
        timeout = int(timeout_match.group("value"))
        if timeout < 1 or timeout > 60:
            errors.append(
                f"{workflow_name} job `{job_name}` timeout-minutes must be between 1 and 60"
            )
    return errors


def _job_blocks(workflow: str) -> dict[str, str]:
    lines = workflow.splitlines()
    try:
        jobs_index = next(
            index for index, line in enumerate(lines) if re.match(r"^\s*jobs\s*:\s*(?:#.*)?$", line)
        )
    except StopIteration:
        return {}

    blocks: dict[str, list[str]] = {}
    current_job: str | None = None
    for line in lines[jobs_index + 1 :]:
        job_match = re.match(r"^  (?P<job>[A-Za-z0-9_-]+):\s*$", line)
        if job_match:
            current_job = job_match.group("job")
            blocks[current_job] = [line]
            continue
        if current_job is not None:
            blocks[current_job].append(line)
    return {job: "\n".join(block_lines) for job, block_lines in blocks.items()}


def validate_ci_contract() -> list[str]:
    if not MAKEFILE_PATH.exists():
        return [f"Missing {MAKEFILE_PATH.relative_to(ROOT).as_posix()}"]
    dockerfile_errors: list[str] = []
    if not DOCKERFILE_PATH.exists():
        dockerfile_errors.append("Missing Dockerfile")
        dockerfile = ""
    else:
        dockerfile = _read(DOCKERFILE_PATH)
    dependency_errors: list[str] = []
    if not PYPROJECT_PATH.exists():
        dependency_errors.append("Missing pyproject.toml")
        pyproject = ""
    else:
        pyproject = _read(PYPROJECT_PATH)
    if not CI_TOOLING_LOCK_PATH.exists():
        dependency_errors.append("Missing requirements/ci-tooling.lock.txt")
        ci_tooling_lock = ""
    else:
        ci_tooling_lock = _read(CI_TOOLING_LOCK_PATH)
    return [
        *validate_makefile(_read(MAKEFILE_PATH)),
        *dockerfile_errors,
        *validate_dockerfile_runtime(dockerfile),
        *dependency_errors,
        *validate_dependency_governance(pyproject, ci_tooling_lock),
        *validate_security_tab_governance_files(ROOT),
        *validate_workflows(WORKFLOWS_DIR),
        *validate_e2e_suite(E2E_TESTS_DIR),
    ]


def main() -> int:
    errors = validate_ci_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("CI contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
