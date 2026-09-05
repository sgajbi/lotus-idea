from app.infrastructure.system_utc_clock import SystemUtcClock
from app.ports.trusted_clock import TrustedClock


_TRUSTED_CLOCK: TrustedClock = SystemUtcClock()


def get_trusted_clock() -> TrustedClock:
    return _TRUSTED_CLOCK


__all__ = ["get_trusted_clock"]
