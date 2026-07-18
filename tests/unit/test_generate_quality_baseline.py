from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_generate_quality_baseline() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_quality_baseline.py"
    spec = importlib.util.spec_from_file_location("generate_quality_baseline", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_python(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_quality_baseline_excludes_non_implementation_protocol_stubs(
    tmp_path: Path,
) -> None:
    module = _load_generate_quality_baseline()
    _write_python(
        tmp_path / "src" / "app" / "ports.py",
        [
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
            "",
            "    def close(self) -> None:",
            "        pass",
            "",
            "",
            "def implemented() -> int:",
            "    return 1",
        ],
    )

    report = module.build_report(tmp_path)

    assert report["python_functions"] == 1
    assert report["largest_functions"] == [
        {
            "line": 155,
            "lines": 2,
            "name": "implemented",
            "path": "src/app/ports.py",
        }
    ]


def test_quality_baseline_writer_uses_filtered_function_rows(tmp_path: Path) -> None:
    module = _load_generate_quality_baseline()
    _write_python(
        tmp_path / "scripts" / "contract.py",
        [
            "class SourceContract:",
            "    def declare(",
            "        self,",
            *[f"        field_{index}: str," for index in range(120)],
            "    ) -> None:",
            "        pass",
            "",
            "",
            "def validate_contract() -> list[str]:",
            "    return []",
        ],
    )

    report = module.write_report(tmp_path)
    markdown = (tmp_path / "quality" / "baseline_report.md").read_text(encoding="utf-8")

    assert report["python_functions"] == 1
    assert "`scripts/contract.py::validate_contract`: 2 lines" in markdown
    assert "declare" not in markdown
