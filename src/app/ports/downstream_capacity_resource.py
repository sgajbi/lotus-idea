from __future__ import annotations

from typing import Any, Mapping, Protocol


class DownstreamCapacityResourcePort(Protocol):
    def fetch_candidate_detail(
        self,
        *,
        candidate_id: str,
        tenant_id: str,
        book_id: str,
        portfolio_id: str,
        client_id: str,
    ) -> Mapping[str, Any]: ...

    def close(self) -> None: ...
