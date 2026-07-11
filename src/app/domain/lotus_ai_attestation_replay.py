from __future__ import annotations

from collections.abc import Iterable

from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt


class LotusAIAttestationReplayIndex:
    def __init__(self) -> None:
        self._request_by_run_id: dict[str, str] = {}
        self._request_by_nonce: dict[str, str] = {}

    def conflicts(
        self,
        *,
        request_id: str,
        receipt: VerifiedLotusAIRunAttestationReceipt,
    ) -> bool:
        return any(
            existing_request_id not in {None, request_id}
            for existing_request_id in (
                self._request_by_run_id.get(receipt.run_id),
                self._request_by_nonce.get(receipt.replay_nonce),
            )
        )

    def record(
        self,
        *,
        request_id: str,
        receipt: VerifiedLotusAIRunAttestationReceipt,
    ) -> None:
        self._request_by_run_id[receipt.run_id] = request_id
        self._request_by_nonce[receipt.replay_nonce] = request_id

    def restore(
        self,
        entries: Iterable[tuple[str, VerifiedLotusAIRunAttestationReceipt]],
    ) -> None:
        for request_id, receipt in entries:
            if self.conflicts(request_id=request_id, receipt=receipt):
                raise ValueError("snapshot contains duplicate lotus-ai attestation identity")
            self.record(request_id=request_id, receipt=receipt)
