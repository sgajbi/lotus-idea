from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_architecture_boundary_gate_is_blocking_in_local_ci() -> None:
    makefile = _read("Makefile")

    assert "architecture-boundary-gate:" in makefile
    assert "scripts/architecture_boundary_gate.py --mode blocking" in makefile
    assert "check: lint typecheck architecture-boundary-gate" in makefile
    assert "ci: lint typecheck architecture-boundary-gate" in makefile
    assert "ci-contract-gate:" in makefile
    assert "$(MAKE) ci-contract-gate" in makefile
    assert "repository-hygiene-gate:" in makefile
    assert "$(MAKE) repository-hygiene-gate" in makefile
    assert "maintainability-gate:" in makefile
    assert "$(MAKE) maintainability-gate" in makefile
    assert "duplicate-implementation-inventory:" in makefile
    assert "scripts/duplicate_implementation_inventory.py" in makefile
    assert "private-import-boundary-gate:" in makefile
    assert "$(MAKE) private-import-boundary-gate" in makefile
    assert "documentation-contract-gate:" in makefile
    assert "$(MAKE) documentation-contract-gate" in makefile
    assert "quality-scorecard-gate:" in makefile
    assert "$(MAKE) quality-scorecard-gate" in makefile
    assert "monetary-float-guard:" in makefile
    assert "$(MAKE) monetary-float-guard" in makefile
    assert "no-sensitive-content-guard:" in makefile
    assert "$(MAKE) no-sensitive-content-guard" in makefile
    assert "runtime-dependency-closure-gate:" in makefile
    assert "$(MAKE) runtime-dependency-closure-gate" in makefile
    assert "source-observability-contract-gate:" in makefile
    assert "$(MAKE) source-observability-contract-gate" in makefile
    assert "api-route-metadata-gate:" in makefile
    assert "$(MAKE) api-route-metadata-gate" in makefile
    assert "api-problem-details-boundary-gate:" in makefile
    assert "$(MAKE) api-problem-details-boundary-gate" in makefile
    assert "api-idempotency-boundary-gate:" in makefile
    assert "$(MAKE) api-idempotency-boundary-gate" in makefile
    assert "api-camel-model-boundary-gate:" in makefile
    assert "$(MAKE) api-camel-model-boundary-gate" in makefile
    assert "openapi-problem-details-example-gate:" in makefile
    assert "api-temporal-validation-boundary-gate:" in makefile
    assert "$(MAKE) api-temporal-validation-boundary-gate" in makefile
    assert "scripts/api_temporal_validation_boundary_gate.py" in makefile
    assert "$(MAKE) openapi-problem-details-example-gate" in makefile
    assert "signal-api-contract-gate:" in makefile
    assert "$(MAKE) signal-api-contract-gate" in makefile
    assert "implementation-truth-gate:" in makefile
    assert "$(MAKE) implementation-truth-gate" in makefile
    assert "data-mesh-contract-gate:" in makefile
    assert "$(MAKE) data-mesh-contract-gate" in makefile
    assert "migration-contract-gate:" in makefile
    assert "$(MAKE) migration-contract-gate" in makefile
    assert "migration-execution-gate:" in makefile
    assert "$(MAKE) migration-execution-gate" in makefile
    assert "scripts/run_migrations.py --direction apply --dry-run" in makefile
    assert "scripts/run_migrations.py --direction rollback --dry-run" in makefile
    assert "source-ingestion-worker-check:" in makefile
    assert "$(MAKE) source-ingestion-worker-check" in makefile
    assert "scripts/source_ingestion_worker_contract_gate.py" in makefile
    assert "test-unit-coverage:" in makefile
    assert "test-integration-coverage:" in makefile
    assert "test-e2e-coverage:" in makefile
    assert (
        "test-coverage: test-unit-coverage test-integration-coverage test-e2e-coverage" in makefile
    )
    assert "postgres-integration-gate:" in makefile
    assert "tests/integration/test_postgres_runtime_integration.py" in makefile
    assert (
        "check: lint typecheck architecture-boundary-gate openapi-gate "
        "migration-contract-gate migration-execution-gate"
    ) in makefile
    assert (
        "ci: lint typecheck architecture-boundary-gate openapi-gate "
        "migration-contract-gate migration-execution-gate"
    ) in makefile
    assert (
        "ci-release: ci implementation-proof-readiness-check "
        "runtime-trust-telemetry-snapshot-check postgres-integration-gate "
        "docker-build container-runtime-smoke container-image-scan release-sbom"
    ) in makefile


