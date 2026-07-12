from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_lineage_idempotency import (
    ai_explanation_lineage_by_request_id,
    record_ai_explanation_lineage_request_with_idempotency,
)
from app.domain.ai_lineage_persistence import (
    AIExplanationLineagePersistenceDecision,
    AIExplanationLineagePersistenceResult,
    ai_explanation_lineage_record_from_result,
)
from app.domain.idempotency import IdempotencyRecord
from app.domain.lotus_ai_attestation_replay import LotusAIAttestationReplayIndex
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import VerifiedAIProviderRetentionReceipt
from app.domain.ai_provider_retention_replay import AIProviderRetentionReplayIndex
from app.domain.persistence_models import CandidatePersistenceRecord


class InMemoryAIExplanationRepositoryMixin:
    _candidate_records: dict[str, CandidatePersistenceRecord]
    _idempotency_records: dict[str, IdempotencyRecord]
    _idempotency_candidates: dict[str, str]
    _ai_explanation_lineage_candidates: dict[str, str]
    _lotus_ai_attestation_replay: LotusAIAttestationReplayIndex
    _ai_provider_retention_replay: AIProviderRetentionReplayIndex

    def _record_for_idempotency_key(
        self, idempotency_key: str
    ) -> CandidatePersistenceRecord | None:
        raise NotImplementedError

    def record_ai_explanation_lineage(
        self,
        result: AIExplanationResult,
        *,
        attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
        provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
    ) -> AIExplanationLineagePersistenceResult:
        lineage_record = ai_explanation_lineage_record_from_result(
            result,
            attestation_receipt=attestation_receipt,
            provider_retention_receipt=provider_retention_receipt,
        )
        candidate_id = lineage_record.candidate_id
        record = self._candidate_records.get(candidate_id)
        if record is None:
            return AIExplanationLineagePersistenceResult(
                decision=AIExplanationLineagePersistenceDecision.NOT_FOUND,
                record=None,
                lineage_record=None,
            )
        if attestation_receipt is not None and self._lotus_ai_attestation_replay.conflicts(
            request_id=lineage_record.request_id,
            receipt=attestation_receipt,
        ):
            return AIExplanationLineagePersistenceResult(
                decision=AIExplanationLineagePersistenceDecision.CONFLICT,
                record=record,
                lineage_record=None,
            )
        if provider_retention_receipt is not None and self._ai_provider_retention_replay.conflicts(
            request_id=lineage_record.request_id,
            receipt=provider_retention_receipt,
        ):
            return AIExplanationLineagePersistenceResult(
                decision=AIExplanationLineagePersistenceDecision.CONFLICT,
                record=record,
                lineage_record=None,
            )
        existing_candidate_id = self._ai_explanation_lineage_candidates.get(
            lineage_record.request_id
        )
        if existing_candidate_id is not None:
            existing_record = self._candidate_records.get(existing_candidate_id)
            existing_lineage = (
                ai_explanation_lineage_by_request_id(existing_record, lineage_record.request_id)
                if existing_record is not None
                else None
            )
            if existing_lineage is not None and (
                existing_lineage.lineage_hash == lineage_record.lineage_hash
            ):
                return AIExplanationLineagePersistenceResult(
                    decision=AIExplanationLineagePersistenceDecision.REPLAYED,
                    record=existing_record,
                    lineage_record=existing_lineage,
                    audit_event=None,
                )
            return AIExplanationLineagePersistenceResult(
                decision=AIExplanationLineagePersistenceDecision.CONFLICT,
                record=existing_record,
                lineage_record=existing_lineage,
                audit_event=None,
            )
        updated = replace(
            record,
            audit_events=(*record.audit_events, result.audit_event),
            ai_explanation_lineage_records=(*record.ai_explanation_lineage_records, lineage_record),
        )
        self._candidate_records[candidate_id] = updated
        self._ai_explanation_lineage_candidates[lineage_record.request_id] = candidate_id
        if attestation_receipt is not None:
            self._lotus_ai_attestation_replay.record(
                request_id=lineage_record.request_id,
                receipt=attestation_receipt,
            )
        if provider_retention_receipt is not None:
            self._ai_provider_retention_replay.record(
                request_id=lineage_record.request_id,
                receipt=provider_retention_receipt,
            )
        return AIExplanationLineagePersistenceResult(
            decision=AIExplanationLineagePersistenceDecision.ACCEPTED,
            record=updated,
            lineage_record=lineage_record,
            audit_event=result.audit_event,
        )

    def record_ai_explanation_lineage_request(
        self,
        result: AIExplanationResult,
        *,
        idempotency_key: str,
        payload: Mapping[str, Any],
        attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
        provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
    ) -> AIExplanationLineagePersistenceResult:
        return record_ai_explanation_lineage_request_with_idempotency(
            result,
            idempotency_key=idempotency_key,
            payload=payload,
            idempotency_records=self._idempotency_records,
            idempotency_candidates=self._idempotency_candidates,
            record_for_idempotency_key=self._record_for_idempotency_key,
            record_lineage=self.record_ai_explanation_lineage,
            attestation_receipt=attestation_receipt,
            provider_retention_receipt=provider_retention_receipt,
        )
