from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.persisted_action_evidence import (
    PersistedActionEvidenceUnavailable,
    require_single_persisted_action,
)
from app.domain import (
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    EventLineageContext,
    GovernedReportEvidencePack,
    ReportEvidencePackCommand,
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
        if self.evidence_pack.idempotency_key != self.idempotency_key:
            raise ValueError(
                "report evidence pack idempotency key must match repository idempotency key"
            )


@dataclass(frozen=True)
class ReportEvidencePackWorkflowResult:
    report_evidence_pack: GovernedReportEvidencePack | None
    persistence: EvidencePackPersistenceResult

    def require_report_evidence_pack(self) -> GovernedReportEvidencePack:
        if self.report_evidence_pack is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful report evidence mutation has no persisted evidence pack"
            )
        return self.report_evidence_pack


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
            report_evidence_pack=_persisted_report_evidence_pack(command, prechecked),
            persistence=prechecked,
        )

    conversion_intent = repository.conversion_intent_by_id(command.conversion_intent_id)
    record = repository.candidate_record_for_conversion_intent(command.conversion_intent_id)
    if conversion_intent is None or record is None:
        return ReportEvidencePackWorkflowResult(
            report_evidence_pack=None,
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
        report_evidence_pack=_persisted_report_evidence_pack(command, persistence),
        persistence=persistence,
    )


def _persisted_report_evidence_pack(
    command: RequestReportEvidencePackToRepositoryCommand,
    persistence: EvidencePackPersistenceResult,
) -> GovernedReportEvidencePack | None:
    if persistence.decision not in {
        EvidencePackPersistenceDecision.ACCEPTED,
        EvidencePackPersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None:
        raise PersistedActionEvidenceUnavailable(
            "Successful report evidence mutation has no candidate record"
        )
    requested = command.evidence_pack
    return require_single_persisted_action(
        evidence_pack
        for evidence_pack in record.report_evidence_packs
        if (
            evidence_pack.report_evidence_pack_id == requested.report_evidence_pack_id
            and evidence_pack.conversion_intent_id == command.conversion_intent_id
            and evidence_pack.purpose is requested.purpose
            and evidence_pack.actor_subject == requested.actor_subject
            and evidence_pack.idempotency_key == command.idempotency_key
            and evidence_pack.reason_codes == requested.reason_codes
            and evidence_pack.requested_at_utc == requested.requested_at_utc
            and evidence_pack.retention_policy_ref == requested.retention_policy_ref
            and not requested.client_ready_publication_requested
        )
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
