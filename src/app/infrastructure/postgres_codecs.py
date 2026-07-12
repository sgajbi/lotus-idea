from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from app.domain.access_scope import ReviewAccessScope
from app.domain.ai_lineage_persistence import (
    AIExplanationLineageRecord,
    ai_provider_retention_receipt_to_mapping,
    verify_ai_explanation_lineage_record_integrity,
)
from app.domain.conversion_governance import (
    ConversionBoundary,
    GovernedConversionIntent,
    GovernedConversionOutcome,
)
from app.domain.ideas import (
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaConversionIntent,
    IdeaConversionOutcome,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
)
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import (
    AIProviderRetentionOutcome,
    VerifiedAIProviderRetentionReceipt,
)
from app.domain.report_evidence import (
    GovernedReportEvidencePack,
    ReportEvidencePackBoundary,
    ReportEvidencePackPurpose,
    ReportEvidenceSourceSummary,
)
from app.domain.review_governance import (
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewAction,
    ReviewActorRole,
)
from app.ports.evidence_payloads import access_scope_payload, source_ref_payload

__all__ = (
    "ai_explanation_lineage_from_json",
    "ai_explanation_lineage_to_json",
    "conversion_intent_from_json",
    "conversion_intent_to_json",
    "conversion_outcome_from_json",
    "conversion_outcome_to_json",
    "decode_datetime",
    "feedback_event_from_json",
    "feedback_event_to_json",
    "idea_candidate_from_json",
    "idea_candidate_to_json",
    "read_json_object",
    "read_row_value",
    "report_evidence_pack_from_json",
    "report_evidence_pack_to_json",
    "review_decision_from_json",
    "review_decision_to_json",
)


def read_row_value(row: Any, key: str) -> Any:
    return _row(row, key)


def read_json_object(row: Any, key: str) -> dict[str, Any]:
    return _json(row, key)


def decode_datetime(value: Any) -> datetime:
    return _datetime(value)


def idea_candidate_to_json(candidate: IdeaCandidate) -> dict[str, Any]:
    return _candidate_to_json(candidate)


def idea_candidate_from_json(payload: Mapping[str, Any]) -> IdeaCandidate:
    return _candidate_from_json(payload)


def review_decision_to_json(decision: GovernedReviewDecision) -> dict[str, Any]:
    return _review_decision_to_json(decision)


def review_decision_from_json(payload: Mapping[str, Any]) -> GovernedReviewDecision:
    return _review_decision_from_json(payload)


def feedback_event_to_json(feedback: GovernedFeedbackEvent) -> dict[str, Any]:
    return _feedback_event_to_json(feedback)


def feedback_event_from_json(payload: Mapping[str, Any]) -> GovernedFeedbackEvent:
    return _feedback_event_from_json(payload)


def conversion_intent_to_json(intent: GovernedConversionIntent) -> dict[str, Any]:
    return _conversion_intent_to_json(intent)


def conversion_intent_from_json(payload: Mapping[str, Any]) -> GovernedConversionIntent:
    return _conversion_intent_from_json(payload)


def conversion_outcome_to_json(outcome: GovernedConversionOutcome) -> dict[str, Any]:
    return _conversion_outcome_to_json(outcome)


def conversion_outcome_from_json(payload: Mapping[str, Any]) -> GovernedConversionOutcome:
    return _conversion_outcome_from_json(payload)


def report_evidence_pack_to_json(pack: GovernedReportEvidencePack) -> dict[str, Any]:
    return _report_evidence_pack_to_json(pack)


def report_evidence_pack_from_json(payload: Mapping[str, Any]) -> GovernedReportEvidencePack:
    return _report_evidence_pack_from_json(payload)


def ai_explanation_lineage_to_json(record: AIExplanationLineageRecord) -> dict[str, Any]:
    return _ai_explanation_lineage_to_json(record)


def ai_explanation_lineage_from_json(
    payload: Mapping[str, Any],
    *,
    expected_integrity_version: str | None = None,
    expected_content_digest: str | None = None,
    expected_execution_provenance_posture: str | None = None,
) -> AIExplanationLineageRecord:
    record = _ai_explanation_lineage_from_json(payload)
    if (
        expected_integrity_version is not None
        and record.output_integrity_version != expected_integrity_version
    ):
        raise ValueError("AI explanation lineage integrity version column mismatch")
    if (
        expected_content_digest is not None
        and record.output_content_digest != expected_content_digest
    ):
        raise ValueError("AI explanation lineage content digest column mismatch")
    if (
        expected_execution_provenance_posture is not None
        and record.execution_provenance_posture != expected_execution_provenance_posture
    ):
        raise ValueError("AI explanation lineage execution provenance column mismatch")
    verify_ai_explanation_lineage_record_integrity(record)
    return record


