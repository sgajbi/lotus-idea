from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from scripts.disaster_recovery_evidence_io import write_dataclass_evidence_atomic


@dataclass(frozen=True)
class Evidence:
    generated_at_utc: datetime
    value: object = "source-safe"


def test_atomic_evidence_writer_serializes_utc_datetime(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"

    write_dataclass_evidence_atomic(
        path,
        Evidence(datetime(2026, 7, 12, 3, 0, tzinfo=UTC)),
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "generated_at_utc": "2026-07-12T03:00:00+00:00",
        "value": "source-safe",
    }
    assert not path.with_suffix(".json.tmp").exists()


def test_atomic_evidence_writer_rejects_naive_datetime(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        write_dataclass_evidence_atomic(
            tmp_path / "evidence.json",
            Evidence(datetime(2026, 7, 12, 3, 0)),
        )


def test_atomic_evidence_writer_rejects_unsupported_value(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="unsupported evidence value: object"):
        write_dataclass_evidence_atomic(
            tmp_path / "evidence.json",
            Evidence(datetime(2026, 7, 12, 3, 0, tzinfo=UTC), object()),
        )
