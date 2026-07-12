from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_lineage_persistence import AIExplanationLineagePersistenceResult
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import VerifiedAIProviderRetentionReceipt
from app.domain.persistence import InMemoryIdeaRepository

_ResultT = TypeVar("_ResultT")


class PostgresAIExplanationWriteMixin:
    def _mutate(self, operation: Callable[[InMemoryIdeaRepository], _ResultT]) -> _ResultT:
        raise NotImplementedError

    def record_ai_explanation_lineage(
        self,
        result: AIExplanationResult,
        *,
        attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
        provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
    ) -> AIExplanationLineagePersistenceResult:
        return self._mutate(
            lambda repository: repository.record_ai_explanation_lineage(
                result,
                attestation_receipt=attestation_receipt,
                provider_retention_receipt=provider_retention_receipt,
            )
        )

    def record_ai_explanation_lineage_request(
        self,
        result: AIExplanationResult,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
        attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
        provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
    ) -> AIExplanationLineagePersistenceResult:
        return self._mutate(
            lambda repository: repository.record_ai_explanation_lineage_request(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                attestation_receipt=attestation_receipt,
                provider_retention_receipt=provider_retention_receipt,
            )
        )
