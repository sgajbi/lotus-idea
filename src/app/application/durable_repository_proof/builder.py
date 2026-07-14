from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.durable_repository_proof.contract import (
    DURABLE_REPOSITORY_BLOCKERS_CLEARED,
    DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
    DURABLE_REPOSITORY_REQUIRED_EVIDENCE_CLASS,
    REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS,
    REQUIRED_DURABLE_REPOSITORY_ASSERTIONS,
    REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS,
    TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY,
    TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME,
    TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.domain.proof_evidence import (
    CIExecutionReceipt,
    EvidenceClass,
    ci_execution_receipt_digest,
    ci_execution_receipt_from_mapping,
    ci_execution_receipt_is_well_formed,
    evidence_class_can_clear,
)


def build_durable_repository_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    source_commit_sha: str,
    ci_execution_receipt: CIExecutionReceipt | None = None,
) -> dict[str, Any]:
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS)
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
        timezone_aware
        and ci_execution_receipt
        and _receipt_satisfies_durable_repository_policy(
            ci_execution_receipt,
            source_commit_sha=source_commit_sha,
            generated_at_utc=generated_at_utc,
        )
    )
    proof_valid = timezone_aware and source_contract_present and receipt_valid
    remaining_blockers: tuple[str, ...] = REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS
    if not proof_valid:
        remaining_blockers = (
            *DURABLE_REPOSITORY_BLOCKERS_CLEARED,
            *remaining_blockers,
        )
    return {
        "schemaVersion": DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "sourceCommitSha": source_commit_sha,
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "postgres_repository_ci_execution",
        "proofScope": "mainline_ci_execution_receipt",
        "evidenceClass": EvidenceClass.CI_EXECUTION.value,
        "requiredEvidenceClass": DURABLE_REPOSITORY_REQUIRED_EVIDENCE_CLASS.value,
        "durableRepositoryProofValid": proof_valid,
        "aggregateBlockersCleared": DURABLE_REPOSITORY_BLOCKERS_CLEARED if proof_valid else (),
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "sourceContractEvidencePresent": source_contract_present,
            "ciExecutionReceiptPresent": ci_execution_receipt is not None,
            "ciExecutionReceiptValid": receipt_valid,
            "evidenceClassMatchesBlockers": evidence_class_can_clear(
                actual=EvidenceClass.CI_EXECUTION,
                required=DURABLE_REPOSITORY_REQUIRED_EVIDENCE_CLASS,
            ),
        },
        "ciExecutionReceipt": asdict(ci_execution_receipt) if ci_execution_receipt else None,
        "ciExecutionReceiptSha256": (
            ci_execution_receipt_digest(ci_execution_receipt) if ci_execution_receipt else None
        ),
        "remainingCertificationBlockers": remaining_blockers,
        "productionStorageCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def durable_repository_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    required_fields = {
        "schemaVersion",
        "repository",
        "sourceCommitSha",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "requiredEvidenceClass",
        "durableRepositoryProofValid",
        "aggregateBlockersCleared",
        "evidenceRefs",
        "proofChecks",
        "ciExecutionReceipt",
        "ciExecutionReceiptSha256",
        "remainingCertificationBlockers",
        "productionStorageCertified",
        "supportedFeaturePromoted",
        "proofClosed",
    }
    if not required_fields <= set(payload) <= {*required_fields, AGGREGATE_PROOF_PROVENANCE_KEY}:
        return False
    receipt_payload = payload.get("ciExecutionReceipt")
    if not isinstance(receipt_payload, Mapping):
        return False
    receipt = ci_execution_receipt_from_mapping(receipt_payload)
    generated_at_utc = _aware_datetime(payload.get("generatedAtUtc"))
    source_commit_sha = payload.get("sourceCommitSha")
    if (
        receipt is None
        or generated_at_utc is None
        or not isinstance(source_commit_sha, str)
        or not _receipt_satisfies_durable_repository_policy(
            receipt,
            source_commit_sha=source_commit_sha,
            generated_at_utc=generated_at_utc,
        )
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping) or set(proof_checks) != {
        "timezoneAwareGeneratedAtUtc",
        "sourceContractEvidencePresent",
        "ciExecutionReceiptPresent",
        "ciExecutionReceiptValid",
        "evidenceClassMatchesBlockers",
    }:
        return False
    return (
        payload.get("schemaVersion") == DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofType") == "postgres_repository_ci_execution"
        and payload.get("proofScope") == "mainline_ci_execution_receipt"
        and payload.get("evidenceClass") == EvidenceClass.CI_EXECUTION.value
        and payload.get("requiredEvidenceClass") == DURABLE_REPOSITORY_REQUIRED_EVIDENCE_CLASS.value
        and payload.get("durableRepositoryProofValid") is True
        and tuple(payload.get("aggregateBlockersCleared") or ())
        == DURABLE_REPOSITORY_BLOCKERS_CLEARED
        and tuple(payload.get("evidenceRefs") or ()) == REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS
        and payload.get("productionStorageCertified") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("sourceContractEvidencePresent") is True
        and proof_checks.get("ciExecutionReceiptPresent") is True
        and proof_checks.get("ciExecutionReceiptValid") is True
        and proof_checks.get("evidenceClassMatchesBlockers") is True
        and payload.get("ciExecutionReceiptSha256") == ci_execution_receipt_digest(receipt)
    )


def _receipt_satisfies_durable_repository_policy(
    receipt: CIExecutionReceipt,
    *,
    source_commit_sha: str,
    generated_at_utc: datetime,
) -> bool:
    completed_at_utc = _aware_datetime(receipt.completed_at_utc)
    return (
        ci_execution_receipt_is_well_formed(receipt)
        and generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None
        and receipt.repository == TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY
        and receipt.workflow_path == TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH
        and receipt.workflow_name == TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME
        and receipt.job_name == TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME
        and receipt.source_commit_sha == source_commit_sha
        and receipt.source_ref == TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF
        and receipt.artifact_name == TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME
        and receipt.assertions == REQUIRED_DURABLE_REPOSITORY_ASSERTIONS
        and completed_at_utc is not None
        and completed_at_utc <= generated_at_utc
    )


def _aware_datetime(value: object) -> datetime | None:
    if not is_timezone_aware_datetime_text(value):
        return None
    assert isinstance(value, str)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
