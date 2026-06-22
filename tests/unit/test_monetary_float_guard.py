from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_guard() -> ModuleType:
    script_path = ROOT / "scripts" / "check_monetary_float_usage.py"
    spec = importlib.util.spec_from_file_location("check_monetary_float_usage", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_python(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_monetary_float_guard_passes_current_repository_baseline() -> None:
    module = _load_guard()

    assert module.validate_monetary_float_usage(ROOT) == []


def test_monetary_float_guard_blocks_money_like_float_annotations(tmp_path: Path) -> None:
    module = _load_guard()
    _write_python(
        tmp_path / "src" / "app" / "domain" / "money.py",
        "market_value: float = 1\n",
    )

    errors = module.validate_monetary_float_usage(tmp_path)

    assert errors == [
        "src/app/domain/money.py:1: monetary float annotation detected",
    ]


def test_monetary_float_guard_blocks_money_like_float_literals(tmp_path: Path) -> None:
    module = _load_guard()
    _write_python(
        tmp_path / "src" / "app" / "domain" / "money.py",
        "cash_balance = 100.25\n",
    )

    errors = module.validate_monetary_float_usage(tmp_path)

    assert errors == [
        "src/app/domain/money.py:1: monetary float literal detected",
    ]


def test_monetary_float_guard_blocks_money_like_float_conversions(tmp_path: Path) -> None:
    module = _load_guard()
    _write_python(
        tmp_path / "src" / "app" / "domain" / "money.py",
        "def parse_price(raw: str) -> object:\n    return float(raw)\n",
    )

    errors = module.validate_monetary_float_usage(tmp_path)

    assert errors == [
        "src/app/domain/money.py:2: monetary float conversion detected",
    ]


def test_monetary_float_guard_blocks_money_like_float_return_annotations(tmp_path: Path) -> None:
    module = _load_guard()
    _write_python(
        tmp_path / "src" / "app" / "domain" / "money.py",
        "def market_value() -> float:\n    return 1\n",
    )

    errors = module.validate_monetary_float_usage(tmp_path)

    assert errors == [
        "src/app/domain/money.py:1: monetary float return annotation detected",
    ]


def test_monetary_float_guard_allows_operational_float_usage(tmp_path: Path) -> None:
    module = _load_guard()
    _write_python(
        tmp_path / "src" / "app" / "infrastructure" / "timeouts.py",
        "timeout_seconds: float = 2.0\n"
        "def parse_timeout(raw: str) -> float:\n"
        "    return float(raw)\n",
    )

    assert module.validate_monetary_float_usage(tmp_path) == []
