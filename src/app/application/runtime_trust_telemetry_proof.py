from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.application.runtime_trust_telemetry import build_runtime_trust_telemetry_preview
from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    evaluate_high_cash_signal,
)

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text

RUNTIME_TRUST_TELEMETRY_PROOF_ENV = "LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_PROOF"
RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION = "lotus-idea.runtime-trust-telemetry-proof.v1"

RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED = ("runtime_candidate_snapshot_missing",)

PRODUCT_COVERAGE_CERTIFICATION_BLOCKERS = (
    "runtime_product_materialization_missing",
    "runtime_product_records_missing",
    "stale_or_unavailable_source_refs_present",
    "durable_repository_not_configured",
)

REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS = (
    "src/app/application/runtime_trust_telemetry.py",
    "scripts/generate_runtime_trust_telemetry_preview.py",
    "scripts/generate_runtime_trust_telemetry_snapshot.py",
    "tests/unit/test_runtime_trust_telemetry.py",
    "tests/integration/test_runtime_trust_telemetry_api.py",
    "make runtime-trust-telemetry-preview-check",
    "make runtime-trust-telemetry-snapshot-check",
    "GET /api/v1/data-mesh/trust-telemetry/runtime-preview",
    "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot",
)

REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS = (
    "runtime_trust_telemetry_product_coverage_incomplete",
    "certified_runtime_trust_telemetry_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "platform_source_manifest_inclusion_missing",
    "platform_mesh_certification_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)

_AS_OF_DATE = date(2026, 6, 21)


def build_runtime_trust_telemetry_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    preview_counts = {
        "candidateSnapshotCount": 0,
        "currentSourceRefCount": 0,
        "staleOrUnavailableSourceRefCount": 0,
        "lineageMaterialized": False,
    }
    product_coverage = _empty_product_coverage_summary()
    telemetry_contract_exercised = False
    if timezone_aware_generated_at_utc:
        repository = _source_safe_candidate_repository(generated_at_utc)
        preview = build_runtime_trust_telemetry_preview(
            repository=repository,
            durable_storage_backed=True,
            generated_at_utc=generated_at_utc,
        )
        preview_counts = {
            "candidateSnapshotCount": preview.candidate_snapshot_count,
            "currentSourceRefCount": preview.current_source_ref_count,
            "staleOrUnavailableSourceRefCount": (preview.stale_or_unavailable_source_ref_count),
            "lineageMaterialized": preview.lineage_materialized,
        }
        product_coverage = _product_coverage_summary(preview.product_postures)
        telemetry_contract_exercised = (
            preview.candidate_snapshot_count == 1
            and preview.current_source_ref_count == 4
            and preview.stale_or_unavailable_source_ref_count == 0
            and preview.lineage_materialized
            and "runtime_candidate_snapshot_missing" not in preview.certification_blockers
        )
    evidence_refs = tuple(REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and telemetry_contract_exercised
    )
    return {
        "schemaVersion": RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "runtime_trust_telemetry_certification",
        "proofScope": "source_safe_seeded_runtime_snapshot_certification",
        "runtimeTrustTelemetryProofValid": proof_valid,
        "aggregateBlockersCleared": RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED,
        **preview_counts,
        "productCoverage": product_coverage,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "telemetryContractExercised": telemetry_contract_exercised,
        },
        "remainingCertificationBlockers": (
            REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS
        ),
        "platformCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def runtime_trust_telemetry_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "runtime_trust_telemetry_certification":
        return False
    if payload.get("proofScope") != "source_safe_seeded_runtime_snapshot_certification":
        return False
    if payload.get("runtimeTrustTelemetryProofValid") is not True:
        return False
    if payload.get("platformCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if (
        tuple(payload.get("aggregateBlockersCleared") or ())
        != RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED
    ):
        return False
    if payload.get("candidateSnapshotCount") != 1:
        return False
    if payload.get("currentSourceRefCount") != 4:
        return False
    if payload.get("staleOrUnavailableSourceRefCount") != 0:
        return False
    if payload.get("lineageMaterialized") is not True:
        return False
    if not _product_coverage_is_valid(payload.get("productCoverage")):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("telemetryContractExercised") is True
    )


def _empty_product_coverage_summary() -> dict[str, Any]:
    return {
        "coverageStatus": "unknown",
        "productCoverageComplete": False,
        "declaredProductCount": 0,
        "runtimeBackedProductCount": 0,
        "blockedProductCount": 0,
        "coverageBlockers": (),
    }


def _product_coverage_summary(product_postures: tuple[Any, ...]) -> dict[str, Any]:
    coverage_blockers = tuple(
        dict.fromkeys(
            blocker
            for posture in product_postures
            for blocker in posture.certification_blockers
            if blocker in PRODUCT_COVERAGE_CERTIFICATION_BLOCKERS
        )
    )
    blocked_product_count = sum(
        1
        for posture in product_postures
        if posture.coverage_status != "runtime_backed"
        or bool(set(posture.certification_blockers).intersection(coverage_blockers))
    )
    runtime_backed_count = sum(1 for posture in product_postures if posture.runtime_backed)
    product_coverage_complete = bool(product_postures) and not coverage_blockers
    return {
        "coverageStatus": "complete" if product_coverage_complete else "incomplete",
        "productCoverageComplete": product_coverage_complete,
        "declaredProductCount": len(product_postures),
        "runtimeBackedProductCount": runtime_backed_count,
        "blockedProductCount": blocked_product_count,
        "coverageBlockers": coverage_blockers,
    }


def _product_coverage_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("coverageStatus") == "incomplete"
        and value.get("productCoverageComplete") is False
        and value.get("declaredProductCount") == 9
        and value.get("runtimeBackedProductCount") == 8
        and value.get("blockedProductCount") == 5
        and tuple(value.get("coverageBlockers") or ())
        == (
            "runtime_product_materialization_missing",
            "runtime_product_records_missing",
        )
    )


def _source_safe_candidate_repository(generated_at_utc: datetime) -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    result = evaluate_high_cash_signal(
        _high_cash_input(generated_at_utc=generated_at_utc),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    if result.outcome is not SignalEvaluationOutcome.CANDIDATE_CREATED:
        raise ValueError("runtime trust telemetry proof seed did not create a candidate")
    if result.candidate is None:
        raise ValueError("runtime trust telemetry proof seed returned no candidate")
    repository.persist_candidate(
        result.candidate,
        idempotency_key="runtime-trust-telemetry-proof",
        payload={"proof": "runtime-trust-telemetry"},
        actor_subject="platform-operator",
        occurred_at_utc=generated_at_utc,
    )
    return repository


def _high_cash_input(*, generated_at_utc: datetime) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=_AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref(
            "lotus-core:PortfolioStateSnapshot:v1",
            generated_at_utc=generated_at_utc,
        ),
        holdings_ref=_source_ref(
            "lotus-core:HoldingsAsOf:v1",
            generated_at_utc=generated_at_utc,
        ),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            generated_at_utc=generated_at_utc,
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            generated_at_utc=generated_at_utc,
        ),
        evaluated_at_utc=generated_at_utc,
    )


def _source_ref(product_id: str, *, generated_at_utc: datetime) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="lotus-core://source-ref/redacted",
        as_of_date=_AS_OF_DATE,
        generated_at_utc=generated_at_utc,
        content_hash=f"sha256:runtime-trust-telemetry-proof:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("make ", "GET ")):
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
