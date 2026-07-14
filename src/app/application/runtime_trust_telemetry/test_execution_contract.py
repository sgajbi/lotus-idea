from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_trust_telemetry import build_runtime_trust_telemetry_preview
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
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
from app.domain.proof_evidence import EvidenceClass

RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV = (
    "LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION"
)
RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.runtime-trust-telemetry-test-execution.v2"
)
RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_BLOCKERS_SATISFIED: tuple[str, ...] = ()

REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS = (
    "runtime_candidate_snapshot_missing",
    "runtime_trust_telemetry_product_coverage_incomplete",
    "certified_runtime_trust_telemetry_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "platform_source_manifest_inclusion_missing",
    "platform_mesh_certification_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS = (
    "src/app/application/runtime_trust_telemetry/telemetry.py",
    "src/app/application/runtime_trust_telemetry/test_execution_contract.py",
    "scripts/runtime_trust_telemetry/generate_preview.py",
    "scripts/runtime_trust_telemetry/generate_snapshot.py",
    "scripts/runtime_trust_telemetry/test_execution_contract_gate.py",
    "tests/unit/runtime_trust_telemetry/test_telemetry.py",
    "tests/integration/test_runtime_trust_telemetry_api.py",
    "make runtime-trust-telemetry-preview-check",
    "make runtime-trust-telemetry-snapshot-check",
    "GET /api/v1/data-mesh/trust-telemetry/runtime-preview",
    "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot",
)

_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "testExecutionValid",
        "aggregateBlockersSatisfied",
        "candidateSnapshotCount",
        "currentSourceRefCount",
        "staleOrUnavailableSourceRefCount",
        "inMemoryLineageMaterialized",
        "productCoverage",
        "evidenceRefs",
        "proofChecks",
        "remainingCertificationBlockers",
        "repositoryAdapter",
        "durableStorageObserved",
        "serviceRuntimeObserved",
        "apiRequestObserved",
        "authorizationObserved",
        "tenantIsolationObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)
_PROOF_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "deterministicInMemoryExerciseObserved",
        "nonDurableRepositoryPosturePreserved",
    }
)
_PRODUCT_COVERAGE_FIELDS = frozenset(
    {
        "coverageStatus",
        "productCoverageComplete",
        "declaredProductCount",
        "runtimeBackedProductCount",
        "blockedProductCount",
        "coverageBlockers",
    }
)
_AS_OF_DATE = date(2026, 6, 21)


def build_runtime_trust_telemetry_test_execution_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    preview_counts = {
        "candidateSnapshotCount": 0,
        "currentSourceRefCount": 0,
        "staleOrUnavailableSourceRefCount": 0,
        "inMemoryLineageMaterialized": False,
    }
    product_coverage = _empty_product_coverage_summary()
    deterministic_exercise_observed = False
    non_durable_posture_preserved = False
    if timezone_aware:
        preview = build_runtime_trust_telemetry_preview(
            repository=_source_safe_candidate_repository(generated_at_utc),
            durable_storage_backed=False,
            generated_at_utc=generated_at_utc,
        )
        preview_counts = {
            "candidateSnapshotCount": preview.candidate_snapshot_count,
            "currentSourceRefCount": preview.current_source_ref_count,
            "staleOrUnavailableSourceRefCount": preview.stale_or_unavailable_source_ref_count,
            "inMemoryLineageMaterialized": preview.lineage_materialized,
        }
        product_coverage = _product_coverage_summary(preview.product_postures)
        deterministic_exercise_observed = (
            preview.candidate_snapshot_count == 1
            and preview.current_source_ref_count == 4
            and preview.stale_or_unavailable_source_ref_count == 0
            and preview.lineage_materialized
        )
        non_durable_posture_preserved = (
            "durable_repository_not_configured" in preview.certification_blockers
        )

    evidence_refs = REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS
    file_evidence_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ", "GET "),
    )
    make_target_evidence_present = required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    test_execution_valid = (
        timezone_aware
        and file_evidence_present
        and make_target_evidence_present
        and deterministic_exercise_observed
        and non_durable_posture_preserved
    )
    return {
        "schemaVersion": RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "runtime_trust_telemetry_test_execution",
        "proofScope": "deterministic_in_memory_contract_exercise",
        "evidenceClass": EvidenceClass.TEST_EXECUTION.value,
        "testExecutionValid": test_execution_valid,
        "aggregateBlockersSatisfied": (
            RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_BLOCKERS_SATISFIED
        ),
        **preview_counts,
        "productCoverage": product_coverage,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "deterministicInMemoryExerciseObserved": deterministic_exercise_observed,
            "nonDurableRepositoryPosturePreserved": non_durable_posture_preserved,
        },
        "remainingCertificationBlockers": REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS,
        "repositoryAdapter": "in_memory",
        "durableStorageObserved": False,
        "serviceRuntimeObserved": False,
        "apiRequestObserved": False,
        "authorizationObserved": False,
        "tenantIsolationObserved": False,
        "deploymentObserved": False,
        "productionCertificationGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }


