from typing import Protocol

from app.domain.lotus_ai_run_attestation import LotusAIAttestationKeyDiscovery


class LotusAIAttestationKeySource(Protocol):
    def get_key_discovery(self) -> LotusAIAttestationKeyDiscovery: ...
