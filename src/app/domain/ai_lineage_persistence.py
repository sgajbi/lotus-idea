from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
from typing import TYPE_CHECKING, Any, Mapping

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_action_policy import AI_ACTION_POLICY_VERSION
from app.domain.audit import AuditEvent

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
    actor_subject: str
    requested_at_utc: datetime
    evaluated_at_utc: datetime
    grants_downstream_authority: bool
    lineage_hash: str

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
            "lineage_hash",
        ):
            _require_text(str(getattr(self, field_name)), field_name)
        if self.fallback_reason is not None:
            _require_text(self.fallback_reason, "fallback_reason")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        _require_aware_utc(self.evaluated_at_utc, "evaluated_at_utc")
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
) -> AIExplanationLineageRecord:
    output = result.output
    evaluated_at_utc = (
        output.verifier_ran_at_utc if output is not None else result.audit_event.occurred_at_utc
    )
    record_payload = {
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
        "purpose": result.request.purpose.value,
        "reason_codes": [reason.value for reason in result.reason_codes],
        "request_id": result.request.request_id,
        "requested_at_utc": result.request.requested_at_utc.isoformat(),
        "evaluated_at_utc": evaluated_at_utc.isoformat(),
        "verifier_outcome": result.verifier_outcome.value,
        "workflow_pack_id": result.request.workflow_pack.workflow_pack_id,
        "workflow_pack_version": result.request.workflow_pack.workflow_pack_version,
    }
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
        actor_subject=result.request.actor_subject,
        requested_at_utc=result.request.requested_at_utc,
        evaluated_at_utc=evaluated_at_utc,
        grants_downstream_authority=result.grants_downstream_authority,
        lineage_hash=lineage_hash,
    )


def _hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
