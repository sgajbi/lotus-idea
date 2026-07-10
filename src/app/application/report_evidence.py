from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain import (
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    EventLineageContext,
    ReportEvidencePackCommand,
    ReportEvidencePackResult,
    request_report_evidence_pack,
)
from app.ports.idea_repository import ReportEvidenceWorkflowRepository


@dataclass(frozen=True)
class RequestReportEvidencePackToRepositoryCommand:
    conversion_intent_id: str
    evidence_pack: ReportEvidencePackCommand
    idempotency_key: str
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class ReportEvidencePackWorkflowResult:
    evidence_pack_result: ReportEvidencePackResult | None
    persistence: EvidencePackPersistenceResult


def request_report_evidence_pack_to_repository(
    command: RequestReportEvidencePackToRepositoryCommand,
    *,
    repository: ReportEvidenceWorkflowRepository,
) -> ReportEvidencePackWorkflowResult:
    payload = _report_evidence_pack_payload(command)
    prechecked = repository.precheck_evidence_pack_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return ReportEvidencePackWorkflowResult(
            evidence_pack_result=None,
            persistence=prechecked,
        )

    conversion_intent = repository.conversion_intent_by_id(command.conversion_intent_id)
    record = repository.candidate_record_for_conversion_intent(command.conversion_intent_id)
    if conversion_intent is None or record is None:
        return ReportEvidencePackWorkflowResult(
            evidence_pack_result=None,
            persistence=EvidencePackPersistenceResult(
                decision=EvidencePackPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    evidence_pack_result = request_report_evidence_pack(
        record.candidate,
        conversion_intent,
        command.evidence_pack,
    )
    persistence = repository.record_report_evidence_pack(
        evidence_pack_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return ReportEvidencePackWorkflowResult(
        evidence_pack_result=evidence_pack_result,
        persistence=persistence,
    )


def _report_evidence_pack_payload(
    command: RequestReportEvidencePackToRepositoryCommand,
) -> dict[str, Any]:
    evidence_pack = command.evidence_pack
    return {
        "client_ready_publication_requested": evidence_pack.client_ready_publication_requested,
        "conversion_intent_id": command.conversion_intent_id,
        "purpose": evidence_pack.purpose.value,
        "reason_codes": [reason.value for reason in evidence_pack.reason_codes],
        "report_evidence_pack_id": evidence_pack.report_evidence_pack_id,
        "requested_at_utc": evidence_pack.requested_at_utc.isoformat(),
        "retention_policy_ref": evidence_pack.retention_policy_ref,
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