def runtime_trust_telemetry_test_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    allowed_fields = (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY})
    if set(payload) not in allowed_fields:
        return False
    if payload.get("schemaVersion") != RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "runtime_trust_telemetry_test_execution":
        return False
    if payload.get("proofScope") != "deterministic_in_memory_contract_exercise":
        return False
    if payload.get("evidenceClass") != EvidenceClass.TEST_EXECUTION.value:
        return False
    if payload.get("testExecutionValid") is not True:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersSatisfied") or ()) != ():
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS
    ):
        return False
    if payload.get("candidateSnapshotCount") != 1:
        return False
    if payload.get("currentSourceRefCount") != 4:
        return False
    if payload.get("staleOrUnavailableSourceRefCount") != 0:
        return False
    if payload.get("inMemoryLineageMaterialized") is not True:
        return False
    if not _product_coverage_is_valid(payload.get("productCoverage")):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping) or set(proof_checks) != _PROOF_CHECK_FIELDS:
        return False
    if any(proof_checks.get(field) is not True for field in _PROOF_CHECK_FIELDS):
        return False
    if payload.get("repositoryAdapter") != "in_memory":
        return False
    return all(
        payload.get(field) is False
        for field in (
            "durableStorageObserved",
            "serviceRuntimeObserved",
            "apiRequestObserved",
            "authorizationObserved",
            "tenantIsolationObserved",
            "deploymentObserved",
            "productionCertificationGranted",
            "supportedFeaturePromoted",
            "certificationClosed",
        )
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
            blocker for posture in product_postures for blocker in posture.certification_blockers
        )
    )
    return {
        "coverageStatus": "incomplete",
        "productCoverageComplete": False,
        "declaredProductCount": len(product_postures),
        "runtimeBackedProductCount": sum(1 for posture in product_postures if posture.runtime_backed),
        "blockedProductCount": sum(1 for posture in product_postures if posture.certification_blockers),
        "coverageBlockers": coverage_blockers,
    }


def _product_coverage_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _PRODUCT_COVERAGE_FIELDS:
        return False
    return (
        value.get("coverageStatus") == "incomplete"
        and value.get("productCoverageComplete") is False
        and value.get("declaredProductCount") == 9
        and value.get("runtimeBackedProductCount") == 8
        and value.get("blockedProductCount") == 9
        and tuple(value.get("coverageBlockers") or ())
        == (
            "runtime_product_materialization_missing",
            "durable_repository_not_configured",
            "platform_source_manifest_inclusion_missing",
            "platform_mesh_certification_missing",
            "gateway_workbench_discovery_proof_missing",
            "supported_feature_promotion_missing",
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
    if result.outcome is not SignalEvaluationOutcome.CANDIDATE_CREATED or result.candidate is None:
        raise ValueError("runtime trust telemetry test seed did not create a candidate")
    repository.persist_candidate(
        result.candidate,
        idempotency_key="runtime-trust-telemetry-test-execution",
        payload={"testExecution": "runtime-trust-telemetry"},
        actor_subject="test-operator",
        occurred_at_utc=generated_at_utc,
    )
    return repository


def _high_cash_input(*, generated_at_utc: datetime) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=_AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref(
            "lotus-core:PortfolioStateSnapshot:v1", generated_at_utc=generated_at_utc
        ),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1", generated_at_utc=generated_at_utc),
        cash_movement_ref=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1", generated_at_utc=generated_at_utc
        ),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1", generated_at_utc=generated_at_utc
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
        content_hash=f"sha256:runtime-trust-telemetry-test:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
