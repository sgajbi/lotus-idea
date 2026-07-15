from datetime import UTC, datetime

import pytest

from app.domain.proof_evidence import (
    is_timezone_aware_datetime_text,
    parse_timezone_aware_datetime,
)


def test_parse_timezone_aware_datetime_normalises_offset_to_utc() -> None:
    assert parse_timezone_aware_datetime("2026-07-15T08:30:00+08:00") == datetime(
        2026,
        7,
        15,
        0,
        30,
        tzinfo=UTC,
    )


@pytest.mark.parametrize(
    "value",
    [None, 1, "", "not-a-date", "2026-07-15T00:30:00"],
)
def test_parse_timezone_aware_datetime_rejects_non_aware_values(value: object) -> None:
    assert parse_timezone_aware_datetime(value) is None
    assert is_timezone_aware_datetime_text(value) is False


def test_timezone_aware_datetime_text_accepts_utc_suffix() -> None:
    assert is_timezone_aware_datetime_text("2026-07-15T00:30:00Z") is True
