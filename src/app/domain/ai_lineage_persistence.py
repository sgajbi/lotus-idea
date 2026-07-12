from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
from typing import TYPE_CHECKING, Any, Mapping

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_action_policy import AI_ACTION_POLICY_VERSION
from app.domain.ai_output_integrity import AIOutputIntegrity
from app.domain.ai_execution_provenance import AIExecutionProvenancePosture
from app.domain.audit import AuditEvent
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import VerifiedAIProviderRetentionReceipt

if TYPE_CHECKING:
    from app.domain.persistence import CandidatePersistenceRecord


class AIExplanationLineagePersistenceDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class AIExplanationLineageRecord:
    request_id: str
    candidate_id: str
    evidence_packet_id: str
    evidence_content_hash: str
    workflow_pack_id: str
    workflow_pack_version: str
    purpose: str
    posture: str
    verifier_outcome: str
    fallback_used: bool
    fallback_reason: str | None
    reason_codes: tuple[str, ...]
    output_id: str | None
    claim_ids: tuple[str, ...]
    proposed_action_types: tuple[str, ...]
    action_policy_version: str
    output_integrity_version: str
    output_content_digest: str
    execution_provenance_posture: str
    actor_subject: str
    requested_at_utc: datetime
    evaluated_at_utc: datetime
    grants_downstream_authority: bool
    lineage_hash: str
    attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None
    provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "candidate_id",
            "evidence_packet_id",
            "evidence_content_hash",
            "workflow_pack_id",
            "workflow_pack_version",
            "purpose",
            "posture",
            "verifier_outcome",
            "actor_subject",
            "action_policy_version",
            "output_integrity_version",
            "output_content_digest",
            "execution_provenance_posture",
            "lineage_hash",
        ):
            _require_text(str(getattr(self, field_name)), field_name)
        if self.fallback_reason is not None:
            _require_text(self.fallback_reason, "fallback_reason")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        _require_aware_utc(self.evaluated_at_utc, "evaluated_at_utc")
        AIOutputIntegrity(
            version=self.output_integrity_version,
            digest=self.output_content_digest,
        )
        AIExecutionProvenancePosture(self.execution_provenance_posture)
        verified_posture = (
            self.execution_provenance_posture
            == AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED.value
        )
        if verified_posture != (self.attestation_receipt is not None):
            raise ValueError(
                "verified execution provenance and attestation receipt must be present together"
            )
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "claim_ids", tuple(self.claim_ids))
        object.__setattr__(self, "proposed_action_types", tuple(self.proposed_action_types))


@dataclass(frozen=True)
class AIExplanationLineagePersistenceResult:
    decision: AIExplanationLineagePersistenceDecision
    record: CandidatePersistenceRecord | None
    lineage_record: AIExplanationLineageRecord | None = None
    audit_event: AuditEvent | None = None


