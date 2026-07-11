from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "trusted_tenant_context_gate.py"
    spec = importlib.util.spec_from_file_location("trusted_tenant_context_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _copy_gate_inputs(module: ModuleType, target: Path) -> None:
    for relative_path in module.REQUIRED_FILES:
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative_path, destination)


def test_trusted_tenant_context_gate_passes_current_contract() -> None:
    module = _load_gate()

    assert module.validate_trusted_tenant_context(ROOT) == []


def test_trusted_tenant_context_gate_rejects_discarded_candidate_scope(tmp_path: Path) -> None:
    module = _load_gate()
    _copy_gate_inputs(module, tmp_path)
    path = tmp_path / "src/app/application/high_cash_signal.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "tenant_portfolio_scope(",
            "portfolio_only_scope(",
        ),
        encoding="utf-8",
    )

    errors = module.validate_trusted_tenant_context(tmp_path)

    assert any("must not discard tenant context" in error for error in errors)


def test_trusted_tenant_context_gate_rejects_default_adapter_tenant(tmp_path: Path) -> None:
    module = _load_gate()
    _copy_gate_inputs(module, tmp_path)
    path = tmp_path / "src/app/infrastructure/lotus_core_sources.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"tenant_id": request.tenant_id',
            '"tenant_id": "default"',
            1,
        ),
        encoding="utf-8",
    )

    errors = module.validate_trusted_tenant_context(tmp_path)

    assert any("hard-coded production tenant fallback" in error for error in errors)


def test_required_fragment_diagnostic_does_not_echo_scanned_content() -> None:
    module = _load_gate()
    errors: list[str] = []
    sensitive_fragment = "secret-token-value"

    module._require_fragments(
        errors,
        Path("contract.py"),
        "unrelated content",
        (sensitive_fragment,),
    )

    assert errors == ["contract.py: required tenant contract fragment 1 is missing"]
    assert sensitive_fragment not in errors[0]


def test_cli_failure_does_not_emit_validation_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_gate()
    sensitive_detail = "secret-token-value"
    monkeypatch.setattr(
        module, "validate_trusted_tenant_context", lambda: [sensitive_detail]
    )

    assert module.main() == 1
    output = capsys.readouterr().out
    assert output == "Trusted tenant context gate failed with 1 violation(s)\n"
    assert sensitive_detail not in output
