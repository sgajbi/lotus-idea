from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text


DURABLE_REPOSITORY_PROOF_ENV = "LOTUS_IDEA_DURABLE_REPOSITORY_PROOF"
DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION = "lotus-idea.durable-repository-proof.v1"

REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS = (
    "migrations/001_idea_repository_foundation.sql",
    "migrations/001_idea_repository_foundation.rollback.sql",
    "src/app/infrastructure/postgres_repository.py",
    "src/app/infrastructure/postgres_codecs.py",
    "src/app/runtime/repository_state.py",
    "tests/integration/test_postgres_runtime_integration.py",
    "make migration-contract-gate",
    "make migration-execution-gate",
    "make postgres-integration-gate",
    "PR Merge Gate / PostgreSQL Runtime Proof",
)

REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS = (
    "production_migration_deploy_evidence_missing",
    "live_core_source_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)


def build_durable_repository_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    evidence_refs = tuple(REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    proof_valid = (
        generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None
        and file_evidence_present
        and make_target_evidence_present
    )
    return {
        "schemaVersion": DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "postgres_runtime_repository_contract",
        "proofScope": "repo_native_ci_runtime_proof",
        "durableRepositoryProofValid": proof_valid,
        "aggregateBlockersCleared": ("durable_repository_not_configured",),
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
            and generated_at_utc.utcoffset() is not None,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "postgresRuntimeProofCiLane": "PR Merge Gate / PostgreSQL Runtime Proof",
        },
        "remainingCertificationBlockers": REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS,
        "productionStorageCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def durable_repository_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "postgres_runtime_repository_contract":
        return False
    if payload.get("proofScope") != "repo_native_ci_runtime_proof":
        return False
    if payload.get("durableRepositoryProofValid") is not True:
        return False
    if payload.get("productionStorageCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    blockers_cleared = payload.get("aggregateBlockersCleared")
    if tuple(blockers_cleared or ()) != ("durable_repository_not_configured",):
        return False
    evidence_refs = payload.get("evidenceRefs")
    if tuple(evidence_refs or ()) != REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS:
        return False
    remaining_blockers = payload.get("remainingCertificationBlockers")
    if tuple(remaining_blockers or ()) != REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS:
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    if proof_checks.get("timezoneAwareGeneratedAtUtc") is not True:
        return False
    if proof_checks.get("fileEvidencePresent") is not True:
        return False
    if proof_checks.get("makeTargetEvidencePresent") is not True:
        return False
    return proof_checks.get("postgresRuntimeProofCiLane") == (
        "PR Merge Gate / PostgreSQL Runtime Proof"
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith("make ") or ref.startswith("PR Merge Gate /"):
            continue
        if not (repository_root / ref).is_file():
            return False
    return True


def _required_make_target_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    makefile_path = repository_root / "Makefile"
    try:
        makefile_text = makefile_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        target = f"{ref.removeprefix('make ')}:"
        if target not in makefile_text:
            return False
    return True
