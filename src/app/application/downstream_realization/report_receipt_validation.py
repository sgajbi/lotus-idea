from __future__ import annotations

from app.domain import (
    DownstreamSubmissionOwnerReceipt,
    GovernedReportEvidencePack,
    SourceSystem,
)
from app.ports.downstream_realization import DownstreamOwnerReceipt


def validated_report_submission_receipt(
    receipt: DownstreamOwnerReceipt,
    evidence_pack: GovernedReportEvidencePack,
) -> DownstreamSubmissionOwnerReceipt:
    """Validate and convert one Report-owned receipt for durable Idea persistence."""
    if receipt.owner_authority is not SourceSystem.LOTUS_REPORT:
        raise ValueError("Report submission requires an authoritative owner receipt")
    evidence = receipt.report_materialization
    if evidence is None:
        raise ValueError("Report owner receipt requires materialization evidence")
    expected_identity = (
        evidence_pack.report_evidence_pack_id,
        evidence_pack.conversion_intent_id,
        evidence_pack.candidate_id,
        evidence_pack.evidence_packet_id,
        evidence_pack.evidence_content_hash,
    )
    actual_identity = (
        evidence.report_evidence_pack_id,
        evidence.conversion_intent_id,
        evidence.candidate_id,
        evidence.evidence_packet_id,
        receipt.source_evidence_fingerprint,
    )
    if actual_identity != expected_identity:
        raise ValueError("Report owner receipt identity does not match the evidence pack")
    return DownstreamSubmissionOwnerReceipt(
        owner_authority=receipt.owner_authority,
        owner_request_id=receipt.owner_request_id,
        owner_realization_id=receipt.owner_realization_id,
        owner_work_id=receipt.owner_work_id,
        source_event_version=receipt.source_event_version,
        source_evidence_fingerprint=receipt.source_evidence_fingerprint,
        report_materialization=evidence,
    )
