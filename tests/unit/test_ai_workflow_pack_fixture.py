from __future__ import annotations

from pathlib import Path

from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_fixture,
    write_lotus_ai_workflow_pack_runtime_execution_fixture,
)


def test_ai_workflow_pack_fixture_writes_source_contract_files(tmp_path: Path) -> None:
    lotus_ai_root = write_lotus_ai_workflow_pack_fixture(tmp_path)

    phase1_spec = _read(lotus_ai_root, "src/app/services/workflow_pack_phase1_specs.py")
    registry_seed = _read(lotus_ai_root, "src/app/services/workflow_pack_registry_seed.py")
    bindings = _read(lotus_ai_root, "src/app/services/workflow_pack_bindings.py")
    supportability = _read(lotus_ai_root, "src/app/services/ai_surface_supportability.py")

    assert 'pack_id="idea_explanation.pack"' in phase1_spec
    assert 'workflow_authority_owner="lotus-idea"' in phase1_spec
    assert '"repo://lotus-idea/src/app/domain/ai_governance.py"' in registry_seed
    assert '"client-ready publication"' in registry_seed
    assert '"supported-feature promotion"' in registry_seed
    assert "IDEA_EXPLANATION_BINDING" in bindings
    assert '"idea_explanation.pack@v1": {"authority": "lotus-idea"}' in supportability


def test_ai_workflow_pack_runtime_fixture_preserves_non_claim_boundaries(
    tmp_path: Path,
) -> None:
    lotus_ai_root = write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path)

    provider_stub = _read(lotus_ai_root, "src/app/providers/idea_explanation_stub.py")
    guardrails = _read(lotus_ai_root, "src/app/services/idea_explanation_guardrails.py")
    caller_policy = _read(
        lotus_ai_root,
        "src/app/repositories/memory_caller_policy_repository.py",
    )
    execution_test = _read(lotus_ai_root, "tests/unit/test_workflow_pack_execution.py")

    assert '"client_ready_publication": "BLOCKED"' in provider_stub
    assert '"downstream_authority": "BLOCKED"' in provider_stub
    assert '_FORBIDDEN_REQUESTED_OUTPUTS = {"client_ready_publication"}' in guardrails
    assert 'assert supportability["client_ready_publication"] == "BLOCKED"' in guardrails
    assert "allow_live_provider=False" in caller_policy
    assert "allow_provider_control=False" in caller_policy
    assert '"client_ready_publication": "BLOCKED"' in execution_test


def test_runtime_fixture_extends_base_fixture_without_replacing_source_contract(
    tmp_path: Path,
) -> None:
    lotus_ai_root = write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path)

    assert (lotus_ai_root / "src/app/services/workflow_pack_phase1_specs.py").is_file()
    assert (lotus_ai_root / "src/app/providers/idea_explanation_stub.py").is_file()
    assert (lotus_ai_root / "tests/unit/test_workflow_pack_registry.py").is_file()
    assert (lotus_ai_root / "tests/unit/test_sqlalchemy_caller_policy_repository.py").is_file()


def _read(lotus_ai_root: Path, relative_path: str) -> str:
    return (lotus_ai_root / relative_path).read_text(encoding="utf-8")