def test_architecture_boundary_gate_runs_in_github_lanes() -> None:
    for workflow in (
        ".github/workflows/feature-lane.yml",
        ".github/workflows/pr-merge-gate.yml",
        ".github/workflows/main-releasability.yml",
    ):
        content = _read(workflow)
        assert "Architecture Boundary Gate" in content
        assert "make architecture-boundary-gate" in content


def test_architecture_boundary_gate_protects_runtime_composition_layer() -> None:
    module = _load_architecture_boundary_gate()

    runtime_rule = module.LAYER_RULES["runtime"]

    assert "app.api" in runtime_rule["forbidden_prefixes"]
    assert "fastapi" in runtime_rule["forbidden_prefixes"]
    assert "framework" in runtime_rule["description"]


def test_architecture_boundary_gate_detects_runtime_api_leakage(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    source_root = tmp_path / "src" / "app"
    runtime_path = source_root / "runtime" / "bad_runtime.py"
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_text(
        "from fastapi import Depends\nfrom app.api.idea_signals import router\n"
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SRC_ROOT", source_root)

    violations = module.validate_architecture_boundaries()

    assert {(violation["layer"], violation["import"]) for violation in violations} == {
        ("runtime", "app.api.idea_signals"),
        ("runtime", "fastapi"),
    }


def test_architecture_boundary_gate_allows_api_runtime_dependency_facade(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    source_root = tmp_path / "src" / "app"
    facade_path = source_root / "api" / "runtime_dependencies.py"
    facade_path.parent.mkdir(parents=True)
    facade_path.write_text(
        "from app.runtime.repository_state import get_idea_repository\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SRC_ROOT", source_root)
    monkeypatch.setattr(module, "API_RUNTIME_DEPENDENCY_FACADE", facade_path)

    assert module.validate_architecture_boundaries() == []


def test_architecture_boundary_gate_blocks_api_runtime_import_outside_facade(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    source_root = tmp_path / "src" / "app"
    route_path = source_root / "api" / "unsafe_route.py"
    route_path.parent.mkdir(parents=True)
    route_path.write_text(
        "from app.runtime.repository_state import get_idea_repository\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SRC_ROOT", source_root)
    monkeypatch.setattr(
        module, "API_RUNTIME_DEPENDENCY_FACADE", source_root / "api" / "runtime_dependencies.py"
    )

    violations = module.validate_architecture_boundaries()

    assert len(violations) == 1
    violation = violations[0]
    assert violation["path"].replace("\\", "/") == "src/app/api/unsafe_route.py"
    assert violation["module"] == "app.api.unsafe_route"
    assert violation["layer"] == "api"
    assert violation["import"] == "app.runtime.repository_state"
    assert violation["rule"] == module.LAYER_RULES["api"]["description"]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_passes_current_repository_contract() -> None:
    module = _load_ci_contract_gate()

    assert module.validate_ci_contract() == []


def test_ci_contract_gate_blocks_missing_merge_grade_checks() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("security-audit", "security-report")

    errors = module.validate_makefile(makefile)

    assert "Makefile missing required target `security-audit`" in errors
    assert "Makefile ci target missing `security-audit`" in errors


def test_ci_contract_gate_blocks_unconstrained_install_target() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace(
        '$(VENV_PYTHON) -m pip install --constraint requirements/runtime-resolved.lock.txt -e ".[dev]"',
        '$(VENV_PYTHON) -m pip install -e ".[dev]"',
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile install target must constrain dev installation with "
        "`requirements/runtime-resolved.lock.txt`"
    ) in errors


def test_ci_contract_gate_blocks_missing_full_lane_release_proof_dependencies() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace(
        "ci-release: ci implementation-proof-readiness-check "
        "runtime-trust-telemetry-snapshot-check postgres-integration-gate "
        "docker-build container-runtime-smoke container-image-scan release-sbom",
        "ci-release: ci",
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile ci-release target missing `implementation-proof-readiness-check`" in errors
    assert "Makefile ci-release target missing `runtime-trust-telemetry-snapshot-check`" in errors
    assert "Makefile ci-release target missing `postgres-integration-gate`" in errors
    assert "Makefile ci-release target missing `docker-build`" in errors
    assert "Makefile ci-release target missing `container-runtime-smoke`" in errors
    assert "Makefile ci-release target missing `container-image-scan`" in errors
    assert "Makefile ci-release target missing `release-sbom`" in errors


def test_ci_contract_gate_blocks_unpinned_release_sbom_tooling() -> None:
    module = _load_ci_contract_gate()

    errors = module.validate_dependency_governance(
        pyproject=_read("pyproject.toml").replace('"cyclonedx-bom==7.3.0",', ""),
        ci_tooling_lock=_read("requirements/ci-tooling.lock.txt").replace(
            "cyclonedx-bom==7.3.0\n", ""
        ),
    )

    assert "pyproject.toml dev dependencies must pin `cyclonedx-bom==7.3.0`" in errors
    assert "requirements/ci-tooling.lock.txt must pin `cyclonedx-bom==7.3.0`" in errors


def test_ci_contract_gate_blocks_ungoverned_release_evidence_targets() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        _read("Makefile")
        .replace("$(VENV_PYTHON) -m cyclonedx_py requirements", "cyclonedx-py requirements")
        .replace("requirements/runtime-resolved.lock.txt", "requirements/shared-runtime.lock.txt")
        .replace(" --pyproject pyproject.toml", "")
        .replace(" --output-reproducible", "")
        .replace(
            "mkdir -p $(dir $(CONTAINER_SCAN_OUTPUT))",
            "$(VENV_PYTHON) -c \"from pathlib import Path; Path('$(CONTAINER_SCAN_OUTPUT)').parent.mkdir(parents=True, exist_ok=True)\"",
        )
        .replace("DOCKER_SOCKET_MOUNT := /var/run/docker.sock:/var/run/docker.sock", "")
        .replace("DOCKER_SOCKET_MOUNT := //var/run/docker.sock:/var/run/docker.sock", "")
        .replace("DOCKER_WORKDIR := /work", "")
        .replace("DOCKER_WORKDIR := //work", "")
        .replace("$(DOCKER_SOCKET_MOUNT)", "/var/run/docker.sock:/var/run/docker.sock")
        .replace("$(DOCKER_WORKDIR)", "/work")
        .replace("aquasec/trivy:0.71.2", "aquasec/trivy:latest")
        .replace("--exit-code 1", "--exit-code 0")
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile release-sbom target must run pinned venv `cyclonedx_py requirements`" in errors
    assert (
        "Makefile release-sbom target must use the resolved runtime dependency lockfile"
    ) in errors
    assert (
        "Makefile release-sbom target must not use the direct-only shared runtime lockfile"
        in errors
    )
    assert "Makefile release-sbom target must attach project metadata" in errors
    assert "Makefile release-sbom target must generate reproducible SBOM output" in errors
    assert (
        "Makefile container-image-scan target must not require the repository Python venv" in errors
    )
    assert (
        "Makefile container-image-scan target must create the scan evidence directory without requiring a Python venv"
        in errors
    )
    assert "Makefile must define the Linux Docker socket mount for image scanning" in errors
    assert "Makefile must define the Windows Docker Desktop socket mount for scanning" in errors
    assert "Makefile must define the Linux container scan workdir" in errors
    assert "Makefile must define the Windows-safe container scan workdir" in errors
    assert (
        "Makefile container-image-scan target must use the governed Docker socket mount" in errors
    )
    assert "Makefile container-image-scan target must use the governed container workdir" in errors
    assert "Makefile must govern `TRIVY_IMAGE` as `aquasec/trivy:0.71.2`" in errors
    assert "Makefile container-image-scan target must fail on governed findings" in errors


def test_ci_contract_gate_blocks_ambiguous_environment_release_sbom() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace(
        "$(VENV_PYTHON) -m cyclonedx_py requirements requirements/runtime-resolved.lock.txt --pyproject pyproject.toml --output-reproducible",
        "$(VENV_PYTHON) -m cyclonedx_py environment",
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile release-sbom target must run pinned venv `cyclonedx_py requirements`" in errors
    assert "Makefile release-sbom target must not generate an ambiguous environment SBOM" in errors


def test_ci_contract_gate_blocks_missing_container_runtime_smoke() -> None:
    module = _load_ci_contract_gate()
    makefile = (
        _read("Makefile")
        .replace("container-runtime-smoke", "container-runtime-optional")
        .replace("CONTAINER_SMOKE_TIMEOUT_SECONDS ?= 45", "")
        .replace("--startup-timeout-seconds $(CONTAINER_SMOKE_TIMEOUT_SECONDS)", "")
    )

    errors = module.validate_makefile(makefile)

    assert "Makefile missing required target `container-runtime-smoke`" in errors
    assert "Makefile must govern the container runtime smoke startup timeout" in errors
    assert "Makefile container-runtime-smoke target must use the governed startup timeout" in errors


def test_ci_contract_gate_blocks_missing_repository_hygiene_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) repository-hygiene-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) repository-hygiene-gate`" in errors


def test_ci_contract_gate_blocks_missing_private_import_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) private-import-boundary-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) private-import-boundary-gate`" in errors


def test_ci_contract_gate_blocks_missing_source_observability_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) source-observability-contract-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) source-observability-contract-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_route_metadata_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) api-route-metadata-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) api-route-metadata-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_problem_details_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) api-problem-details-boundary-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) api-problem-details-boundary-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_idempotency_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) api-idempotency-boundary-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) api-idempotency-boundary-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_camel_model_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) api-camel-model-boundary-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) api-camel-model-boundary-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_signal_model_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) api-signal-model-boundary-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) api-signal-model-boundary-gate`" in errors


def test_ci_contract_gate_blocks_missing_api_temporal_validation_boundary_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace(
        "$(MAKE) api-temporal-validation-boundary-gate",
        "",
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) api-temporal-validation-boundary-gate`" in errors
    )