def ai_explanation_lineage_record_from_result(
    result: AIExplanationResult,
    *,
    attestation_receipt: VerifiedLotusAIRunAttestationReceipt | None = None,
    provider_retention_receipt: VerifiedAIProviderRetentionReceipt | None = None,
) -> AIExplanationLineageRecord:
    if (
        attestation_receipt is not None
        and attestation_receipt.consumer_request_id != result.request.request_id
    ):
        raise ValueError("attestation receipt request does not match AI explanation request")
    if provider_retention_receipt is not None:
        if attestation_receipt is None:
            raise ValueError("provider retention receipt requires a verified run attestation")
        if provider_retention_receipt.workflow_run_id != attestation_receipt.run_id:
            raise ValueError("provider retention receipt run does not match run attestation")
    output = result.output
    evaluated_at_utc = (
        output.verifier_ran_at_utc if output is not None else result.audit_event.occurred_at_utc
    )
    record_payload: dict[str, Any] = {
        "actor_subject": result.request.actor_subject,
        "candidate_id": result.request.redacted_evidence.candidate_id,
        "claim_ids": [claim.claim_id for claim in output.claims] if output is not None else [],
        "evidence_content_hash": result.request.redacted_evidence.evidence_content_hash,
        "evidence_packet_id": result.request.redacted_evidence.evidence_packet_id,
        "fallback_reason": (
            result.fallback_reason.value if result.fallback_reason is not None else None
        ),
        "fallback_used": result.fallback_used,
        "grants_downstream_authority": result.grants_downstream_authority,
        "output_id": output.output_id if output is not None else None,
        "posture": result.posture.value,
        "proposed_action_types": (
            [action.action_type.value for action in output.proposed_actions]
            if output is not None
            else []
        ),
        "action_policy_version": AI_ACTION_POLICY_VERSION,
        "output_integrity_version": result.output_integrity.version,
        "output_content_digest": result.output_integrity.digest,
        "execution_provenance_posture": result.execution_provenance_posture.value,
        "purpose": result.request.purpose.value,
        "reason_codes": [reason.value for reason in result.reason_codes],
        "request_id": result.request.request_id,
        "requested_at_utc": result.request.requested_at_utc.isoformat(),
        "evaluated_at_utc": evaluated_at_utc.isoformat(),
        "verifier_outcome": result.verifier_outcome.value,
        "workflow_pack_id": result.request.workflow_pack.workflow_pack_id,
        "workflow_pack_version": result.request.workflow_pack.workflow_pack_version,
    }
    if attestation_receipt is not None:
        record_payload["attestation_receipt"] = _attestation_receipt_payload(attestation_receipt)
    if provider_retention_receipt is not None:
        record_payload["provider_retention_receipt"] = _provider_retention_receipt_payload(
            provider_retention_receipt
        )
    lineage_hash = _hash_payload(record_payload)
    return AIExplanationLineageRecord(
        request_id=result.request.request_id,
        candidate_id=result.request.redacted_evidence.candidate_id,
        evidence_packet_id=result.request.redacted_evidence.evidence_packet_id,
        evidence_content_hash=result.request.redacted_evidence.evidence_content_hash,
        workflow_pack_id=result.request.workflow_pack.workflow_pack_id,
        workflow_pack_version=result.request.workflow_pack.workflow_pack_version,
        purpose=result.request.purpose.value,
        posture=result.posture.value,
        verifier_outcome=result.verifier_outcome.value,
        fallback_used=result.fallback_used,
        fallback_reason=(
            result.fallback_reason.value if result.fallback_reason is not None else None
        ),
        reason_codes=tuple(reason.value for reason in result.reason_codes),
        output_id=output.output_id if output is not None else None,
        claim_ids=tuple(claim.claim_id for claim in output.claims) if output is not None else (),
        proposed_action_types=(
            tuple(action.action_type.value for action in output.proposed_actions)
            if output is not None
            else ()
        ),
        action_policy_version=AI_ACTION_POLICY_VERSION,
        output_integrity_version=result.output_integrity.version,
        output_content_digest=result.output_integrity.digest,
        execution_provenance_posture=result.execution_provenance_posture.value,
        actor_subject=result.request.actor_subject,
        requested_at_utc=result.request.requested_at_utc,
        evaluated_at_utc=evaluated_at_utc,
        grants_downstream_authority=result.grants_downstream_authority,
        lineage_hash=lineage_hash,
        attestation_receipt=attestation_receipt,
        provider_retention_receipt=provider_retention_receipt,
    )


