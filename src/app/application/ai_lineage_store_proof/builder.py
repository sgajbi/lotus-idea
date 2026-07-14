from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.ai_lineage_store_proof.contract import (
    AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
    AI_LINEAGE_STORE_REQUIRED_EVIDENCE_CLASS,
    REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS,
    REQUIRED_AI_LINEAGE_STORE_ASSERTIONS,
    REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS,
    TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY,
    TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME,
    TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH,
)
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain.proof_evidence import (
    CIExecutionReceipt,
    EvidenceClass,
    ci_execution_receipt_digest,
    ci_execution_receipt_from_mapping,
    ci_execution_receipt_is_well_formed,
    evidence_class_can_clear,
)


_CERTIFICATION_BLOCKER = "certified_ai_lineage_store_missing"


def build_ai_lineage_store_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    ci_execution_receipt: CIExecutionReceipt | None = None,
) -> dict[str, Any]:
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS)
    source_contract_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ", "Main Releasability /"),
    ) and required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    receipt_valid = bool(
        ci_execution_receipt and _receipt_satisfies_ai_lineage_policy(ci_execution_receipt)
    )
    proof_valid = timezone_aware and source_contract_present and receipt_valid
    receipt_payload = asdict(ci_execution_receipt) if ci_execution_receipt else None
    remaining_blockers: tuple[str, ...] = REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS
    if not proof_valid:
        remaining_blockers = (_CERTIFICATION_BLOCKER, *remaining_blockers)
    return {
        "schemaVersion": AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "postgres_ai_lineage_ci_execution",
        "proofScope": "mainline_ci_execution_receipt",
        "evidenceClass": EvidenceClass.CI_EXECUTION.value,
        "requiredEvidenceClass": AI_LINEAGE_STORE_REQUIRED_EVIDENCE_CLASS.value,
        "aiLineageStoreProofValid": proof_valid,
        "aggregateBlockersCleared": (_CERTIFICATION_BLOCKER,) if proof_valid else (),
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "sourceContractEvidencePresent": source_contract_present,
            "ciExecutionReceiptPresent": ci_execution_receipt is not None,
            "ciExecutionReceiptValid": receipt_valid,
            "evidenceClassMatchesBlocker": evidence_class_can_clear(
                actual=EvidenceClass.CI_EXECUTION,
                required=AI_LINEAGE_STORE_REQUIRED_EVIDENCE_CLASS,
            ),
        },
        "ciExecutionReceipt": receipt_payload,
        "ciExecutionReceiptSha256": (
            ci_execution_receipt_digest(ci_execution_receipt) if ci_execution_receipt else None
        ),
        "remainingCertificationBlockers": remaining_blockers,
        "durableAiLineageStoreBacked": proof_valid,
        "lotusAiRuntimeExecuted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def ai_lineage_store_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    required_fields = {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "requiredEvidenceClass",
        "aiLineageStoreProofValid",
        "aggregateBlockersCleared",
        "evidenceRefs",
        "proofChecks",
        "ciExecutionReceipt",
        "ciExecutionReceiptSha256",
        "remainingCertificationBlockers",
        "durableAiLineageStoreBacked",
        "lotusAiRuntimeExecuted",
        "supportedFeaturePromoted",
        "proofClosed",
    }
    if (
        not required_fields
        <= set(payload)
        <= {
            *required_fields,
            AGGREGATE_PROOF_PROVENANCE_KEY,
        }
    ):
        return False
    receipt_payload = payload.get("ciExecutionReceipt")
    if not isinstance(receipt_payload, Mapping):
        return False
    receipt = ci_execution_receipt_from_mapping(receipt_payload)
    if receipt is None or not _receipt_satisfies_ai_lineage_policy(receipt):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping) or set(proof_checks) != {
        "timezoneAwareGeneratedAtUtc",
        "sourceContractEvidencePresent",
        "ciExecutionReceiptPresent",
        "ciExecutionReceiptValid",
        "evidenceClassMatchesBlocker",
    }:
        return False
    return (
        payload.get("schemaVersion") == AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofType") == "postgres_ai_lineage_ci_execution"
        and payload.get("proofScope") == "mainline_ci_execution_receipt"
        and payload.get("evidenceClass") == EvidenceClass.CI_EXECUTION.value
        and payload.get("requiredEvidenceClass") == AI_LINEAGE_STORE_REQUIRED_EVIDENCE_CLASS.value
        and payload.get("aiLineageStoreProofValid") is True
        and payload.get("durableAiLineageStoreBacked") is True
        and payload.get("lotusAiRuntimeExecuted") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and is_timezone_aware_datetime_text(payload.get("generatedAtUtc"))
        and tuple(payload.get("aggregateBlockersCleared") or ()) == (_CERTIFICATION_BLOCKER,)
        and tuple(payload.get("evidenceRefs") or ()) == REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS
        and proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("sourceContractEvidencePresent") is True
        and proof_checks.get("ciExecutionReceiptPresent") is True
        and proof_checks.get("ciExecutionReceiptValid") is True
        and proof_checks.get("evidenceClassMatchesBlocker") is True
        and payload.get("ciExecutionReceiptSha256") == ci_execution_receipt_digest(receipt)
    )


def _receipt_satisfies_ai_lineage_policy(receipt: CIExecutionReceipt) -> bool:
    return (
        ci_execution_receipt_is_well_formed(receipt)
        and receipt.repository == TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY
        and receipt.workflow_path == TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH
        and receipt.workflow_name == TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME
        and receipt.job_name == TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME
        and receipt.source_ref == TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF
        and receipt.artifact_name == TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME
        and receipt.assertions == REQUIRED_AI_LINEAGE_STORE_ASSERTIONS
    )
