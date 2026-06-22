from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "no_sensitive_content_guard.py"
    spec = importlib.util.spec_from_file_location("no_sensitive_content_guard", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_sensitive_content_guard_passes_clean_artifacts(tmp_path: Path) -> None:
    module = _load_gate()
    output = tmp_path / "output"
    output.mkdir()
    (output / "summary.md").write_text("bounded operation evidence only\n", encoding="utf-8")

    assert module.validate_no_sensitive_content(scan_roots=(output,)) == []


def test_no_sensitive_content_guard_blocks_sensitive_artifact_markers(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    artifact = evidence / "run-summary.json"
    artifact.write_text('{"portfolio_id": "PB_SG_GLOBAL_BAL_001"}\n', encoding="utf-8")

    errors = module.validate_no_sensitive_content(scan_roots=(evidence,))

    assert errors == [f"{artifact.as_posix()}: forbidden sensitive content marker portfolio_id"]


def test_no_sensitive_content_guard_honors_absolute_allowlist(tmp_path: Path) -> None:
    module = _load_gate()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    allowed = evidence / "README.md"
    allowed.write_text("This guide names request_body as a blocked marker.\n", encoding="utf-8")

    assert (
        module.validate_no_sensitive_content(
            scan_roots=(evidence,),
            allowlist={allowed},
        )
        == []
    )


def test_no_sensitive_content_guard_ignores_binary_artifacts(tmp_path: Path) -> None:
    module = _load_gate()
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "diagnostic.bin").write_bytes(b"\xff\xfe\x00\x00")

    assert module.validate_no_sensitive_content(scan_roots=(logs,)) == []