def _row(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row[key]
    raise TypeError("PostgresIdeaRepository requires mapping rows")


def _json(row: Any, key: str) -> dict[str, Any]:
    value = _row(row, key)
    if hasattr(value, "obj"):
        value = value.obj
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a JSON object")
    return value


def _candidate_to_json(candidate: IdeaCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "family": candidate.family.value,
        "lifecycle_status": candidate.lifecycle_status.value,
        "review_posture": candidate.review_posture.value,
        "evidence_packet": _evidence_packet_to_json(candidate.evidence_packet),
        "source_signal_ids": list(candidate.source_signal_ids),
        "score": _score_to_json(candidate.score) if candidate.score is not None else None,
        "access_scope": access_scope_payload(candidate.access_scope),
        "suppression_reason": (
            candidate.suppression_reason.value if candidate.suppression_reason is not None else None
        ),
        "created_at_utc": candidate.created_at_utc.isoformat(),
        "updated_at_utc": candidate.updated_at_utc.isoformat(),
    }


def _candidate_from_json(payload: Mapping[str, Any]) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=str(payload["candidate_id"]),
        family=OpportunityFamily(payload["family"]),
        lifecycle_status=IdeaLifecycleStatus(payload["lifecycle_status"]),
        review_posture=ReviewPosture(payload["review_posture"]),
        evidence_packet=_evidence_packet_from_json(payload["evidence_packet"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        score=(_score_from_json(payload["score"]) if payload.get("score") is not None else None),
        access_scope=(
            _access_scope_from_json(payload["access_scope"])
            if payload.get("access_scope") is not None
            else None
        ),
        suppression_reason=(
            SuppressionReason(payload["suppression_reason"])
            if payload.get("suppression_reason") is not None
            else None
        ),
        created_at_utc=_datetime(payload["created_at_utc"]),
        updated_at_utc=_datetime(payload["updated_at_utc"]),
    )


def _review_decision_to_json(decision: GovernedReviewDecision) -> dict[str, Any]:
    return {
        "review_id": decision.review_id,
        "candidate_id": decision.candidate_id,
        "evidence_packet_id": decision.evidence_packet_id,
        "evidence_content_hash": decision.evidence_content_hash,
        "action": decision.action.value,
        "resulting_posture": decision.resulting_posture.value,
        "actor_subject": decision.actor_subject,
        "actor_role": decision.actor_role.value,
        "reason_codes": [reason.value for reason in decision.reason_codes],
        "decided_at_utc": decision.decided_at_utc.isoformat(),
        "suppression_reason": (
            decision.suppression_reason.value if decision.suppression_reason is not None else None
        ),
        "snoozed_until_utc": (
            decision.snoozed_until_utc.isoformat()
            if decision.snoozed_until_utc is not None
            else None
        ),
    }


def _review_decision_from_json(payload: Mapping[str, Any]) -> GovernedReviewDecision:
    return GovernedReviewDecision(
        review_id=str(payload["review_id"]),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        action=ReviewAction(payload["action"]),
        resulting_posture=ReviewPosture(payload["resulting_posture"]),
        actor_subject=str(payload["actor_subject"]),
        actor_role=ReviewActorRole(payload["actor_role"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        decided_at_utc=_datetime(payload["decided_at_utc"]),
        suppression_reason=(
            SuppressionReason(payload["suppression_reason"])
            if payload.get("suppression_reason") is not None
            else None
        ),
        snoozed_until_utc=(
            _datetime(payload["snoozed_until_utc"])
            if payload.get("snoozed_until_utc") is not None
            else None
        ),
    )


def _feedback_event_to_json(feedback: GovernedFeedbackEvent) -> dict[str, Any]:
    return {
        "feedback": {
            "feedback_id": feedback.feedback.feedback_id,
            "outcome": feedback.feedback.outcome.value,
            "actor_role": feedback.feedback.actor_role,
            "reason_codes": [reason.value for reason in feedback.feedback.reason_codes],
            "recorded_at_utc": feedback.feedback.recorded_at_utc.isoformat(),
        },
        "candidate_id": feedback.candidate_id,
        "evidence_packet_id": feedback.evidence_packet_id,
        "evidence_content_hash": feedback.evidence_content_hash,
        "source_signal_ids": list(feedback.source_signal_ids),
        "actor_subject": feedback.actor_subject,
        "actor_role": feedback.actor_role.value,
    }


def _feedback_event_from_json(payload: Mapping[str, Any]) -> GovernedFeedbackEvent:
    from app.domain.ideas import FeedbackOutcome, IdeaFeedback

    feedback = payload["feedback"]
    return GovernedFeedbackEvent(
        feedback=IdeaFeedback(
            feedback_id=str(feedback["feedback_id"]),
            outcome=FeedbackOutcome(feedback["outcome"]),
            actor_role=str(feedback["actor_role"]),
            reason_codes=tuple(ReasonCode(value) for value in feedback["reason_codes"]),
            recorded_at_utc=_datetime(feedback["recorded_at_utc"]),
        ),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        actor_subject=str(payload["actor_subject"]),
        actor_role=ReviewActorRole(payload["actor_role"]),
    )


def _conversion_intent_to_json(intent: GovernedConversionIntent) -> dict[str, Any]:
    return {
        "intent": {
            "conversion_intent_id": intent.intent.conversion_intent_id,
            "candidate_id": intent.intent.candidate_id,
            "target": intent.intent.target.value,
            "source_status": intent.intent.source_status.value,
            "requested_at_utc": intent.intent.requested_at_utc.isoformat(),
        },
        "evidence_packet_id": intent.evidence_packet_id,
        "evidence_content_hash": intent.evidence_content_hash,
        "source_signal_ids": list(intent.source_signal_ids),
        "actor_subject": intent.actor_subject,
        "idempotency_key": intent.idempotency_key,
        "reason_codes": [reason.value for reason in intent.reason_codes],
        "target_source_authority": intent.target_source_authority.value,
        "boundary": intent.boundary.value,
    }


def _conversion_intent_from_json(payload: Mapping[str, Any]) -> GovernedConversionIntent:
    intent = payload["intent"]
    return GovernedConversionIntent(
        intent=IdeaConversionIntent(
            conversion_intent_id=str(intent["conversion_intent_id"]),
            candidate_id=str(intent["candidate_id"]),
            target=ConversionTarget(intent["target"]),
            source_status=IdeaLifecycleStatus(intent["source_status"]),
            requested_at_utc=_datetime(intent["requested_at_utc"]),
        ),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        actor_subject=str(payload["actor_subject"]),
        idempotency_key=str(payload["idempotency_key"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        target_source_authority=SourceSystem(payload["target_source_authority"]),
        boundary=ConversionBoundary(payload["boundary"]),
    )


def _conversion_outcome_to_json(outcome: GovernedConversionOutcome) -> dict[str, Any]:
    return {
        "outcome": {
            "conversion_outcome_id": outcome.outcome.conversion_outcome_id,
            "conversion_intent_id": outcome.outcome.conversion_intent_id,
            "status": outcome.outcome.status.value,
            "downstream_reference": outcome.outcome.downstream_reference,
            "recorded_at_utc": outcome.outcome.recorded_at_utc.isoformat(),
        },
        "conversion_intent_id": outcome.conversion_intent_id,
        "target": outcome.target.value,
        "source_system": outcome.source_system.value,
        "boundary": outcome.boundary.value,
        "source_event_version": outcome.source_event_version,
        "actor_subject": outcome.actor_subject,
        "supersedes_conversion_outcome_id": outcome.supersedes_conversion_outcome_id,
        "correction_reason": outcome.correction_reason,
    }


def _conversion_outcome_from_json(payload: Mapping[str, Any]) -> GovernedConversionOutcome:
    outcome = payload["outcome"]
    return GovernedConversionOutcome(
        outcome=IdeaConversionOutcome(
            conversion_outcome_id=str(outcome["conversion_outcome_id"]),
            conversion_intent_id=str(outcome["conversion_intent_id"]),
            status=ConversionOutcomeStatus(outcome["status"]),
            downstream_reference=outcome.get("downstream_reference"),
            recorded_at_utc=_datetime(outcome["recorded_at_utc"]),
        ),
        conversion_intent_id=str(payload["conversion_intent_id"]),
        target=ConversionTarget(payload["target"]),
        source_system=SourceSystem(payload["source_system"]),
        boundary=ConversionBoundary(payload["boundary"]),
        source_event_version=int(payload["source_event_version"]),
        actor_subject=str(payload["actor_subject"]),
        supersedes_conversion_outcome_id=(
            str(payload["supersedes_conversion_outcome_id"])
            if payload.get("supersedes_conversion_outcome_id") is not None
            else None
        ),
        correction_reason=(
            str(payload["correction_reason"])
            if payload.get("correction_reason") is not None
            else None
        ),
    )


def _report_evidence_pack_to_json(pack: GovernedReportEvidencePack) -> dict[str, Any]:
    return {
        "report_evidence_pack_id": pack.report_evidence_pack_id,
        "conversion_intent_id": pack.conversion_intent_id,
        "candidate_id": pack.candidate_id,
        "evidence_packet_id": pack.evidence_packet_id,
        "evidence_content_hash": pack.evidence_content_hash,
        "source_signal_ids": list(pack.source_signal_ids),
        "source_summaries": [
            _report_source_summary_to_json(summary) for summary in pack.source_summaries
        ],
        "purpose": pack.purpose.value,
        "actor_subject": pack.actor_subject,
        "idempotency_key": pack.idempotency_key,
        "reason_codes": [reason.value for reason in pack.reason_codes],
        "requested_at_utc": pack.requested_at_utc.isoformat(),
        "retention_policy_ref": pack.retention_policy_ref,
        "report_source_authority": pack.report_source_authority.value,
        "render_source_authority": pack.render_source_authority.value,
        "archive_source_authority": pack.archive_source_authority.value,
        "boundary": pack.boundary.value,
    }


def _report_evidence_pack_from_json(payload: Mapping[str, Any]) -> GovernedReportEvidencePack:
    return GovernedReportEvidencePack(
        report_evidence_pack_id=str(payload["report_evidence_pack_id"]),
        conversion_intent_id=str(payload["conversion_intent_id"]),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        source_signal_ids=tuple(payload["source_signal_ids"]),
        source_summaries=tuple(
            _report_source_summary_from_json(summary) for summary in payload["source_summaries"]
        ),
        purpose=ReportEvidencePackPurpose(payload["purpose"]),
        actor_subject=str(payload["actor_subject"]),
        idempotency_key=str(payload["idempotency_key"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        requested_at_utc=_datetime(payload["requested_at_utc"]),
        retention_policy_ref=str(payload["retention_policy_ref"]),
        report_source_authority=SourceSystem(payload["report_source_authority"]),
        render_source_authority=SourceSystem(payload["render_source_authority"]),
        archive_source_authority=SourceSystem(payload["archive_source_authority"]),
        boundary=ReportEvidencePackBoundary(payload["boundary"]),
    )


def _ai_explanation_lineage_to_json(record: AIExplanationLineageRecord) -> dict[str, Any]:
    return {
        "request_id": record.request_id,
        "candidate_id": record.candidate_id,
        "evidence_packet_id": record.evidence_packet_id,
        "evidence_content_hash": record.evidence_content_hash,
        "workflow_pack_id": record.workflow_pack_id,
        "workflow_pack_version": record.workflow_pack_version,
        "purpose": record.purpose,
        "posture": record.posture,
        "verifier_outcome": record.verifier_outcome,
        "fallback_used": record.fallback_used,
        "fallback_reason": record.fallback_reason,
        "reason_codes": list(record.reason_codes),
        "output_id": record.output_id,
        "claim_ids": list(record.claim_ids),
        "proposed_action_types": list(record.proposed_action_types),
        "action_policy_version": record.action_policy_version,
        "output_integrity_version": record.output_integrity_version,
        "output_content_digest": record.output_content_digest,
        "execution_provenance_posture": record.execution_provenance_posture,
        "actor_subject": record.actor_subject,
        "requested_at_utc": record.requested_at_utc.isoformat(),
        "evaluated_at_utc": record.evaluated_at_utc.isoformat(),
        "grants_downstream_authority": record.grants_downstream_authority,
        "lineage_hash": record.lineage_hash,
        "attestation_receipt": (
            _attestation_receipt_to_json(record.attestation_receipt)
            if record.attestation_receipt is not None
            else None
        ),
        "provider_retention_receipt": (
            ai_provider_retention_receipt_to_mapping(record.provider_retention_receipt)
            if record.provider_retention_receipt is not None
            else None
        ),
    }


def _ai_explanation_lineage_from_json(
    payload: Mapping[str, Any],
) -> AIExplanationLineageRecord:
    return AIExplanationLineageRecord(
        request_id=str(payload["request_id"]),
        candidate_id=str(payload["candidate_id"]),
        evidence_packet_id=str(payload["evidence_packet_id"]),
        evidence_content_hash=str(payload["evidence_content_hash"]),
        workflow_pack_id=str(payload["workflow_pack_id"]),
        workflow_pack_version=str(payload["workflow_pack_version"]),
        purpose=str(payload["purpose"]),
        posture=str(payload["posture"]),
        verifier_outcome=str(payload["verifier_outcome"]),
        fallback_used=bool(payload["fallback_used"]),
        fallback_reason=(
            str(payload["fallback_reason"]) if payload.get("fallback_reason") is not None else None
        ),
        reason_codes=tuple(str(value) for value in payload["reason_codes"]),
        output_id=str(payload["output_id"]) if payload.get("output_id") is not None else None,
        claim_ids=tuple(str(value) for value in payload.get("claim_ids", ())),
        proposed_action_types=tuple(
            str(value) for value in payload.get("proposed_action_types", ())
        ),
        action_policy_version=str(payload["action_policy_version"]),
        output_integrity_version=str(payload["output_integrity_version"]),
        output_content_digest=str(payload["output_content_digest"]),
        execution_provenance_posture=str(payload["execution_provenance_posture"]),
        actor_subject=str(payload["actor_subject"]),
        requested_at_utc=_datetime(payload["requested_at_utc"]),
        evaluated_at_utc=_datetime(payload["evaluated_at_utc"]),
        grants_downstream_authority=bool(payload["grants_downstream_authority"]),
        lineage_hash=str(payload["lineage_hash"]),
        attestation_receipt=(
            _attestation_receipt_from_json(payload["attestation_receipt"])
            if payload.get("attestation_receipt") is not None
            else None
        ),
        provider_retention_receipt=(
            _provider_retention_receipt_from_json(payload["provider_retention_receipt"])
            if payload.get("provider_retention_receipt") is not None
            else None
        ),
    )


def _attestation_receipt_to_json(
    receipt: VerifiedLotusAIRunAttestationReceipt,
) -> dict[str, object]:
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


def _attestation_receipt_from_json(
    payload: Mapping[str, Any],
) -> VerifiedLotusAIRunAttestationReceipt:
    return VerifiedLotusAIRunAttestationReceipt(
        run_id=str(payload["run_id"]),
        consumer_request_id=str(payload["consumer_request_id"]),
        replay_nonce=str(payload["replay_nonce"]),
        key_id=str(payload["key_id"]),
        rotation_epoch=int(payload["rotation_epoch"]),
        provider_id=str(payload["provider_id"]),
        provider_mode=str(payload["provider_mode"]),
        model_id=str(payload["model_id"]),
        model_version=str(payload["model_version"]),
        model_risk_approval_ref=str(payload["model_risk_approval_ref"]),
        evaluator_id=str(payload["evaluator_id"]),
        evaluator_policy_version=str(payload["evaluator_policy_version"]),
        input_evidence_sha256=str(payload["input_evidence_sha256"]),
        output_content_sha256=str(payload["output_content_sha256"]),
        issued_at_utc=_datetime(payload["issued_at_utc"]),
        expires_at_utc=_datetime(payload["expires_at_utc"]),
        verified_at_utc=_datetime(payload["verified_at_utc"]),
    )


def _provider_retention_receipt_from_json(
    payload: Mapping[str, Any],
) -> VerifiedAIProviderRetentionReceipt:
    return VerifiedAIProviderRetentionReceipt(
        confirmation_id=str(payload["confirmation_id"]),
        workflow_run_id=str(payload["workflow_run_id"]),
        tenant_id=str(payload["tenant_id"]),
        provider_confirmation_ref=str(payload["provider_confirmation_ref"]),
        retention_policy_id=str(payload["retention_policy_id"]),
        outcome=AIProviderRetentionOutcome(str(payload["outcome"])),
        evidence_sha256=str(payload["evidence_sha256"]),
        provider_failure_code=(
            str(payload["provider_failure_code"])
            if payload.get("provider_failure_code") is not None
            else None
        ),
        deletion_confirmed=bool(payload["deletion_confirmed"]),
        supportability_status=str(payload["supportability_status"]),
        replay_nonce=str(payload["replay_nonce"]),
        key_id=str(payload["key_id"]),
        rotation_epoch=int(payload["rotation_epoch"]),
        provider_decision_at_utc=_datetime(payload["provider_decision_at_utc"]),
        issued_at_utc=_datetime(payload["issued_at_utc"]),
        expires_at_utc=_datetime(payload["expires_at_utc"]),
        verified_at_utc=_datetime(payload["verified_at_utc"]),
    )


def _access_scope_from_json(payload: Mapping[str, Any]) -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id=str(payload["tenant_id"]),
        book_id=str(payload["book_id"]),
        portfolio_id=str(payload["portfolio_id"]),
        client_id=str(payload["client_id"]),
    )


def _evidence_packet_to_json(packet: IdeaEvidencePacket) -> dict[str, Any]:
    return {
        "evidence_packet_id": packet.evidence_packet_id,
        "supportability": packet.supportability.value,
        "source_refs": [source_ref_payload(source_ref) for source_ref in packet.source_refs],
        "lineage_ref": _lineage_ref_to_json(packet.lineage_ref),
        "reason_codes": [reason.value for reason in packet.reason_codes],
        "unsupported_reasons": [reason.value for reason in packet.unsupported_reasons],
        "created_at_utc": packet.created_at_utc.isoformat(),
    }


def _evidence_packet_from_json(payload: Mapping[str, Any]) -> IdeaEvidencePacket:
    return IdeaEvidencePacket(
        evidence_packet_id=str(payload["evidence_packet_id"]),
        supportability=EvidenceSupportability(payload["supportability"]),
        source_refs=tuple(_source_ref_from_json(item) for item in payload["source_refs"]),
        lineage_ref=_lineage_ref_from_json(payload["lineage_ref"]),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
        unsupported_reasons=tuple(
            UnsupportedEvidenceReason(value) for value in payload["unsupported_reasons"]
        ),
        created_at_utc=_datetime(payload["created_at_utc"]),
    )


def _lineage_ref_to_json(lineage_ref: LineageRef) -> dict[str, Any]:
    return {
        "lineage_id": lineage_ref.lineage_id,
        "source_refs": [source_ref_payload(source_ref) for source_ref in lineage_ref.source_refs],
        "content_hash": lineage_ref.content_hash,
    }


def _lineage_ref_from_json(payload: Mapping[str, Any]) -> LineageRef:
    return LineageRef(
        lineage_id=str(payload["lineage_id"]),
        source_refs=tuple(_source_ref_from_json(item) for item in payload["source_refs"]),
        content_hash=str(payload["content_hash"]),
    )


def _source_ref_from_json(payload: Mapping[str, Any]) -> SourceRef:
    return SourceRef(
        product_id=str(payload["product_id"]),
        source_system=SourceSystem(payload["source_system"]),
        product_version=str(payload["product_version"]),
        route=str(payload["route"]),
        as_of_date=date.fromisoformat(str(payload["as_of_date"])),
        generated_at_utc=_datetime(payload["generated_at_utc"]),
        content_hash=str(payload["content_hash"]),
        data_quality_status=str(payload["data_quality_status"]),
        freshness=EvidenceFreshness(payload["freshness"]),
    )


def _score_to_json(score: IdeaScore) -> dict[str, Any]:
    return {
        "policy_version": score.policy_version,
        "score": str(score.score),
        "reason_codes": [reason.value for reason in score.reason_codes],
    }


def _score_from_json(payload: Mapping[str, Any]) -> IdeaScore:
    return IdeaScore(
        policy_version=str(payload["policy_version"]),
        score=Decimal(str(payload["score"])),
        reason_codes=tuple(ReasonCode(value) for value in payload["reason_codes"]),
    )


def _report_source_summary_to_json(summary: ReportEvidenceSourceSummary) -> dict[str, Any]:
    return {
        "product_id": summary.product_id,
        "source_system": summary.source_system.value,
        "product_version": summary.product_version,
        "as_of_date": summary.as_of_date,
        "generated_at_utc": summary.generated_at_utc.isoformat(),
        "content_hash": summary.content_hash,
        "data_quality_status": summary.data_quality_status,
        "freshness": summary.freshness,
    }


def _report_source_summary_from_json(
    payload: Mapping[str, Any],
) -> ReportEvidenceSourceSummary:
    return ReportEvidenceSourceSummary(
        product_id=str(payload["product_id"]),
        source_system=SourceSystem(payload["source_system"]),
        product_version=str(payload["product_version"]),
        as_of_date=str(payload["as_of_date"]),
        generated_at_utc=_datetime(payload["generated_at_utc"]),
        content_hash=str(payload["content_hash"]),
        data_quality_status=str(payload["data_quality_status"]),
        freshness=str(payload["freshness"]),
    )


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
