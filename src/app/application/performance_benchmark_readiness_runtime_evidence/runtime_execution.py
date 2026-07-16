from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.application.performance_benchmark_readiness import (
    PerformanceBenchmarkReadinessResult,
)
from app.application.runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
    source_ref_material,
)
from app.domain import (
    PerformanceBenchmarkReadinessOutcome,
    SourceSystem,
    assess_performance_benchmark_readiness,
)
from app.domain.proof_evidence import EvidenceClass
from app.ports.performance_sources import PerformanceBenchmarkReadinessEvidence

PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_ENV = (
    "LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF"
)
PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.performance-benchmark-readiness.runtime-execution.v2"
)
PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_performance_benchmark_readiness_source_ref_missing",
)
PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS = (
    "opportunity_archetype_missing_benchmark_live_core_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/performance_benchmark_readiness.py",
    "src/app/application/performance_benchmark_readiness_runtime_evidence/runtime_execution.py",
    "src/app/application/performance_benchmark_readiness_runtime_evidence/contract.py",
    "src/app/domain/performance_benchmark_readiness.py",
    "src/app/ports/performance_sources.py",
    "src/app/infrastructure/lotus_performance_sources.py",
    "scripts/performance_benchmark_readiness_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make missing-benchmark-performance-readiness-proof-contract-gate",
)

_PRODUCT_ID = "lotus-performance:ReturnsSeriesBundle:v1"
_ROUTE = "/integration/returns/series"
_QUALIFYING_DATA_QUALITY = frozenset({"ready", "partial"})


