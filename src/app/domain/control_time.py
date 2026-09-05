from enum import StrEnum


class AcceptanceTimeSource(StrEnum):
    """Provenance for the service-controlled acceptance timestamp."""

    SERVER_ACCEPTED = "server_accepted"
    LEGACY_OBSERVED_TIME_ASSUMED = "legacy_observed_time_assumed"
