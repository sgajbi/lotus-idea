from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import pytest

from app.api.temporal_validation import (
    is_timezone_aware,
    is_utc_datetime,
    require_timezone_aware,
    require_utc_datetime,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_api_temporal_validation_boundary_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "api_temporal_validation_boundary_gate.py"
    spec = importlib.util.spec_from_file_location(
        "api_temporal_validation_boundary_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_timezone_aware_validator_accepts_aware_datetimes() -> None:
    value = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    assert is_timezone_aware(value)
    assert require_timezone_aware(value, field_name="evaluatedAtUtc") is value


def test_timezone_aware_validator_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="evaluatedAtUtc must be timezone-aware"):
        require_timezone_aware(
            datetime(2026, 6, 21, 10, 0),
            field_name="evaluatedAtUtc",
        )


def test_utc_validator_rejects_non_utc_datetimes() -> None:
    singapore = timezone(timedelta(hours=8))
    value = datetime(2026, 6, 21, 18, 0, tzinfo=singapore)

    assert is_timezone_aware(value)
    assert not is_utc_datetime(value)
    with pytest.raises(ValueError, match="deliveredAtUtc must be UTC"):
        require_utc_datetime(value, field_name="deliveredAtUtc")


def test_utc_validator_accepts_utc_datetimes() -> None:
    value = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    assert is_utc_datetime(value)
    assert require_utc_datetime(value, field_name="deliveredAtUtc") is value


def test_api_temporal_validation_boundary_gate_passes_current_repository() -> None:
    module = _load_api_temporal_validation_boundary_gate()

    assert module.validate_api_temporal_validation_boundary() == []


def test_api_temporal_validation_boundary_gate_blocks_route_local_timezone_checks(
    tmp_path: Path,
) -> None:
    module = _load_api_temporal_validation_boundary_gate()
    api_dir = tmp_path / "src" / "app" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "temporal_validation.py").write_text(
        "from datetime import datetime\n",
        encoding="utf-8",
    )
    (api_dir / "unsafe_route.py").write_text(
        "def validate(value):\n"
        "    if value.tzinfo is None or value.utcoffset() is None:\n"
        "        raise ValueError('bad')\n",
        encoding="utf-8",
    )

    errors = module.validate_api_temporal_validation_boundary(tmp_path)

    assert errors == [
        "src/app/api/unsafe_route.py:2: API routes must use "
        "`app.api.temporal_validation` instead of checking `tzinfo` directly",
        "src/app/api/unsafe_route.py:2: API routes must use "
        "`app.api.temporal_validation` instead of calling `utcoffset()` directly",
    ]
