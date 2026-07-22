from __future__ import annotations

from app.application.report.materialization_source_contract import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_OWNER_PROOF_REF,
    REPORT_MATERIALIZATION_ROUTE,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
)
from app.domain.proof_evidence import EvidenceClass


def valid_report_materialization_source_contract() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_materialization_source_contract",
        "proofScope": "report_materialization_declaration_and_contract_compatibility",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": True,
        "aggregateBlockersCleared": REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractDeclaresMaterialization": True,
            "reportContractPreservesNonProofBoundaries": True,
            "reportOwnerProofRefLinked": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
        "reportOwnerMaterializationContractConsumed": True,
        "reportOwnerProofRef": REPORT_MATERIALIZATION_OWNER_PROOF_REF,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }
