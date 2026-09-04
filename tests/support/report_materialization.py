from __future__ import annotations

from typing import Any

from app.domain import (
    GovernedReportEvidencePack,
    ReportMaterializationReceiptEvidence,
    SourceSystem,
)
from app.ports.downstream_realization import DownstreamOwnerReceipt, DownstreamRealizationOutcome


def report_materialization_receipt_payload(
    evidence_pack: GovernedReportEvidencePack,
    *,
    idempotency_key: str,
) -> dict[str, Any]:
    report_job_id = f"report-job-{evidence_pack.report_evidence_pack_id}"
    return {
        "report_request_id": f"report-request-{evidence_pack.report_evidence_pack_id}",
        "report_job_id": report_job_id,
        "status": "data_ready",
        "materialization_status": "data_ready",
        "status_url": f"/reports/jobs/{report_job_id}",
        "idempotency_key": idempotency_key,
        "report_package_identity": {
            "report_evidence_pack_id": evidence_pack.report_evidence_pack_id,
            "conversion_intent_id": evidence_pack.conversion_intent_id,
            "candidate_id": evidence_pack.candidate_id,
            "evidence_packet_id": evidence_pack.evidence_packet_id,
            "evidence_content_fingerprint": evidence_pack.evidence_content_hash,
            "source_contract_version": "lotus_idea_evidence_pack_report_input.v1",
            "owned_product": "lotus-report:ClientReportEvidencePack:v1",
        },
        "producer": "lotus-idea",
        "source_authority": {
            "idea_evidence": "lotus-idea",
            "report_materialization": "lotus-report",
            "rendering": "lotus-render",
            "archive_record": "lotus-archive",
            "client_publication": "blocked",
        },
        "materialization_proven": True,
        "creates_report_job": True,
        "creates_rendered_output": False,
        "creates_archive_record": False,
        "grants_client_publication_authority": False,
        "supported_feature_promoted": False,
        "supportability_status": "not_certified",
        "remaining_blockers": [
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ],
        "evidence_refs": [f"idea-evidence-pack://{evidence_pack.report_evidence_pack_id}"],
        "render_job_id": None,
        "archive_document_id": None,
    }


def authoritative_report_outcome(
    evidence_pack: GovernedReportEvidencePack,
) -> DownstreamRealizationOutcome:
    report_job_id = f"report-job-{evidence_pack.report_evidence_pack_id}"
    return DownstreamRealizationOutcome.accepted_by_downstream(
        DownstreamOwnerReceipt(
            owner_authority=SourceSystem.LOTUS_REPORT,
            owner_request_id=f"report-request-{evidence_pack.report_evidence_pack_id}",
            owner_realization_id=report_job_id,
            owner_work_id=None,
            source_event_version=None,
            source_evidence_fingerprint=evidence_pack.evidence_content_hash,
            report_materialization=ReportMaterializationReceiptEvidence(
                status="data_ready",
                materialization_status="data_ready",
                status_url=f"/reports/jobs/{report_job_id}",
                report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
                conversion_intent_id=evidence_pack.conversion_intent_id,
                candidate_id=evidence_pack.candidate_id,
                evidence_packet_id=evidence_pack.evidence_packet_id,
                creates_report_job=True,
                creates_rendered_output=False,
                creates_archive_record=False,
                render_job_id=None,
                archive_document_id=None,
                supportability_status="not_certified",
                remaining_blockers=(
                    "client_publication_authority_blocked",
                    "supported_feature_promotion_missing",
                ),
            ),
        )
    )


def report_owner_receipt_response(evidence_pack: GovernedReportEvidencePack) -> dict[str, Any]:
    report_job_id = f"report-job-{evidence_pack.report_evidence_pack_id}"
    return {
        "ownerAuthority": "lotus-report",
        "ownerRequestId": f"report-request-{evidence_pack.report_evidence_pack_id}",
        "ownerRealizationId": report_job_id,
        "ownerWorkId": None,
        "sourceEventVersion": None,
        "sourceEvidenceFingerprint": evidence_pack.evidence_content_hash,
        "reportMaterialization": {
            "status": "data_ready",
            "materializationStatus": "data_ready",
            "statusUrl": f"/reports/jobs/{report_job_id}",
            "reportEvidencePackId": evidence_pack.report_evidence_pack_id,
            "conversionIntentId": evidence_pack.conversion_intent_id,
            "candidateId": evidence_pack.candidate_id,
            "evidencePacketId": evidence_pack.evidence_packet_id,
            "createsReportJob": True,
            "createsRenderedOutput": False,
            "createsArchiveRecord": False,
            "renderJobId": None,
            "archiveDocumentId": None,
            "supportabilityStatus": "not_certified",
            "remainingBlockers": [
                "client_publication_authority_blocked",
                "supported_feature_promotion_missing",
            ],
        },
    }


__all__ = [
    "authoritative_report_outcome",
    "report_materialization_receipt_payload",
    "report_owner_receipt_response",
]
