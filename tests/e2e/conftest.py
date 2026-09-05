from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from app.runtime import trusted_clock_state
from tests.support.fixed_utc_clock import FixedUtcClock
from tests.support.http import managed_test_client_scope


@pytest.fixture(autouse=True)
def _deterministic_control_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trusted_clock_state,
        "_TRUSTED_CLOCK",
        FixedUtcClock(datetime(2026, 6, 21, 10, 10, tzinfo=UTC)),
    )


@pytest.fixture(autouse=True)
def _close_e2e_test_clients() -> Iterator[None]:
    with managed_test_client_scope():
        yield