def verify_ai_explanation_lineage_record_integrity(
    record: AIExplanationLineageRecord,
) -> None:
    if record.output_integrity_version != "lotus-idea.ai-output-integrity.v1":
        return
    if (
        record.execution_provenance_posture
        == AIExecutionProvenancePosture.PRE_ATTESTATION_UNVERIFIABLE.value
    ):
        return
    expected_payload: dict[str, Any] = {
        "actor_subject": record.actor_subject,
        "candidate_id": record.candidate_id,
        "claim_ids": list(record.claim_ids),
        "evidence_content_hash": record.evidence_content_hash,
        "evidence_packet_id": record.evidence_packet_id,
        "fallback_reason": record.fallback_reason,
        "fallback_used": record.fallback_used,
        "grants_downstream_authority": record.grants_downstream_authority,
        "output_id": record.output_id,
        "posture": record.posture,
        "proposed_action_types": list(record.proposed_action_types),
        "action_policy_version": record.action_policy_version,
        "output_integrity_version": record.output_integrity_version,
        "output_content_digest": record.output_content_digest,
        "execution_provenance_posture": record.execution_provenance_posture,
        "purpose": record.purpose,
        "reason_codes": list(record.reason_codes),
        "request_id": record.request_id,
        "requested_at_utc": record.requested_at_utc.isoformat(),
        "evaluated_at_utc": record.evaluated_at_utc.isoformat(),
        "verifier_outcome": record.verifier_outcome,
        "workflow_pack_id": record.workflow_pack_id,
        "workflow_pack_version": record.workflow_pack_version,
    }
    if record.attestation_receipt is not None:
        expected_payload["attestation_receipt"] = _attestation_receipt_payload(
            record.attestation_receipt
        )
    if record.provider_retention_receipt is not None:
        expected_payload["provider_retention_receipt"] = _provider_retention_receipt_payload(
            record.provider_retention_receipt
        )
    expected = _hash_payload(expected_payload)
    if record.lineage_hash != expected:
        raise ValueError("AI explanation lineage hash does not match persisted content")


def _hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _attestation_receipt_payload(
    receipt: VerifiedLotusAIRunAttestationReceipt | None,
) -> dict[str, object] | None:
    if receipt is None:
        return None
    return {
        "run_id": receipt.run_id,
        "consumer_request_id": receipt.consumer_request_id,
        "replay_nonce": receipt.replay_nonce,
        "key_id": receipt.key_id,
        "rotation_epoch": receipt.rotation_epoch,
        "provider_id": receipt.provider_id,
        "provider_mode": receipt.provider_mode,
        "model_id": receipt.model_id,
        "model_version": receipt.model_version,
        "model_risk_approval_ref": receipt.model_risk_approval_ref,
        "evaluator_id": receipt.evaluator_id,
        "evaluator_policy_version": receipt.evaluator_policy_version,
        "input_evidence_sha256": receipt.input_evidence_sha256,
        "output_content_sha256": receipt.output_content_sha256,
        "issued_at_utc": receipt.issued_at_utc.isoformat(),
        "expires_at_utc": receipt.expires_at_utc.isoformat(),
        "verified_at_utc": receipt.verified_at_utc.isoformat(),
    }


def _provider_retention_receipt_payload(
    receipt: VerifiedAIProviderRetentionReceipt,
) -> dict[str, object]:
    return {
        "confirmation_id": receipt.confirmation_id,
        "workflow_run_id": receipt.workflow_run_id,
        "tenant_id": receipt.tenant_id,
        "provider_confirmation_ref": receipt.provider_confirmation_ref,
        "retention_policy_id": receipt.retention_policy_id,
        "outcome": receipt.outcome.value,
        "evidence_sha256": receipt.evidence_sha256,
        "provider_failure_code": receipt.provider_failure_code,
        "deletion_confirmed": receipt.deletion_confirmed,
        "supportability_status": receipt.supportability_status,
        "replay_nonce": receipt.replay_nonce,
        "key_id": receipt.key_id,
        "rotation_epoch": receipt.rotation_epoch,
        "provider_decision_at_utc": receipt.provider_decision_at_utc.isoformat(),
        "issued_at_utc": receipt.issued_at_utc.isoformat(),
        "expires_at_utc": receipt.expires_at_utc.isoformat(),
        "verified_at_utc": receipt.verified_at_utc.isoformat(),
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
