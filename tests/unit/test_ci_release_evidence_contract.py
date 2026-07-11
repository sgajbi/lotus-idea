from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from scripts.ci_release_evidence_contract import (
    validate_compose_build_identity,
    validate_dockerfile_runtime,
    validate_release_evidence_targets,
)

ROOT = Path(__file__).resolve().parents[2]


def test_compose_passes_complete_non_secret_build_identity() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert validate_compose_build_identity(compose) == []
    assert "SECRET" not in "\n".join(
        line for line in compose.splitlines() if "LOTUS_IDEA_BUILD_" in line
    )


def test_compose_build_identity_rejects_missing_commit_and_run_id() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    degraded = compose.replace(
        '        GIT_COMMIT_SHA: "${LOTUS_IDEA_BUILD_GIT_COMMIT_SHA:-unknown}"\n',
        "",
    ).replace(
        '        CI_RUN_ID: "${LOTUS_IDEA_BUILD_RUN_ID:-local}"\n',
        "",
    )

    errors = validate_compose_build_identity(degraded)

    assert "docker-compose.yml must pass governed commit SHA build identity" in errors
    assert "docker-compose.yml must pass governed run ID build identity" in errors


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_workflows(workflow_dir: Path, workflow_name: str, old: str, new: str) -> None:
    workflow_dir.mkdir(parents=True)
    for workflow_path in (ROOT / ".github" / "workflows").glob("*.yml"):
        content = workflow_path.read_text(encoding="utf-8")
        if workflow_path.name == workflow_name:
            content = content.replace(old, new)
        (workflow_dir / workflow_path.name).write_text(content, encoding="utf-8")


def test_ci_contract_gate_blocks_removed_pr_container_image_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "pr-merge-gate.yml",
        "      - name: Scan Docker image\n        run: make container-image-scan\n",
        "",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert "pr-merge-gate.yml missing `make container-image-scan`" in module.validate_ci_contract()


