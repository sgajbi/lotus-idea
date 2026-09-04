from __future__ import annotations

from pydantic import Field

from app.api.base_model import CamelModel
from app.domain import (
    DownstreamSubmissionOwnerReceipt,
    ReportMaterializationReceiptEvidence,
    SourceSystem,
)


class ReportMaterializationReceiptResponse(CamelModel):
    status: str
    materialization_status: str = Field(..., alias="materializationStatus")
    status_url: str = Field(..., alias="statusUrl")
    report_evidence_pack_id: str = Field(..., alias="reportEvidencePackId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    candidate_id: str = Field(..., alias="candidateId")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    creates_report_job: bool = Field(..., alias="createsReportJob")
    creates_rendered_output: bool = Field(..., alias="createsRenderedOutput")
    creates_archive_record: bool = Field(..., alias="createsArchiveRecord")
    render_job_id: str | None = Field(default=None, alias="renderJobId")
    archive_document_id: str | None = Field(default=None, alias="archiveDocumentId")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    remaining_blockers: tuple[str, ...] = Field(..., alias="remainingBlockers")

    @classmethod
    def from_domain(
        cls,
        evidence: ReportMaterializationReceiptEvidence,
    ) -> "ReportMaterializationReceiptResponse":
        return cls(
            status=evidence.status,
            materializationStatus=evidence.materialization_status,
            statusUrl=evidence.status_url,
            reportEvidencePackId=evidence.report_evidence_pack_id,
            conversionIntentId=evidence.conversion_intent_id,
            candidateId=evidence.candidate_id,
            evidencePacketId=evidence.evidence_packet_id,
            createsReportJob=evidence.creates_report_job,
            createsRenderedOutput=evidence.creates_rendered_output,
            createsArchiveRecord=evidence.creates_archive_record,
            renderJobId=evidence.render_job_id,
            archiveDocumentId=evidence.archive_document_id,
            supportabilityStatus=evidence.supportability_status,
            remainingBlockers=evidence.remaining_blockers,
        )


class DownstreamOwnerReceiptResponse(CamelModel):
    owner_authority: SourceSystem = Field(..., alias="ownerAuthority")
    owner_request_id: str = Field(..., alias="ownerRequestId")
    owner_realization_id: str = Field(..., alias="ownerRealizationId")
    owner_work_id: str | None = Field(default=None, alias="ownerWorkId")
    source_event_version: int | None = Field(default=None, alias="sourceEventVersion")
    source_evidence_fingerprint: str = Field(..., alias="sourceEvidenceFingerprint")
    report_materialization: ReportMaterializationReceiptResponse | None = Field(
        default=None,
        alias="reportMaterialization",
    )

    @classmethod
    def from_domain(
        cls,
        receipt: DownstreamSubmissionOwnerReceipt,
    ) -> "DownstreamOwnerReceiptResponse":
        return cls(
            ownerAuthority=receipt.owner_authority,
            ownerRequestId=receipt.owner_request_id,
            ownerRealizationId=receipt.owner_realization_id,
            ownerWorkId=receipt.owner_work_id,
            sourceEventVersion=receipt.source_event_version,
            sourceEvidenceFingerprint=receipt.source_evidence_fingerprint,
            reportMaterialization=(
                ReportMaterializationReceiptResponse.from_domain(receipt.report_materialization)
                if receipt.report_materialization is not None
                else None
            ),
        )


__all__ = [
    "DownstreamOwnerReceiptResponse",
    "ReportMaterializationReceiptResponse",
]
