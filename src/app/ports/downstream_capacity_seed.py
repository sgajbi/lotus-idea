from __future__ import annotations

from datetime import date, datetime
from typing import Protocol


class DownstreamCapacitySeedPort(Protocol):
    def persist_candidate(
        self, *, seed_key: str, as_of_date: date, seeded_at_utc: datetime
    ) -> str: ...

    def transition_candidate(
        self,
        *,
        candidate_id: str,
        seed_key: str,
        target_status: str,
        changed_at_utc: datetime,
    ) -> None: ...

    def approve_candidate(
        self, *, candidate_id: str, seed_key: str, decided_at_utc: datetime
    ) -> None: ...

    def record_conversion_intent(
        self,
        *,
        candidate_id: str,
        conversion_intent_id: str,
        seed_key: str,
        requested_at_utc: datetime,
    ) -> None: ...

    def close(self) -> None: ...
