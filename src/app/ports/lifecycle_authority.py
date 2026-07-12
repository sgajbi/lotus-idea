from typing import Protocol

from app.domain.data_lifecycle.authority import LifecycleAuthorityKeyDiscovery


class LifecycleAuthorityKeySource(Protocol):
    def get_key_discovery(self) -> LifecycleAuthorityKeyDiscovery: ...