def test_ci_contract_gate_blocks_removed_pr_container_runtime_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "pr-merge-gate.yml",
        "      - name: Smoke test Docker runtime\n        run: make container-runtime-smoke\n",
        "",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert "pr-merge-gate.yml missing `make container-runtime-smoke`" in (
        module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_main_container_runtime_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        "      - name: Smoke test Docker runtime\n        run: make container-runtime-smoke\n",
        "",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert "main-releasability.yml missing `make container-runtime-smoke`" in (
        module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_main_release_scan_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        "            output/security/container-image-scan.trivy.json\n",
        "",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        "main-releasability.yml missing `            output/security/container-image-scan.trivy.json`"
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_inline_cyclonedx_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        "        run: make release-sbom",
        "        run: ./.venv/bin/python -m pip install cyclonedx-bom",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    errors = module.validate_ci_contract()

    assert "main-releasability.yml missing `make release-sbom`" in errors
    assert "main-releasability.yml must not contain `pip install cyclonedx-bom`" in errors


def test_ci_contract_gate_blocks_removed_container_provenance_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '          docker pull "$CONTAINER_BASE_IMAGE" >/dev/null\n',
        "",
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        'main-releasability.yml missing `docker pull "$CONTAINER_BASE_IMAGE"`'
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_digest_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"container_scanner_resolved_digest": os.environ[',
        '"container_scanner_reference_only": os.environ[',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        'main-releasability.yml missing `"container_scanner_resolved_digest": os.environ[`'
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_image_digest_manifest_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"container_image_digest": os.environ["RELEASE_IMAGE_DIGEST"]',
        '"container_image_reference_only": os.environ["RELEASE_IMAGE_DIGEST"]',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        'main-releasability.yml missing `"container_image_digest": os.environ["RELEASE_IMAGE_DIGEST"]`'
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_image_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"image_signature": {',
        '"image_unsigned": {',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert 'main-releasability.yml missing `"image_signature": {`' in (
        module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_image_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"provenance_attestation": {',
        '"provenance_reference_only": {',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert 'main-releasability.yml missing `"provenance_attestation": {`' in (
        module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_sbom_scope_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"scope": "runtime_python_dependencies"',
        '"scope": "ambiguous_environment"',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        'main-releasability.yml missing `"scope": "runtime_python_dependencies"`'
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_sbom_target_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        '"target_artifact": os.environ["RELEASE_IMAGE_DIGEST_REF"]',
        '"target_artifact": "unknown"',
    )

    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        'main-releasability.yml missing `"target_artifact": os.environ["RELEASE_IMAGE_DIGEST_REF"]`'
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_self_referential_image_digest_label() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        '      io.lotus.image.build.id="${IMAGE_BUILD_ID}" \\\n',
        '      io.lotus.image.digest="${IMAGE_BUILD_ID}" \\\n',
    )

    errors = validate_dockerfile_runtime(degraded)

    assert "Dockerfile must label the non-self-referential image build identity" in errors
    assert "Dockerfile must not claim a pre-publication value is the registry digest" in errors


def test_ci_contract_gate_blocks_removed_release_identity_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        "make release-image-identity-contract-gate",
        "make removed-identity-contract-gate",
    )
    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        "main-releasability.yml missing `make release-image-identity-contract-gate`"
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_removed_release_license_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_contract_gate()
    workflow_dir = tmp_path / ".github" / "workflows"
    _copy_workflows(
        workflow_dir,
        "main-releasability.yml",
        "make license-release-evidence-gate",
        "make removed-license-evidence-gate",
    )
    monkeypatch.setattr(module, "WORKFLOWS_DIR", workflow_dir)

    assert (
        "main-releasability.yml missing `make license-release-evidence-gate`"
        in module.validate_ci_contract()
    )


def test_ci_contract_gate_blocks_missing_runtime_license_notices() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(" LICENSE THIRD_PARTY_NOTICES.md", "")

    assert "Dockerfile must include service license and third-party notices" in (
        validate_dockerfile_runtime(degraded)
    )


def test_ci_contract_gate_blocks_unfinalized_cyclonedx_release_sbom() -> None:
    makefile = (
        (ROOT / "Makefile")
        .read_text(encoding="utf-8")
        .replace(
            "\n\t$(VENV_PYTHON) scripts/finalize_release_sbom.py sbom.cdx.json",
            "",
        )
    )

    assert (
        "Makefile release-sbom target must finalize CycloneDX JSON for GitHub SBOM attestation"
        in validate_release_evidence_targets(makefile)
    )


def test_ci_contract_gate_blocks_dev_extras_in_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        "python -m pip install --no-cache-dir --no-deps .",
        'python -m pip install --no-cache-dir -e ".[dev]"',
    )

    errors = validate_dockerfile_runtime(degraded)

    assert "Dockerfile runtime image must not install development extras" in errors


def test_ci_contract_gate_blocks_secret_like_docker_build_args() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        "ARG SERVICE_VERSION=0.1.0",
        "ARG SERVICE_VERSION=0.1.0\nARG API_TOKEN=unsafe",
    )

    errors = validate_dockerfile_runtime(degraded)

    assert any("secret-like build metadata variable `API_TOKEN`" in error for error in errors)


def test_ci_contract_gate_blocks_makefile_image_push_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    degraded = makefile.replace(
        "docker-build:\n",
        "docker-push:\n\tdocker push $(CONTAINER_IMAGE_NAME)\n\ndocker-build:\n",
    )

    assert "Makefile must not push images; registry publication is CI-only" in (
        validate_release_evidence_targets(degraded)
    )


def test_ci_contract_gate_blocks_removed_service_version_image_label() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        '      org.opencontainers.image.version="${SERVICE_VERSION}" \\\n',
        "",
    )

    assert "Dockerfile must label the service version" in validate_dockerfile_runtime(degraded)


def test_ci_contract_gate_blocks_root_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace("USER lotus", "USER root")

    errors = validate_dockerfile_runtime(degraded)

    assert "Dockerfile runtime image must not run as root" in errors


def test_ci_contract_gate_accepts_hardened_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert validate_dockerfile_runtime(dockerfile) == []


def test_ci_contract_gate_blocks_unconstrained_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        "python -m pip install --no-cache-dir --requirement requirements/runtime-resolved.lock.txt",
        "python -m pip install --no-cache-dir fastapi uvicorn",
    )

    errors = validate_dockerfile_runtime(degraded)

    assert (
        "Dockerfile must install the resolved runtime dependency lockfile before source copy"
        in errors
    )


def test_ci_contract_gate_blocks_source_copy_before_runtime_dependency_install() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    cache_aware_install = (
        "RUN python -m pip install --no-cache-dir --upgrade pip \\\n"
        "    && python -m pip install --no-cache-dir --requirement "
        "requirements/runtime-resolved.lock.txt\n\n"
        "COPY src ./src\n"
        "RUN python -m pip install --no-cache-dir --no-deps ."
    )
    source_before_dependencies = (
        "COPY src ./src\n"
        "RUN python -m pip install --no-cache-dir --upgrade pip \\\n"
        "    && python -m pip install --no-cache-dir --requirement "
        "requirements/runtime-resolved.lock.txt\n"
        "RUN python -m pip install --no-cache-dir --no-deps ."
    )
    degraded = dockerfile.replace(cache_aware_install, source_before_dependencies)
    assert degraded != dockerfile

    errors = validate_dockerfile_runtime(degraded)

    assert (
        "Dockerfile must install resolved runtime dependencies before copying source and "
        "installing the local package"
    ) in errors


def test_ci_contract_gate_blocks_dependency_reinstall_during_local_package_install() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        "python -m pip install --no-cache-dir --no-deps .",
        "python -m pip install --no-cache-dir .",
    )

    errors = validate_dockerfile_runtime(degraded)

    assert (
        "Dockerfile must install the local service package without reinstalling dependencies"
        in errors
    )
