from __future__ import annotations

from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.report_evidence import ReportEvidencePackApiResponse


REPORT_EVIDENCE_PACK_OPERATION_PATH = (
    "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs"
)
REPORT_EVIDENCE_PACK_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New report evidence-pack request accepted and persisted",
    "replayed": "Existing report evidence-pack request replayed without duplicate mutation",
}


def build_report_evidence_pack_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_report_evidence_pack_response(
            {
                "reportEvidencePack": {
                    "reportEvidencePackId": "report-evidence-pack-001",
                    "conversionIntentId": "conversion-report-001",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "purpose": "client_review_report_section",
                    "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                    "evidenceContentHash": "sha256:evidence-lineage",
                    "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                    "sourceSummaries": [
                        {
                            "productId": "lotus-core:PortfolioStateSnapshot:v1",
                            "sourceSystem": "lotus-core",
                            "productVersion": "v1",
                            "asOfDate": "2026-06-21",
                            "generatedAtUtc": "2026-06-21T10:00:00Z",
                            "contentHash": "sha256:portfolio-state",
                            "dataQualityStatus": "complete",
                            "freshness": "current",
                        }
                    ],
                    "reasonCodes": ["review_approved_for_conversion"],
                    "reportSourceAuthority": "lotus-report",
                    "renderSourceAuthority": "lotus-render",
                    "archiveSourceAuthority": "lotus-archive",
                    "boundary": "request_only",
                    "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
                    "requestedAtUtc": "2026-06-21T10:25:00Z",
                    "grantsClientPublicationAuthority": False,
                    "createsRenderedOutput": False,
                    "createsArchiveRecord": False,
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.report_evidence_pack.requested",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_report_evidence_pack_response(
            {
                "reportEvidencePack": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "converted_to_report",
                    "reviewPosture": "approved_for_conversion",
                    "auditEventType": "idea.report_evidence_pack.requested",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_report_evidence_pack_openapi_examples() -> dict[str, dict[str, Any]]:
    return build_named_openapi_examples(
        build_report_evidence_pack_response_examples(),
        REPORT_EVIDENCE_PACK_SUCCESS_EXAMPLE_SUMMARIES,
    )


def apply_report_evidence_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    apply_named_response_examples(
        openapi_schema,
        operation_path=REPORT_EVIDENCE_PACK_OPERATION_PATH,
        examples=build_report_evidence_pack_openapi_examples(),
    )
    return openapi_schema


def _validated_report_evidence_pack_response(payload: dict[str, Any]) -> dict[str, Any]:
    return ReportEvidencePackApiResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


__all__ = [
    "REPORT_EVIDENCE_PACK_OPERATION_PATH",
    "REPORT_EVIDENCE_PACK_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_report_evidence_openapi_examples",
    "build_report_evidence_pack_openapi_examples",
    "build_report_evidence_pack_response_examples",
]
