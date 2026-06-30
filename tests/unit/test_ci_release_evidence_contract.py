from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from scripts.ci_release_evidence_contract import validate_dockerfile_runtime


ROOT = Path(__file__).resolve().parents[2]


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


def test_ci_contract_gate_blocks_dev_extras_in_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace(
        "python -m pip install --no-cache-dir .",
        'python -m pip install --no-cache-dir -e ".[dev]"',
    )

    errors = validate_dockerfile_runtime(degraded)

    assert "Dockerfile runtime image must not install development extras" in errors


def test_ci_contract_gate_blocks_root_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    degraded = dockerfile.replace("USER lotus", "USER root")

    errors = validate_dockerfile_runtime(degraded)

    assert "Dockerfile runtime image must not run as root" in errors


def test_ci_contract_gate_accepts_hardened_runtime_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert validate_dockerfile_runtime(dockerfile) == []
