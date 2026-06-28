from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(Path(__file__).resolve().parent))
from ci_contract_gate_expectations import (  # noqa: E402
    GENERATED_READINESS_ARTIFACTS,
    PASSED_READINESS_ARTIFACTS,
    REQUIRED_READINESS_WIRING,
)

MAKEFILE_PATH = ROOT / "Makefile"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
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

REQUIRED_LINT_TARGETS = (
    "ci-contract-gate",
    "repository-hygiene-gate",
    "maintainability-gate",
    "documentation-contract-gate",
    "quality-scorecard-gate",
    "monetary-float-guard",
    "no-sensitive-content-guard",
    "source-observability-contract-gate",
    "signal-api-contract-gate",
    "operation-metric-contract-gate",
    "ai-model-risk-ops-contract-gate",
    "implementation-truth-gate",
    "data-mesh-contract-gate",
    "mesh-policy-proof-contract-gate",
    "opportunity-archetype-contract-gate",
    "downstream-realization-contract-gate",
    "downstream-route-contract-proof-gate",
    "outbox-event-contract-gate",
    "outbox-consumer-contract-gate",
    "migration-contract-gate",
    "migration-execution-gate",
    "durable-repository-proof-contract-gate",
    "runtime-trust-telemetry-proof-contract-gate",
    "ai-lineage-store-proof-contract-gate",
    "ai-workflow-pack-registration-proof-contract-gate",
    "ai-workflow-pack-runtime-execution-proof-contract-gate",
    "report-intake-route-proof-contract-gate",
    "report-materialization-proof-contract-gate",
    "workbench-read-path-proof-contract-gate",
    "gateway-workbench-operational-proof-contract-gate",
    "gateway-workbench-discovery-proof-contract-gate",
    "outbox-broker-proof-contract-gate",
    "outbox-consumer-runtime-proof-contract-gate",
    "outbox-platform-mesh-event-publication-proof-contract-gate",
    "platform-mesh-onboarding-proof-contract-gate",
    "source-ingestion-worker-check",
    "source-ingestion-scheduled-worker-check",
    "source-ingestion-live-proof-contract-gate",
    "risk-concentration-live-proof-contract-gate",
    "core-benchmark-assignment-live-proof-contract-gate",
    "core-portfolio-state-live-proof-contract-gate",
    "bond-maturity-live-proof-contract-gate",
    "missing-benchmark-live-proof-contract-gate",
    "missing-benchmark-performance-readiness-proof-contract-gate",
    "low-income-core-cashflow-live-proof-contract-gate",
    "manage-mandate-live-proof-contract-gate",
    "missing-suitability-live-proof-contract-gate",
    "missing-risk-profile-live-proof-contract-gate",
    "performance-underperformance-live-proof-contract-gate",
    "runtime-trust-telemetry-snapshot-check",
    "supported-features-gate",
    "endpoint-certification-gate",
)
REQUIRED_TARGETS = (
    *REQUIRED_LINT_TARGETS,
    "postgres-integration-gate",
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
REQUIRED_TEST_SELECTORS = {
    "UNIT_TESTS ?= tests/unit": "Makefile must define UNIT_TESTS for scoped unit validation",
    "INTEGRATION_TESTS ?= tests/integration": (
        "Makefile must define INTEGRATION_TESTS for scoped integration validation"
    ),
    "E2E_TESTS ?= tests/e2e": "Makefile must define E2E_TESTS for scoped e2e validation",
}

WORKFLOW_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "feature-lane.yml": (
        "permissions:\n  contents: read",
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0",
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0",
        "reviewdog/action-actionlint@6fb7acc99f4a1008869fa8a0f09cfca740837d9d # v1.72.0",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "pytest tests/unit",
    ),
    "pr-merge-gate.yml": (
        "permissions:\n  contents: read",
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0",
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0",
        "reviewdog/action-actionlint@6fb7acc99f4a1008869fa8a0f09cfca740837d9d # v1.72.0",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1",
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1",
        "docker/setup-buildx-action@d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5 # v4.1.0",
        "suite: unit",
        "suite: integration",
        "suite: e2e",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "coverage report --fail-under=99",
        "PostgreSQL Runtime Proof",
        "postgres:18-alpine",
        "LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED",
        "LOTUS_IDEA_POSTGRES_INTEGRATION_URL",
        "make postgres-integration-gate",
        "make docker-build",
        "NODE_OPTIONS: --no-deprecation",
    ),
    "main-releasability.yml": (
        "workflow_dispatch:",
        "permissions:\n  contents: read",
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0",
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0",
        "reviewdog/action-actionlint@6fb7acc99f4a1008869fa8a0f09cfca740837d9d # v1.72.0",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1",
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1",
        "docker/setup-buildx-action@d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5 # v4.1.0",
        "suite: unit",
        "suite: integration",
        "suite: e2e",
        "make lint",
        "make typecheck",
        "make architecture-boundary-gate",
        "make openapi-gate",
        "make security-audit",
        "coverage report --fail-under=99",
        "PostgreSQL Runtime Proof",
        "postgres:18-alpine",
        "LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED",
        "LOTUS_IDEA_POSTGRES_INTEGRATION_URL",
        "make postgres-integration-gate",
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
        "Resource not accessible by personal access token",
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
    "feature-lane.yml": (
        "pull_request_target:",
        "contents: write",
        "pull-requests: write",
        "continue-on-error:",
    ),
    "pr-merge-gate.yml": (
        "pull_request_target:",
        "contents: write",
        "pull-requests: write",
        "continue-on-error:",
    ),
    "main-releasability.yml": (
        "pull_request_target:",
        "contents: write",
        "pull-requests: write",
        "continue-on-error:",
    ),
    "pr-auto-merge.yml": ("continue-on-error:",),
    "merged-pr-main-releasability.yml": ("continue-on-error:",),
}
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


def validate_makefile(makefile: str) -> list[str]:
    errors: list[str] = []
    for target in REQUIRED_TARGETS:
        if not re.search(rf"^{re.escape(target)}:", makefile, re.MULTILINE):
            errors.append(f"Makefile missing required target `{target}`")
    for selector, error in REQUIRED_TEST_SELECTORS.items():
        if selector not in makefile:
            errors.append(error)
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
    test_target_expectations = {
        "test-unit": "$(VENV_PYTHON) -m pytest $(UNIT_TESTS)",
        "test-integration": "$(VENV_PYTHON) -m pytest $(INTEGRATION_TESTS)",
        "test-e2e": "$(VENV_PYTHON) -m pytest $(E2E_TESTS)",
    }
    for target, expected_command in test_target_expectations.items():
        if expected_command not in _target_block(makefile, target):
            errors.append(f"Makefile {target} target must run `{expected_command}`")

    coverage_block = _target_block(makefile, "test-coverage")
    for selector in ("$(UNIT_TESTS)", "$(INTEGRATION_TESTS)", "$(E2E_TESTS)"):
        if selector not in coverage_block:
            errors.append(f"Makefile test-coverage target must use `{selector}`")
    security_audit = _target_block(makefile, "security-audit")
    if "-m pip_audit" not in security_audit:
        errors.append("Makefile security-audit target must run pip-audit")
    if "requirements/shared-runtime.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit shared runtime lock")
    if "requirements/ci-tooling.lock.txt" not in security_audit:
        errors.append("Makefile security-audit target must audit CI tooling lock")

    script_target_expectations = {
        "source-ingestion-worker-check": "scripts/source_ingestion_worker_contract_gate.py",
        "source-ingestion-scheduled-worker-check": "scripts/source_ingestion_scheduled_worker_contract_gate.py",
        "source-ingestion-live-proof-contract-gate": "scripts/source_ingestion_live_proof_contract_gate.py",
        "risk-concentration-live-proof-contract-gate": "scripts/risk_concentration_live_proof_contract_gate.py",
        "performance-underperformance-live-proof-contract-gate": "scripts/performance_underperformance_live_proof_contract_gate.py",
        "core-benchmark-assignment-live-proof-contract-gate": "scripts/core_benchmark_assignment_live_proof_contract_gate.py",
        "core-portfolio-state-live-proof-contract-gate": "scripts/core_portfolio_state_live_proof_contract_gate.py",
        "bond-maturity-live-proof-contract-gate": "scripts/bond_maturity_live_proof_contract_gate.py",
        "missing-benchmark-live-proof-contract-gate": "scripts/missing_benchmark_live_proof_contract_gate.py",
        "missing-benchmark-performance-readiness-proof-contract-gate": (
            "scripts/missing_benchmark_performance_readiness_proof_contract_gate.py"
        ),
        "low-income-core-cashflow-live-proof-contract-gate": "scripts/low_income_core_cashflow_live_proof_contract_gate.py",
        "risk-drawdown-live-proof-contract-gate": "scripts/risk_drawdown_live_proof_contract_gate.py",
        "manage-mandate-live-proof-contract-gate": "scripts/manage_mandate_live_proof_contract_gate.py",
        "mandate-restriction-live-proof-contract-gate": (
            "scripts/mandate_restriction_live_proof_contract_gate.py"
        ),
        "missing-suitability-live-proof-contract-gate": "scripts/missing_suitability_live_proof_contract_gate.py",
        "missing-risk-profile-live-proof-contract-gate": "scripts/missing_risk_profile_live_proof_contract_gate.py",
        "mesh-policy-proof-contract-gate": "scripts/mesh_policy_proof_contract_gate.py",
        "opportunity-archetype-contract-gate": ("scripts/opportunity_archetype_contract_gate.py"),
        "durable-repository-proof-contract-gate": "scripts/durable_repository_proof_contract_gate.py",
        "runtime-trust-telemetry-proof-contract-gate": "scripts/runtime_trust_telemetry_proof_contract_gate.py",
        "ai-lineage-store-proof-contract-gate": "scripts/ai_lineage_store_proof_contract_gate.py",
        "ai-workflow-pack-registration-proof-contract-gate": "scripts/ai_workflow_pack_registration_proof_contract_gate.py",
        "ai-workflow-pack-runtime-execution-proof-contract-gate": "scripts/ai_workflow_pack_runtime_execution_proof_contract_gate.py",
        "downstream-route-contract-proof-gate": "scripts/downstream_route_contract_proof_gate.py",
        "report-intake-route-proof-contract-gate": "scripts/report_intake_route_proof_contract_gate.py",
        "report-materialization-proof-contract-gate": "scripts/report_materialization_proof_contract_gate.py",
        "workbench-read-path-proof-contract-gate": "scripts/workbench_read_path_proof_contract_gate.py",
        "gateway-workbench-operational-proof-contract-gate": (
            "scripts/gateway_workbench_operational_proof_contract_gate.py"
        ),
        "gateway-workbench-discovery-proof-contract-gate": (
            "scripts/gateway_workbench_discovery_proof_contract_gate.py"
        ),
        "outbox-broker-proof-contract-gate": "scripts/outbox_broker_proof_contract_gate.py",
        "outbox-consumer-runtime-proof-contract-gate": (
            "scripts/outbox_consumer_runtime_proof_contract_gate.py"
        ),
        "outbox-platform-mesh-event-publication-proof-contract-gate": (
            "scripts/outbox_platform_mesh_event_publication_proof_contract_gate.py"
        ),
        "outbox-consumer-contract-gate": "scripts/outbox_consumer_contract_gate.py",
        "signal-api-contract-gate": "scripts/signal_api_contract_gate.py",
        "operation-metric-contract-gate": "scripts/operation_metric_contract_gate.py",
        "ai-model-risk-ops-contract-gate": "scripts/ai_model_risk_operations_contract_gate.py",
    }
    for target, script in script_target_expectations.items():
        if script not in _target_block(makefile, target):
            errors.append(f"Makefile {target} target must run `{script}`")
    errors.extend(_validate_implementation_proof_readiness_target(makefile))
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
