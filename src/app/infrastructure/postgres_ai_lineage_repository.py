from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_lineage_persistence import AIExplanationLineagePersistenceResult
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import VerifiedAIProviderRetentionReceipt
from app.domain.persistence import InMemoryIdeaRepository
from app.infrastructure.persistence import RelatedCandidateIdsLoader
from app.infrastructure.postgres_ai_lineage_identity import (
    load_ai_lineage_identity_candidate_ids,
)
from app.infrastructure.postgres_protocols import PostgresConnection

_ResultT = TypeVar("_ResultT")


class PostgresAIExplanationWriteMixin:
    _connection: PostgresConnection

    def _mutate_candidate(
        self,
        *,
        candidate_ids: tuple[str, ...],
        operation: Callable[[InMemoryIdeaRepository], _ResultT],
        idempotency_key: str | None = None,
        identity_keys: tuple[str, ...] = (),
        related_candidate_ids_loader: RelatedCandidateIdsLoader | None = None,
    ) -> _ResultT:
        raise NotImplementedError

    def record_ai_explanation_lineage(
        self,
        result: AIExplanationResult,
        *,
        attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
        provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
    ) -> AIExplanationLineagePersistenceResult:
        candidate_id = result.request.redacted_evidence.candidate_id
        request_id = result.request.request_id
        return self._mutate_candidate(
            candidate_ids=(candidate_id,),
            identity_keys=_ai_lineage_identity_keys(
                request_id=request_id,
                attestation_receipt=attestation_receipt,
                provider_retention_receipt=provider_retention_receipt,
            ),
            related_candidate_ids_loader=lambda: load_ai_lineage_identity_candidate_ids(
                self._connection,
                request_id=request_id,
                attestation_replay_nonce=(
                    attestation_receipt.replay_nonce
                    if attestation_receipt is not None
                    else None
                ),
                provider_replay_nonce=(
                    provider_retention_receipt.replay_nonce
                    if provider_retention_receipt is not None
                    else None
                ),
            ),
            operation=lambda repository: repository.record_ai_explanation_lineage(
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
        candidate_id = result.request.redacted_evidence.candidate_id
        request_id = result.request.request_id
        return self._mutate_candidate(
            candidate_ids=(candidate_id,),
            idempotency_key=idempotency_key,
            identity_keys=_ai_lineage_identity_keys(
                request_id=request_id,
                attestation_receipt=attestation_receipt,
                provider_retention_receipt=provider_retention_receipt,
            ),
            related_candidate_ids_loader=lambda: load_ai_lineage_identity_candidate_ids(
                self._connection,
                request_id=request_id,
                attestation_replay_nonce=(
                    attestation_receipt.replay_nonce
                    if attestation_receipt is not None
                    else None
                ),
                provider_replay_nonce=(
                    provider_retention_receipt.replay_nonce
                    if provider_retention_receipt is not None
                    else None
                ),
            ),
            operation=lambda repository: repository.record_ai_explanation_lineage_request(
                result,
                idempotency_key=idempotency_key,
                payload=payload,
                attestation_receipt=attestation_receipt,
                provider_retention_receipt=provider_retention_receipt,
            )
        )


def _ai_lineage_identity_keys(
    *,
    request_id: str,
    attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None,
    provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None,
) -> tuple[str, ...]:
    keys = {f"ai-request:{request_id}"}
    if attestation_receipt is not None:
        keys.add(f"lotus-ai-replay:{attestation_receipt.replay_nonce}")
    if provider_retention_receipt is not None:
        keys.add(f"provider-replay:{provider_retention_receipt.replay_nonce}")
    return tuple(sorted(keys))
