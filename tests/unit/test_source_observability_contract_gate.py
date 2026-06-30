from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "source_observability_contract_gate.py"
    spec = importlib.util.spec_from_file_location("source_observability_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_python(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_source_observability_contract_gate_passes_current_repository() -> None:
    module = _load_gate()

    assert module.validate_source_observability_contract(ROOT) == []


def test_source_observability_contract_gate_blocks_print_in_application_source(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "api" / "unsafe.py",
        "def handler() -> None:\n    print('raw payload')\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    assert errors == [
        "src/app/api/unsafe.py:2: print() is prohibited in application source; "
        "use bounded structured logging"
    ]


def test_source_observability_contract_gate_blocks_direct_logging_imports(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "application" / "unsafe_logging.py",
        "import logging\n\n\ndef run() -> None:\n    logging.getLogger('lotus-idea').info('raw')\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    assert errors == [
        "src/app/application/unsafe_logging.py:1: direct logging imports are only allowed in "
        "src/app/observability/logging.py",
        "src/app/application/unsafe_logging.py:5: direct logging calls are only allowed in "
        "src/app/observability/logging.py",
    ]


def test_source_observability_contract_gate_allows_central_logging_module(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "observability" / "logging.py",
        "import logging\n\n\ndef configure() -> None:\n    logging.basicConfig(level=logging.INFO)\n",
    )

    assert module.validate_source_observability_contract(tmp_path) == []


def test_source_observability_contract_gate_blocks_low_level_log_event_bypass(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "api" / "unsafe_event.py",
        "from app.observability import log_event\n\n\ndef handler() -> None:\n"
        "    log_event('idea.raw', 'lotus-idea', portfolio_id='PB_SG_GLOBAL_BAL_001')\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    assert errors == [
        "src/app/api/unsafe_event.py:1: import bounded operation-event helpers instead of "
        "low-level log_event",
        "src/app/api/unsafe_event.py:5: call emit_operation_event or "
        "emit_foundation_operation_event instead of log_event",
    ]


def test_source_observability_contract_gate_blocks_manage_payload_hash_fallback(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "infrastructure" / "lotus_manage_sources.py",
        "import hashlib\n"
        "import json\n\n\n"
        "def _content_hash(payload: dict[str, object]) -> str:\n"
        "    canonical = json.dumps(payload, sort_keys=True)\n"
        "    return 'sha256:' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    assert errors == [
        "src/app/infrastructure/lotus_manage_sources.py:1: hashlib import is prohibited "
        "because upstream source-ref hashes must be source-authored",
        "src/app/infrastructure/lotus_manage_sources.py:2: json import is prohibited because "
        "upstream source-ref hashes must be source-authored",
        "src/app/infrastructure/lotus_manage_sources.py:6: json.dumps fallback is prohibited "
        "because upstream source-ref hashes must be source-authored",
        "src/app/infrastructure/lotus_manage_sources.py:7: hashlib.sha256 fallback is "
        "prohibited because upstream source-ref hashes must be source-authored",
    ]


def test_source_observability_contract_gate_blocks_core_maturity_position_scan(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "infrastructure" / "lotus_core_sources.py",
        "def _source_reported_maturity_dates(payload: dict[str, object]) -> tuple[object, ...]:\n"
        '    positions = payload.get("positions")\n'
        "    for position in positions:\n"
        "        pass\n"
        "    return ()\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    reason = (
        "Core bond-maturity evidence must consume explicit Core-owned maturity summary facts, "
        "not local raw-position maturity scans"
    )
    assert errors == [
        f"src/app/infrastructure/lotus_core_sources.py:1: {reason}",
        f"src/app/infrastructure/lotus_core_sources.py:2: {reason}",
        f"src/app/infrastructure/lotus_core_sources.py:3: {reason}",
    ]


def test_source_observability_contract_gate_blocks_freshness_supportability_inference(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "infrastructure" / "lotus_risk_sources.py",
        "from app.domain import EvidenceFreshness\n\n\n"
        "def _freshness(supportability_state: str) -> EvidenceFreshness:\n"
        "    if supportability_state.lower() == 'ready':\n"
        "        return EvidenceFreshness.CURRENT\n"
        "    return EvidenceFreshness.UNAVAILABLE\n",
    )

    errors = module.validate_source_observability_contract(tmp_path)

    assert errors == [
        "src/app/infrastructure/lotus_risk_sources.py:5: source adapters must not infer "
        "current freshness from readiness, supportability, coverage, health-state, or "
        "data-quality posture"
    ]


def test_source_observability_contract_gate_allows_explicit_freshness_current_mapping(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_python(
        tmp_path / "src" / "app" / "infrastructure" / "lotus_risk_sources.py",
        "from app.domain import EvidenceFreshness\n\n\n"
        "def _freshness(freshness_value: str) -> EvidenceFreshness:\n"
        "    if 'current' in freshness_value.lower():\n"
        "        return EvidenceFreshness.CURRENT\n"
        "    return EvidenceFreshness.UNAVAILABLE\n",
    )

    assert module.validate_source_observability_contract(tmp_path) == []
