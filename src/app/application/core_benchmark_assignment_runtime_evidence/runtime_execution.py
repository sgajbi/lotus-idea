from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.domain.proof_evidence import EvidenceClass
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBenchmarkAssignmentSourcePort,
)

CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_ENV = (
    "LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF"
)
CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.core-benchmark-assignment.runtime-execution.v2"
)
CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_benchmark_assignment_source_ref_missing",
)
CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS = (
    "opportunity_archetype_live_performance_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/core_benchmark_assignment_runtime_evidence/runtime_execution.py",
    "src/app/application/core_benchmark_assignment_runtime_evidence/contract.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py",
    "make core-benchmark-assignment-live-proof-contract-gate",
)
_PRODUCT_ID = "lotus-core:BenchmarkAssignment:v1"


@dataclass(frozen=True)
class EvaluateCoreBenchmarkAssignmentReadiness:
    tenant_id: str
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip() or not self.portfolio_id.strip():
            raise ValueError("tenant_id and portfolio_id are required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class CoreBenchmarkAssignmentReadinessResult:
    command: EvaluateCoreBenchmarkAssignmentReadiness
    evidence: CoreBenchmarkAssignmentEvidence


def evaluate_core_benchmark_assignment_readiness(
    command: EvaluateCoreBenchmarkAssignmentReadiness,
    *,
    core_source: CoreBenchmarkAssignmentSourcePort,
) -> CoreBenchmarkAssignmentReadinessResult:
    evidence = core_source.fetch_benchmark_assignment_evidence(
        CoreBenchmarkAssignmentEvidenceRequest(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            reporting_currency=command.reporting_currency,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    )
    return CoreBenchmarkAssignmentReadinessResult(command=command, evidence=evidence)


def build_core_benchmark_assignment_runtime_execution(
    *, generated_at_utc: datetime, result: CoreBenchmarkAssignmentReadinessResult
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    command, evidence = result.command, result.evidence
    request_receipt = _request_receipt(command)
    source_receipt = _source_receipt(evidence.benchmark_assignment_ref)
    blockers = _qualification_blockers(command, evidence)
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="completed",
        request_receipt=request_receipt,
        source_receipt=source_receipt,
        assignment_status=evidence.assignment_status or "unknown",
        diagnostic_code=evidence.assignment_diagnostic or "core_benchmark_assignment_unknown",
        qualification_blockers=blockers,
    )


def build_blocked_core_benchmark_assignment_runtime_execution(
    *, generated_at_utc: datetime, command: EvaluateCoreBenchmarkAssignmentReadiness, error_code: str
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        request_receipt=_request_receipt(command),
        source_receipt=None,
        assignment_status="unknown",
        diagnostic_code=error_code,
        qualification_blockers=("core_benchmark_assignment_source_execution_blocked", error_code),
    )


def _payload(*, generated_at_utc: datetime, command: EvaluateCoreBenchmarkAssignmentReadiness,
             status: str, request_receipt: dict[str, Any], source_receipt: dict[str, Any] | None,
             assignment_status: str, diagnostic_code: str,
             qualification_blockers: tuple[str, ...]) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "core_benchmark_assignment",
        "proofType": "lotus_core_effective_dated_benchmark_assignment_read",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "evaluatedAtUtc": _format_utc(command.evaluated_at_utc),
            "requestReceipt": request_receipt,
            "sourceReceipt": source_receipt,
            "assignmentStatus": assignment_status,
            "diagnosticCode": diagnostic_code,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS),
        "evidenceRefs": list(CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "benchmarkAssignmentOwned": "lotus-core",
            "benchmarkAssignmentChanged": False,
            "performanceMethodologyCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _qualification_blockers(
    command: EvaluateCoreBenchmarkAssignmentReadiness,
    evidence: CoreBenchmarkAssignmentEvidence,
) -> tuple[str, ...]:
    ref = evidence.benchmark_assignment_ref
    blockers: list[str] = []
    if ref is None or ref.source_system is not SourceSystem.LOTUS_CORE or ref.product_id != _PRODUCT_ID:
        blockers.append("core_benchmark_assignment_source_ref_missing")
    elif ref.as_of_date != command.as_of_date:
        blockers.append("core_benchmark_assignment_scope_mismatch")
    elif ref.generated_at_utc > command.evaluated_at_utc:
        blockers.append("core_benchmark_assignment_source_time_invalid")
    elif ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append("core_benchmark_assignment_evidence_not_current")
    if not evidence.entitlement_allowed:
        blockers.append("core_benchmark_assignment_entitlement_denied")
    if not evidence.benchmark_identity_resolved:
        blockers.append("core_benchmark_identity_missing")
    if not evidence.assignment_effective_for_as_of_date:
        blockers.append("core_benchmark_assignment_not_effective_for_as_of_date")
    if not evidence.assignment_version_present:
        blockers.append("core_benchmark_assignment_version_missing")
    if (evidence.assignment_status or "").lower() != "active":
        blockers.append("core_benchmark_assignment_not_active")
    return tuple(dict.fromkeys(blockers))


def _request_receipt(command: EvaluateCoreBenchmarkAssignmentReadiness) -> dict[str, Any]:
    material = {
        "tenantIdHash": _identity_hash(command.tenant_id),
        "portfolioIdHash": _identity_hash(command.portfolio_id),
        "asOfDate": command.as_of_date.isoformat(),
        "reportingCurrency": command.reporting_currency,
        "evaluatedAtUtc": _format_utc(command.evaluated_at_utc),
    }
    return {**material, "requestDigest": _sha256_json(material)}


def _source_receipt(ref: SourceRef | None) -> dict[str, Any] | None:
    if ref is None:
        return None
    material = {
        "productId": ref.product_id,
        "sourceSystem": ref.source_system.value,
        "productVersion": ref.product_version,
        "route": ref.route,
        "asOfDate": ref.as_of_date.isoformat(),
        "generatedAtUtc": _format_utc(ref.generated_at_utc),
        "contentHash": ref.content_hash,
        "dataQualityStatus": ref.data_quality_status,
        "freshness": ref.freshness.value,
    }
    return {**material, "receiptDigest": _sha256_json(material)}


def _identity_hash(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.strip().encode('utf-8')).hexdigest()}"


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
