from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "contracts" / "operations" / "lotus-idea-deployment-migrations.v1.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deployment-migration-evidence.yml"


def test_deployment_migration_contract_gate_passes_repository_truth() -> None:
    module = _load_gate()

    assert module.validate_deployment_migration_contract(ROOT) == []


def test_deployment_migration_contract_gate_rejects_bundle_drift(tmp_path: Path) -> None:
    module = _load_gate()
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["migrationBundleSha256"] = f"sha256:{'0' * 64}"
    altered_contract = tmp_path / "deployment-migrations.json"
    altered_contract.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_deployment_migration_contract(
        ROOT,
        contract_path=altered_contract,
    )

    assert "migrationBundleSha256 does not match the repository migration bundle" in errors


def test_deployment_migration_workflow_rejects_mutable_or_injected_execution() -> None:
    module = _load_gate()
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = workflow.replace(
        'docker pull "$IMAGE_DIGEST_REFERENCE"',
        "docker pull ghcr.io/sgajbi/lotus-idea:latest",
    ).replace(
        '[[ "$EXPECTED_COMMIT_SHA" =~ ^[0-9a-f]{40}$ ]]',
        '[[ "${{ inputs.expected_commit_sha }}" =~ ^[0-9a-f]{40}$ ]]',
    )

    errors = module.validate_deployment_migration_workflow(workflow)

    assert any("docker pull" in error for error in errors)
    assert any(":latest" in error for error in errors)
    assert any("job environment variables" in error for error in errors)


def test_deployment_migration_workflow_rejects_unavailable_self_hosted_runner() -> None:
    module = _load_gate()
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8").replace(
        "runs-on: ubuntu-latest",
        "runs-on: [self-hosted, linux, lotus-deployment]",
    )

    errors = module.validate_deployment_migration_workflow(workflow)

    assert any("runs-on: ubuntu-latest" in error for error in errors)
    assert any("self-hosted" in error for error in errors)
    assert any("lotus-deployment" in error for error in errors)


def test_contract_gate_rejects_direct_migration_in_other_workflows() -> None:
    module = _load_gate()

    errors = module.validate_production_migration_entrypoints(
        {
            "production-rollout.yml": "steps:\n  - run: make migrate\n",
            "scheduled-data-lifecycle-review.yml": "steps:\n  - run: make migrate\n",
        }
    )

    assert errors == [
        "production-rollout.yml must use the governed exact-image deployment migration "
        "workflow; direct migration execution is reserved for approved disposable fixtures"
    ]


def _load_gate() -> ModuleType:
    script = ROOT / "scripts" / "deployment_migration_contract_gate.py"
    spec = importlib.util.spec_from_file_location("deployment_migration_contract_gate", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
