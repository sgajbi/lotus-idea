from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = ROOT / "Makefile"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"


REQUIRED_TARGETS = (
    "ci-contract-gate",
    "monetary-float-guard",
    "no-sensitive-content-guard",
    "data-mesh-contract-gate",
    "supported-features-gate",
    "endpoint-certification-gate",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "test-unit",
    "test-integration",
    "test-e2e",
    "test-coverage",
    "coverage-gate",
    "security-audit",
    "docker-build",
)

REQUIRED_LINT_CALLS = (
    "$(MAKE) ci-contract-gate",
    "$(MAKE) monetary-float-guard",
    "$(MAKE) no-sensitive-content-guard",
    "$(MAKE) data-mesh-contract-gate",
    "$(MAKE) supported-features-gate",
    "$(MAKE) endpoint-certification-gate",
)

REQUIRED_CHECK_DEPS = (
    "lint",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "supported-features-gate",
    "endpoint-certification-gate",
    "test",
)

REQUIRED_CI_DEPS = (
    "lint",
    "typecheck",
    "architecture-boundary-gate",
    "openapi-gate",
    "supported-features-gate",
    "endpoint-certification-gate",
    "test-integration",
    "test-e2e",
    "test-coverage",
    "security-audit",
)

WORKFLOW_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "feature-lane.yml": (
        "permissions:\n  contents: read",
        "actions/checkout@v7",
        "actions/setup-python@v6",
        "reviewdog/action-actionlint@v1",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "pytest tests/unit",
    ),
    "pr-merge-gate.yml": (
        "permissions:\n  contents: read",
        "actions/checkout@v7",
        "actions/setup-python@v6",
        "reviewdog/action-actionlint@v1",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "docker/setup-buildx-action@v4",
        "suite: unit",
        "suite: integration",
        "suite: e2e",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "coverage report --fail-under=99",
        "make docker-build",
        "NODE_OPTIONS: --no-deprecation",
    ),
    "main-releasability.yml": (
        "workflow_dispatch:",
        "permissions:\n  contents: read",
        "actions/checkout@v7",
        "actions/setup-python@v6",
        "reviewdog/action-actionlint@v1",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "docker/setup-buildx-action@v4",
        "suite: unit",
        "suite: integration",
        "suite: e2e",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "coverage report --fail-under=99",
        "make docker-build",
        "cyclonedx-py environment",
        "release-evidence.json",
        "main-releasability-release-evidence",
        "NODE_OPTIONS: --no-deprecation",
    ),
    "pr-auto-merge.yml": (
        "pull_request_target:",
        "contents: read",
        "github.event.pull_request.head.repo.fork == false",
        "secrets.LOTUS_AUTOMERGE_TOKEN",
        "LOTUS_AUTOMERGE_TOKEN is required",
        "gh pr merge",
        "--auto --rebase --delete-branch",
    ),
    "merged-pr-main-releasability.yml": (
        "pull_request_target:",
        "types: [closed]",
        "actions: write",
        "contents: read",
        "github.event.pull_request.merged == true",
        "github.event.pull_request.base.ref == 'main'",
        "gh workflow run main-releasability.yml",
        "--ref main",
    ),
}

PROHIBITED_WORKFLOW_PATTERNS: dict[str, tuple[str, ...]] = {
    "feature-lane.yml": ("pull_request_target:", "contents: write", "pull-requests: write"),
    "pr-merge-gate.yml": ("pull_request_target:", "contents: write", "pull-requests: write"),
    "main-releasability.yml": ("pull_request_target:", "contents: write", "pull-requests: write"),
}


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


def validate_makefile(makefile: str) -> list[str]:
    errors: list[str] = []
    for target in REQUIRED_TARGETS:
        if not re.search(rf"^{re.escape(target)}:", makefile, re.MULTILINE):
            errors.append(f"Makefile missing required target `{target}`")

    lint_block = _target_block(makefile, "lint")
    for call in REQUIRED_LINT_CALLS:
        if call not in lint_block:
            errors.append(f"Makefile lint target must call `{call}`")

    check_deps = _target_deps(makefile, "check")
    for dependency in REQUIRED_CHECK_DEPS:
        if dependency not in check_deps:
            errors.append(f"Makefile check target missing `{dependency}`")

    ci_deps = _target_deps(makefile, "ci")
    for dependency in REQUIRED_CI_DEPS:
        if dependency not in ci_deps:
            errors.append(f"Makefile ci target missing `{dependency}`")

    security_audit = _target_block(makefile, "security-audit")
    if "-m pip_audit" not in security_audit:
        errors.append("Makefile security-audit target must run pip-audit")
    if "requirements/shared-runtime.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit shared runtime lock")
    if "requirements/ci-tooling.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit CI tooling lock")
    return errors


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
    return errors


def validate_ci_contract() -> list[str]:
    if not MAKEFILE_PATH.exists():
        return [f"Missing {MAKEFILE_PATH.relative_to(ROOT).as_posix()}"]
    return [*validate_makefile(_read(MAKEFILE_PATH)), *validate_workflows(WORKFLOWS_DIR)]


def main() -> int:
    errors = validate_ci_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("CI contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
