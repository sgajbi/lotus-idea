from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_maintainability_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "maintainability_gate.py"
    spec = importlib.util.spec_from_file_location("maintainability_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_python(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_maintainability_gate_passes_current_repository_baseline() -> None:
    module = _load_maintainability_gate()

    assert module.validate_maintainability(ROOT) == []


def test_maintainability_gate_blocks_oversized_source_function(tmp_path: Path) -> None:
    module = _load_maintainability_gate()
    function_body = ["def oversized() -> int:", "    total = 0"]
    function_body.extend(f"    total += {index}" for index in range(130))
    function_body.append("    return total")
    _write_python(tmp_path / "src" / "app" / "domain" / "oversized.py", function_body)

    errors = module.validate_maintainability(tmp_path)

    assert len(errors) == 1
    assert "src/app/domain/oversized.py:1 `oversized` has 133 lines" in errors[0]
    assert "source functions must stay at or below 130 lines" in errors[0]


def test_maintainability_gate_ignores_non_implementation_protocol_stubs(
    tmp_path: Path,
) -> None:
    module = _load_maintainability_gate()
    protocol_body = [
        "from typing import Protocol",
        "",
        "",
        "class OversizedPort(Protocol):",
        "    def publish(",
        "        self,",
        "        event_id: str,",
        "        *,",
        *[f"        field_{index}: str," for index in range(140)],
        "    ) -> None: ...",
    ]
    _write_python(tmp_path / "src" / "app" / "ports.py", protocol_body)

    assert module.validate_maintainability(tmp_path) == []


def test_maintainability_gate_blocks_oversized_script_file(tmp_path: Path) -> None:
    module = _load_maintainability_gate()
    _write_python(
        tmp_path / "scripts" / "too_large.py",
        ["VALUE = 1", *(f"VALUE += {index}" for index in range(500))],
    )

    errors = module.validate_maintainability(tmp_path)

    assert len(errors) == 1
    assert "scripts/too_large.py has 501 lines" in errors[0]
    assert "scripts files must stay at or below 500 lines" in errors[0]
