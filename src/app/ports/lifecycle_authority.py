from typing import Protocol

from app.domain.lifecycle_authority import LifecycleAuthorityKeyDiscovery


class LifecycleAuthorityKeySource(Protocol):
    def get_key_discovery(self) -> LifecycleAuthorityKeyDiscovery: ...