def test_ci_contract_gate_blocks_missing_openapi_problem_details_example_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) openapi-problem-details-example-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) openapi-problem-details-example-gate`" in errors


def test_ci_contract_gate_blocks_missing_signal_api_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) signal-api-contract-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) signal-api-contract-gate`" in errors


def test_ci_contract_gate_blocks_missing_caller_context_contract_gate() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace("$(MAKE) caller-context-contract-gate", "")

    errors = module.validate_makefile(makefile)

    assert "Makefile lint target must call `$(MAKE) caller-context-contract-gate`" in errors


def test_ci_contract_gate_blocks_downgraded_source_ingestion_worker_check() -> None:
    module = _load_ci_contract_gate()
    makefile = _read("Makefile").replace(
        "scripts/source_ingestion_worker_contract_gate.py",
        "scripts/run_source_ingestion_worker.py",
    )

    errors = module.validate_makefile(makefile)

    assert (
        "Makefile source-ingestion-worker-check target must run "
        "`scripts/source_ingestion_worker_contract_gate.py`"
    ) in errors


def test_ci_contract_gate_blocks_write_permissions_in_read_only_lanes(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace("contents: read", "contents: write"),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml must not contain `contents: write`" in errors


def test_ci_contract_gate_requires_merged_pr_main_releasability_dispatch(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    dispatch_workflow = workflow_dir / "merged-pr-main-releasability.yml"
    dispatch_workflow.write_text(
        dispatch_workflow.read_text(encoding="utf-8").replace(
            "gh workflow run main-releasability.yml",
            "echo missing dispatch",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert (
        "merged-pr-main-releasability.yml missing `gh workflow run main-releasability.yml`"
        in errors
    )


def test_ci_contract_gate_requires_non_suppressed_auto_merge_token(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    auto_merge = workflow_dir / "pr-auto-merge.yml"
    auto_merge.write_text(
        auto_merge.read_text(encoding="utf-8").replace(
            "secrets.LOTUS_AUTOMERGE_TOKEN",
            "github.token",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "pr-auto-merge.yml missing `secrets.LOTUS_AUTOMERGE_TOKEN`" in errors


def test_ci_contract_gate_requires_postgres_runtime_proof(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    pr_merge_gate = workflow_dir / "pr-merge-gate.yml"
    pr_merge_gate.write_text(
        pr_merge_gate.read_text(encoding="utf-8").replace(
            "run: make postgres-integration-gate",
            "run: echo missing postgres proof",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "pr-merge-gate.yml missing `make postgres-integration-gate`" in errors


def test_ci_contract_gate_requires_job_timeouts(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8")
        .replace("jobs:", "jobs: # generated lanes", 1)
        .replace("    timeout-minutes: 10\n", "", 1),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml job `workflow-lint` missing timeout-minutes" in errors


def test_ci_contract_gate_blocks_soft_failed_workflow_jobs(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace(
            "    timeout-minutes: 10\n",
            "    timeout-minutes: 10\n    continue-on-error: ${{ true }}\n",
            1,
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml must not contain `continue-on-error:`" in errors


def test_ci_contract_gate_blocks_raw_workflow_pytest_shortcuts(tmp_path: Path) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    for workflow_name in module.WORKFLOW_EXPECTATIONS:
        source = ROOT / ".github" / "workflows" / workflow_name
        target = workflow_dir / workflow_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    feature_lane = workflow_dir / "feature-lane.yml"
    feature_lane.write_text(
        feature_lane.read_text(encoding="utf-8").replace(
            "run: make test-unit",
            "run: ./.venv/bin/python -m pytest tests/unit",
        ),
        encoding="utf-8",
    )

    errors = module.validate_workflows(workflow_dir)

    assert "feature-lane.yml missing `make test-unit`" in errors
    assert "feature-lane.yml must not contain `run: ./.venv/bin/python -m pytest`" in errors


def test_ci_contract_gate_rejects_workflows_without_parseable_jobs() -> None:
    module = _load_ci_contract_gate()

    errors = module.validate_workflows(ROOT / "tests" / "fixtures" / "missing-workflow-dir")
    timeout_errors = module._validate_job_timeouts("synthetic.yml", "name: Synthetic\n")

    assert errors
    assert timeout_errors == ["synthetic.yml must define at least one parseable job"]


def test_generated_quality_reports_do_not_dirty_worktree() -> None:
    gitignore = _read(".gitignore")

    assert "quality/architecture_boundary_report.json" in gitignore
    assert "quality/baseline_report.json" in gitignore
    assert "quality/baseline_report.md" in gitignore


def _load_api_route_metadata_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_route_metadata_gate.py"
    spec = importlib.util.spec_from_file_location("api_route_metadata_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_openapi_problem_details_example_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "openapi_problem_details_example_gate.py"
    spec = importlib.util.spec_from_file_location(
        "openapi_problem_details_example_gate", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openapi_problem_details_example_gate_passes_current_repository() -> None:
    module = _load_openapi_problem_details_example_gate()

    assert module.validate_problem_details_examples() == []


def test_api_route_metadata_gate_passes_current_repository() -> None:
    module = _load_api_route_metadata_gate()

    assert module.validate_api_route_metadata(ROOT) == []


def test_api_route_metadata_gate_blocks_local_route_metadata_clone(tmp_path: Path) -> None:
    module = _load_api_route_metadata_gate()
    shared_module = tmp_path / "src" / "app" / "api" / "route_metadata.py"
    shared_module.parent.mkdir(parents=True)
    shared_module.write_text(
        "from typing import TypedDict\n\nclass RouteMetadata(TypedDict):\n    path: str\n",
        encoding="utf-8",
    )
    cloned_module = tmp_path / "src" / "app" / "api" / "review_workflow.py"
    cloned_module.write_text(
        "from typing import TypedDict\n\nclass RouteMetadata(TypedDict):\n    path: str\n",
        encoding="utf-8",
    )

    errors = module.validate_api_route_metadata(tmp_path)

    assert errors == [
        "src/app/api/review_workflow.py:3: route metadata TypedDict must be defined once "
        "in `app.api.route_metadata`"
    ]


def _load_architecture_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "architecture_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("architecture_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_blocking_architecture_boundary_gate_does_not_write_report(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    report_path = tmp_path / "architecture_boundary_report.json"

    monkeypatch.setattr(module, "REPORT_PATH", report_path)
    monkeypatch.setattr(module, "validate_architecture_boundaries", lambda: [])
    monkeypatch.setattr(sys, "argv", ["architecture_boundary_gate.py", "--mode", "blocking"])

    assert module.main() == 0

    assert not report_path.exists()
    assert "Architecture boundary gate passed" in capsys.readouterr().out


def test_report_only_architecture_boundary_gate_writes_report(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    module = _load_architecture_boundary_gate()
    report_path = tmp_path / "architecture_boundary_report.json"

    monkeypatch.setattr(module, "REPORT_PATH", report_path)
    monkeypatch.setattr(module, "validate_architecture_boundaries", lambda: [])
    monkeypatch.setattr(sys, "argv", ["architecture_boundary_gate.py", "--mode", "report-only"])

    assert module.main() == 0

    assert report_path.exists()
    assert "Architecture boundary report passed" in capsys.readouterr().out
