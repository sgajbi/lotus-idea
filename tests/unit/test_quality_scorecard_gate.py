from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "quality_scorecard_gate.py"
    spec = importlib.util.spec_from_file_location("quality_scorecard_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_quality_scorecard_gate_passes_current_repository_truth() -> None:
    module = _load_gate()

    assert module.validate_quality_scorecard() == []


def test_quality_scorecard_gate_blocks_stale_scaffold_underclaim(tmp_path: Path) -> None:
    module = _load_gate()
    scorecard = tmp_path / "quality_scorecard.md"
    scorecard.write_text(
        "# Bank-Buyable Quality Scorecard\n\n"
        "| Control Area | Current Status | Evidence | Gap | Next Slice |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| API and contracts | `Partially implemented` | OpenAPI and endpoint certification. | "
        "Business endpoints not yet implemented. | Add certification evidence. |\n",
        encoding="utf-8",
    )

    errors = module.validate_quality_scorecard(scorecard)

    assert (
        "quality/quality_scorecard.md: stale scaffold-era scorecard claim "
        "`business_endpoints_not_implemented`"
    ) in errors


def test_quality_scorecard_gate_blocks_report_only_architecture_evidence_as_current_proof(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    scorecard = tmp_path / "quality_scorecard.md"
    scorecard.write_text(
        "# Bank-Buyable Quality Scorecard\n\n"
        "| Control Area | Current Status | Evidence | Gap | Next Slice |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Architecture | `Partially implemented` | architecture-boundary-gate, "
        "maintainability-gate, and report-only architecture evidence. | "
        "Specific ownership gaps remain. | Tighten module ownership. |\n",
        encoding="utf-8",
    )

    errors = module.validate_quality_scorecard(scorecard)

    assert (
        "quality/quality_scorecard.md: stale scaffold-era scorecard claim "
        "`architecture_report_treated_as_current_proof`"
    ) in errors


def test_quality_scorecard_gate_requires_bank_buyable_control_rows(tmp_path: Path) -> None:
    module = _load_gate()
    scorecard = tmp_path / "quality_scorecard.md"
    scorecard.write_text(
        "# Bank-Buyable Quality Scorecard\n\n"
        "| Control Area | Current Status | Evidence | Gap | Next Slice |\n"
        "| --- | --- | --- | --- | --- |\n",
        encoding="utf-8",
    )

    errors = module.validate_quality_scorecard(scorecard)

    assert "quality/quality_scorecard.md: missing control row `Architecture`" in errors
    assert (
        "quality/quality_scorecard.md: missing control row `Documentation and operations`" in errors
    )


def test_quality_scorecard_gate_rejects_non_contract_status(tmp_path: Path) -> None:
    module = _load_gate()
    scorecard = tmp_path / "quality_scorecard.md"
    scorecard.write_text(
        "# Bank-Buyable Quality Scorecard\n\n"
        "| Control Area | Current Status | Evidence | Gap | Next Slice |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Architecture | `Mostly done` | architecture-boundary-gate and maintainability-gate. | "
        "Specific ownership gaps remain. | Tighten module ownership. |\n",
        encoding="utf-8",
    )

    errors = module.validate_quality_scorecard(scorecard)

    assert (
        "quality/quality_scorecard.md: `Architecture` has unsupported status `Mostly done`"
        in errors
    )


def test_quality_scorecard_gate_requires_evidence_anchors(tmp_path: Path) -> None:
    module = _load_gate()
    scorecard = tmp_path / "quality_scorecard.md"
    scorecard.write_text(
        "# Bank-Buyable Quality Scorecard\n\n"
        "| Control Area | Current Status | Evidence | Gap | Next Slice |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Architecture | `Partially implemented` | Layered packages exist. | "
        "Specific ownership gaps remain. | Tighten module ownership. |\n",
        encoding="utf-8",
    )

    errors = module.validate_quality_scorecard(scorecard)

    assert (
        "quality/quality_scorecard.md: `Architecture` evidence missing `architecture-boundary-gate`"
        in errors
    )
    assert (
        "quality/quality_scorecard.md: `Architecture` evidence missing `maintainability-gate`"
        in errors
    )
