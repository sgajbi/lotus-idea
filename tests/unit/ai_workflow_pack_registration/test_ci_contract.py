from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[3]


def test_readiness_generation_requires_registration_source_contract_input() -> None:
    makefile = _makefile().replace(
        "$(if $(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),"
        "--ai-workflow-pack-registration-proof "
        "$(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF),"
        "--ai-workflow-pack-registration-proof "
        "$(LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT)) ",
        "",
    )

    errors = _load_ci_contract_gate().validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the "
        "AI workflow-pack registration source-contract proof artifact into readiness generation"
    ) in errors


def test_readiness_generation_requires_registration_source_contract_generator() -> None:
    makefile = _makefile().replace(
        "scripts/ai_workflow_pack_registration/generate_source_contract_proof.py",
        "scripts/removed.py",
    )

    errors = _load_ci_contract_gate().validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must generate "
        "an AI workflow-pack registration source-contract proof artifact"
    ) in errors


def test_readiness_generation_requires_registration_output_wiring() -> None:
    makefile = _makefile().replace(
        "LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT",
        "REMOVED_AI_WORKFLOW_PACK_PROOF_OUTPUT",
    )

    errors = _load_ci_contract_gate().validate_makefile(makefile)

    assert (
        "Makefile implementation-proof-readiness-check target must pass the default "
        "AI workflow-pack registration proof output into readiness generation"
    ) in errors


def test_readiness_generation_requires_lotus_ai_source_root() -> None:
    errors = _load_ci_contract_gate().validate_makefile(_makefile().replace("LOTUS_AI_ROOT", ""))

    assert (
        "Makefile implementation-proof-readiness-check target must support default "
        "lotus-ai root wiring for AI workflow-pack registration proof generation"
    ) in errors


def test_lint_requires_registration_source_contract_gate() -> None:
    makefile = (
        _makefile()
        .replace("$(MAKE) ai-workflow-pack-registration-proof-contract-gate\n", "")
        .replace(
            "scripts/ai_workflow_pack_registration/source_contract_proof_gate.py",
            "scripts/removed.py",
        )
    )

    errors = _load_ci_contract_gate().validate_makefile(makefile)

    assert (
        "Makefile lint target must call `$(MAKE) ai-workflow-pack-registration-proof-contract-gate`"
    ) in errors
    assert (
        "Makefile ai-workflow-pack-registration-proof-contract-gate target must run "
        "`scripts/ai_workflow_pack_registration/source_contract_proof_gate.py`"
    ) in errors


def _makefile() -> str:
    return (ROOT / "Makefile").read_text(encoding="utf-8")


def _load_ci_contract_gate() -> ModuleType:
    path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
