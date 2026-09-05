from __future__ import annotations

from typing import Any, Mapping

from app.domain.presentation_receipts import (
    CandidatePresentationReceipt,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
    PresentationReceiptResult,
    validate_presentation_receipt_candidate,
)


class InMemoryPresentationReceiptRepositoryMixin:
    _candidate_records: Mapping[str, Any]
    _presentation_receipts: dict[str, CandidatePresentationReceipt]

    def presentation_receipt_by_id(
        self,
        receipt_id: str,
        *,
        candidate_id: str,
        tenant_id: str,
    ) -> CandidatePresentationReceipt | None:
        receipt = self._presentation_receipts.get(receipt_id)
        if receipt is None:
            return None
        if receipt.candidate_id != candidate_id or receipt.tenant_id != tenant_id:
            return None
        return receipt

    def record_presentation_receipt(
        self,
        receipt: CandidatePresentationReceipt,
    ) -> PresentationReceiptResult:
        existing = self._presentation_receipts.get(receipt.receipt_id)
        if existing is not None:
            if (
                existing.tenant_id != receipt.tenant_id
                or existing.candidate_id != receipt.candidate_id
            ):
                raise PresentationReceiptCandidateStateError(
                    "receipt identity is unavailable in the candidate scope"
                )
            return PresentationReceiptResult(
                decision=(
                    PresentationReceiptDecision.REPLAYED
                    if existing.has_same_producer_claim(receipt)
                    else PresentationReceiptDecision.CONFLICT
                ),
                receipt=existing,
            )

        record = self._candidate_records.get(receipt.candidate_id)
        if record is None:
            raise PresentationReceiptCandidateStateError("candidate is unavailable")
        validate_presentation_receipt_candidate(receipt, record.candidate)
        self._presentation_receipts[receipt.receipt_id] = receipt
        return PresentationReceiptResult(
            decision=PresentationReceiptDecision.ACCEPTED,
            receipt=receipt,
        )


__all__ = ["InMemoryPresentationReceiptRepositoryMixin"]
