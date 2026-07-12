from __future__ import annotations

from collections.abc import Iterable

from app.domain.ai_provider_retention import VerifiedAIProviderRetentionReceipt


class AIProviderRetentionReplayIndex:
    def __init__(self) -> None:
        self._request_by_confirmation_id: dict[str, str] = {}
        self._request_by_provider_ref: dict[str, str] = {}
        self._request_by_nonce: dict[str, str] = {}

    def conflicts(
        self,
        *,
        request_id: str,
        receipt: VerifiedAIProviderRetentionReceipt,
    ) -> bool:
        return any(
            existing_request_id not in {None, request_id}
            for existing_request_id in (
                self._request_by_confirmation_id.get(receipt.confirmation_id),
                self._request_by_provider_ref.get(receipt.provider_confirmation_ref),
                self._request_by_nonce.get(receipt.replay_nonce),
            )
        )

    def record(
        self,
        *,
        request_id: str,
        receipt: VerifiedAIProviderRetentionReceipt,
    ) -> None:
        self._request_by_confirmation_id[receipt.confirmation_id] = request_id
        self._request_by_provider_ref[receipt.provider_confirmation_ref] = request_id
        self._request_by_nonce[receipt.replay_nonce] = request_id

    def restore(
        self,
        entries: Iterable[tuple[str, VerifiedAIProviderRetentionReceipt]],
    ) -> None:
        for request_id, receipt in entries:
            if self.conflicts(request_id=request_id, receipt=receipt):
                raise ValueError("snapshot contains duplicate AI provider retention identity")
            self.record(request_id=request_id, receipt=receipt)