def build_performance_benchmark_readiness_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: PerformanceBenchmarkReadinessResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    request_receipt = _request_receipt(result)
    source_receipt = _source_receipt(result.evidence)
    evaluation_receipt = _evaluation_receipt(
        result,
        request_receipt=request_receipt,
        source_receipt=source_receipt,
    )
    blockers = list(_qualification_blockers(result))
    return {
        "schemaVersion": PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "missing_benchmark_performance_readiness",
        "proofType": "lotus_performance_benchmark_readiness_evaluation",
        "sourceAuthority": SourceSystem.LOTUS_PERFORMANCE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": "completed" if result.evidence is not None else "blocked",
            "evaluatedAtUtc": format_utc(result.command.evaluated_at_utc),
            "requestReceipt": request_receipt,
            "sourceReceipt": source_receipt,
            "evaluationReceipt": evaluation_receipt,
            "qualificationBlockers": blockers,
        },
        "aggregateBlockersSatisfied": (
            list(PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS),
        "evidenceRefs": list(PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialPerformanceOwned": "lotus-performance",
            "benchmarkAssignmentOwned": "lotus-core",
            "opportunityReadinessOwned": "lotus-idea",
            "benchmarkAssignmentChanged": False,
            "officialPerformanceCalculated": False,
            "benchmarkMethodologyCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _request_receipt(result: PerformanceBenchmarkReadinessResult) -> dict[str, Any]:
    command = result.command
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "bookIdHash": identity_hash(command.book_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "clientIdHash": identity_hash(command.client_id),
        "evaluationIdHash": identity_hash(command.evaluation_id),
        "asOfDate": command.as_of_date.isoformat(),
        "periodName": command.period_name.strip(),
        "reportingCurrency": (
            command.reporting_currency.strip().upper() if command.reporting_currency else None
        ),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": "lotus-idea",
        "correlationIdHash": identity_hash(command.correlation_id or ""),
        "traceIdHash": identity_hash(command.trace_id or ""),
        "policyVersion": result.policy_version,
    }
    return {**material, "requestDigest": sha256_json(material)}


def _source_receipt(
    evidence: PerformanceBenchmarkReadinessEvidence | None,
) -> dict[str, Any] | None:
    ref = evidence.performance_ref if evidence is not None else None
    if evidence is None or ref is None:
        return None
    material = {
        **source_ref_material(ref),
        "calculationIdHash": identity_hash(evidence.calculation_id),
        "portfolioIdHash": identity_hash(evidence.response_portfolio_id),
        "inputFingerprint": evidence.input_fingerprint,
        "calculationHash": evidence.calculation_hash,
        "benchmarkContextAvailable": evidence.benchmark_context_available,
        "benchmarkIdHash": (
            identity_hash(evidence.benchmark_id) if evidence.benchmark_id is not None else None
        ),
        "benchmarkReturnSource": evidence.benchmark_return_source,
        "requestedPointCount": evidence.requested_point_count,
        "returnedPointCount": evidence.returned_point_count,
        "missingPointCount": evidence.missing_point_count,
        "coverageRatio": str(evidence.coverage_ratio),
        "producerCorrelationIdHash": (
            identity_hash(evidence.producer_correlation_id)
            if evidence.producer_correlation_id is not None
            else None
        ),
        "producerTraceIdHash": (
            identity_hash(evidence.producer_trace_id)
            if evidence.producer_trace_id is not None
            else None
        ),
        "readinessDiagnostic": evidence.readiness_diagnostic,
        "entitlementAllowed": evidence.entitlement_allowed,
    }
    return {**material, "receiptDigest": sha256_json(material)}


def _evaluation_receipt(
    result: PerformanceBenchmarkReadinessResult,
    *,
    request_receipt: dict[str, Any],
    source_receipt: dict[str, Any] | None,
) -> dict[str, Any] | None:
    assessment = result.assessment
    if assessment is None:
        return None
    material = {
        "family": "missing_benchmark",
        "outcome": assessment.outcome.value,
        "readinessDiagnostic": assessment.diagnostic,
        "benchmarkReviewRequired": assessment.benchmark_review_required,
        "policyVersion": result.policy_version,
        "requestReceiptDigest": request_receipt["requestDigest"],
        "sourceReceiptDigest": (
            source_receipt["receiptDigest"] if source_receipt is not None else sha256_json(None)
        ),
        "benchmarkContextDigest": _benchmark_context_digest(source_receipt),
        "sourceRefCount": 1 if source_receipt is not None else 0,
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _benchmark_context_digest(source_receipt: dict[str, Any] | None) -> str:
    if source_receipt is None:
        return sha256_json(None)
    return sha256_json(
        {
            key: source_receipt[key]
            for key in (
                "benchmarkContextAvailable",
                "benchmarkIdHash",
                "benchmarkReturnSource",
                "readinessDiagnostic",
            )
        }
    )


def _qualification_blockers(
    result: PerformanceBenchmarkReadinessResult,
) -> tuple[str, ...]:
    command = result.command
    evidence = result.evidence
    if evidence is None:
        return tuple(
            dict.fromkeys(
                (
                    "performance_benchmark_readiness_source_execution_blocked",
                    result.source_error_code or "performance_benchmark_readiness_source_missing",
                )
            )
        )
    ref = evidence.performance_ref
    blockers: list[str] = []
    if ref is None:
        blockers.append("performance_benchmark_readiness_source_ref_missing")
    else:
        if ref.product_id != _PRODUCT_ID or ref.source_system is not SourceSystem.LOTUS_PERFORMANCE:
            blockers.append("performance_benchmark_readiness_source_authority_mismatch")
        if ref.route != _ROUTE:
            blockers.append("performance_benchmark_readiness_route_mismatch")
        if ref.as_of_date != command.as_of_date:
            blockers.append("performance_benchmark_readiness_as_of_date_mismatch")
        if ref.generated_at_utc > command.evaluated_at_utc:
            blockers.append("performance_benchmark_readiness_evidence_from_future")
        if ref.freshness.value != "current":
            blockers.append("performance_benchmark_readiness_evidence_not_current")
        if ref.data_quality_status.strip().lower() not in _QUALIFYING_DATA_QUALITY:
            blockers.append("performance_benchmark_readiness_data_quality_unsupported")
        if ref.content_hash != evidence.calculation_hash:
            blockers.append("performance_benchmark_readiness_content_hash_mismatch")
    if not evidence.entitlement_allowed:
        blockers.append("performance_benchmark_readiness_entitlement_denied")
    if evidence.response_portfolio_id != command.portfolio_id:
        blockers.append("performance_benchmark_readiness_portfolio_scope_mismatch")
    if evidence.producer_correlation_id != command.correlation_id:
        blockers.append("performance_benchmark_readiness_correlation_mismatch")
    if evidence.producer_trace_id != command.trace_id:
        blockers.append("performance_benchmark_readiness_trace_mismatch")
    if not _coverage_is_valid(evidence):
        blockers.append("performance_benchmark_readiness_coverage_invalid")
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=evidence.benchmark_context_available,
        benchmark_id=evidence.benchmark_id,
        benchmark_return_source=evidence.benchmark_return_source,
    )
    if evidence.readiness_diagnostic != assessment.diagnostic:
        blockers.append("performance_benchmark_readiness_diagnostic_mismatch")
    if assessment.outcome not in {
        PerformanceBenchmarkReadinessOutcome.REVIEW_REQUIRED,
        PerformanceBenchmarkReadinessOutcome.NO_OPPORTUNITY,
    }:
        blockers.append("performance_benchmark_readiness_evaluation_blocked")
    if result.assessment != assessment:
        blockers.append("performance_benchmark_readiness_evaluation_mismatch")
    return tuple(dict.fromkeys(blockers))


def _coverage_is_valid(evidence: PerformanceBenchmarkReadinessEvidence) -> bool:
    requested = evidence.requested_point_count
    returned = evidence.returned_point_count
    missing = evidence.missing_point_count
    if requested <= 0 or returned < 0 or missing < 0 or returned + missing != requested:
        return False
    return evidence.coverage_ratio == Decimal(returned) / Decimal(requested)
