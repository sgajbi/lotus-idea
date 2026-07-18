from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "architecture_boundary_gate.py"
    spec = importlib.util.spec_from_file_location("architecture_boundary_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_architecture_boundary_gate_passes_current_committed_report() -> None:
    module = _load_gate()

    assert module.validate_architecture_boundaries() == []
    assert module.validate_architecture_report_freshness() == []


def test_architecture_boundary_report_freshness_accepts_regenerated_report(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    report_path = tmp_path / "architecture_boundary_report.json"
    _write_report(report_path, module.build_architecture_report("report-only"))

    assert module.validate_architecture_report_freshness(report_path) == []


def test_architecture_boundary_report_freshness_rejects_missing_schema(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    report_path = tmp_path / "architecture_boundary_report.json"
    report = module.build_architecture_report("report-only")
    report.pop("schema_version")
    _write_report(report_path, report)

    errors = module.validate_architecture_report_freshness(report_path)

    assert any("missing or unsupported schema_version" in error for error in errors)


def test_architecture_boundary_report_freshness_rejects_stale_fingerprint(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    report_path = tmp_path / "architecture_boundary_report.json"
    report = module.build_architecture_report("report-only")
    fingerprint = dict(report["input_fingerprint"])
    fingerprint["source_import_digest"] = "stale"
    report["input_fingerprint"] = fingerprint
    _write_report(report_path, report)

    errors = module.validate_architecture_report_freshness(report_path)

    assert any("stale source/rule fingerprint" in error for error in errors)


def test_architecture_boundary_report_freshness_rejects_tampered_status(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    report_path = tmp_path / "architecture_boundary_report.json"
    report = module.build_architecture_report("report-only")
    report["status"] = "unknown"
    _write_report(report_path, report)

    errors = module.validate_architecture_report_freshness(report_path)

    assert any("stale `status` field" in error for error in errors)
