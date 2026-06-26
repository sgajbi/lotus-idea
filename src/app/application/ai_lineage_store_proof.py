from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


AI_LINEAGE_STORE_PROOF_ENV = "LOTUS_IDEA_AI_LINEAGE_STORE_PROOF"
AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION = "lotus-idea.ai-lineage-store-proof.v1"

REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS = (
    "migrations/002_ai_explanation_lineage.sql",
    "migrations/002_ai_explanation_lineage.rollback.sql",
    "src/app/application/ai_governance.py",
    "src/app/domain/ai_lineage_persistence.py",
    "src/app/infrastructure/postgres_repository.py",
    "tests/integration/test_postgres_runtime_integration.py",
    "tests/unit/test_idea_persistence.py",
    "tests/unit/test_postgres_repository.py",
    "make postgres-integration-gate",
    "PR Merge Gate / PostgreSQL Runtime Proof",
)

REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS = (
    "lotus_ai_runtime_execution_missing",
    "workflow_pack_runtime_contract_not_certified",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)


def build_ai_lineage_store_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    proof_valid = (
        timezone_aware_generated_at_utc and file_evidence_present and make_target_evidence_present
    )
    return {
        "schemaVersion": AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "postgres_runtime_ai_lineage_store_contract",
        "proofScope": "repo_native_ci_runtime_proof",
        "aiLineageStoreProofValid": proof_valid,
        "aggregateBlockersCleared": ("certified_ai_lineage_store_missing",),
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "postgresRuntimeProofCiLane": "PR Merge Gate / PostgreSQL Runtime Proof",
        },
        "remainingCertificationBlockers": REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS,
        "durableAiLineageStoreBacked": True,
        "lotusAiRuntimeExecuted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def ai_lineage_store_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "postgres_runtime_ai_lineage_store_contract":
        return False
    if payload.get("proofScope") != "repo_native_ci_runtime_proof":
        return False
    if payload.get("aiLineageStoreProofValid") is not True:
        return False
    if payload.get("durableAiLineageStoreBacked") is not True:
        return False
    if payload.get("lotusAiRuntimeExecuted") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        "certified_ai_lineage_store_missing",
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("postgresRuntimeProofCiLane")
        == "PR Merge Gate / PostgreSQL Runtime Proof"
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("make ", "PR Merge Gate /")):
            continue
        if not (repository_root / ref).is_file():
            return False
    return True


def _required_make_target_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    try:
        makefile_text = (repository_root / "Makefile").read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        target = f"{ref.removeprefix('make ')}:"
        if target not in makefile_text:
            return False
    return True


def _is_timezone_aware_datetime_text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None
