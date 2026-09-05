from datetime import UTC, datetime, timedelta

from app.infrastructure.system_utc_clock import SystemUtcClock
from app.ports.trusted_clock import TrustedClock


def _read(clock: TrustedClock) -> datetime:
    return clock.now_utc()


def test_system_clock_returns_current_timezone_aware_utc() -> None:
    before = datetime.now(UTC) - timedelta(seconds=1)

    observed = _read(SystemUtcClock())

    after = datetime.now(UTC) + timedelta(seconds=1)
    assert observed.tzinfo is UTC
    assert before <= observed <= after
