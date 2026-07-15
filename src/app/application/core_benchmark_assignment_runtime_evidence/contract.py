from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from app.application.core_benchmark_assignment_runtime_evidence.runtime_execution import (
    CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION,
    _sha256_json,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain import EvidenceFreshness, SourceSystem
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear, parse_timezone_aware_datetime

_TOP_KEYS = frozenset({"schemaVersion", "repository", "evidenceClass", "proofFamily", "proofType", "sourceAuthority", "generatedAtUtc", "execution", "aggregateBlockersSatisfied", "remainingCertificationBlockers", "evidenceRefs", "nonProofClaims"})
_EXECUTION_KEYS = frozenset({"status", "evaluatedAtUtc", "requestReceipt", "sourceReceipt", "assignmentStatus", "diagnosticCode", "qualificationBlockers"})
_REQUEST_KEYS = frozenset({"tenantIdHash", "portfolioIdHash", "asOfDate", "reportingCurrency", "evaluatedAtUtc", "requestDigest"})
_SOURCE_KEYS = frozenset({"productId", "sourceSystem", "productVersion", "route", "asOfDate", "generatedAtUtc", "contentHash", "dataQualityStatus", "freshness", "receiptDigest"})
_CLAIM_KEYS = frozenset({"benchmarkAssignmentOwned", "benchmarkAssignmentChanged", "performanceMethodologyCertified", "dataMeshRuntimeCertified", "gatewayWorkbenchRuntimeObserved", "clientPublicationApproved", "deploymentCertified", "productionCertified", "supportedFeaturePromoted", "ideaPersistenceRequired"})


def core_benchmark_assignment_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (payload.get("schemaVersion") != CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION
            or payload.get("repository") != "lotus-idea"
            or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
            or payload.get("proofFamily") != "core_benchmark_assignment"
            or payload.get("proofType") != "lotus_core_effective_dated_benchmark_assignment_read"
            or payload.get("sourceAuthority") != SourceSystem.LOTUS_CORE.value):
        return False
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if generated is None or not isinstance(execution, Mapping) or set(execution) != _EXECUTION_KEYS:
        return False
    if not isinstance(claims, Mapping) or set(claims) != _CLAIM_KEYS:
        return False
    if claims.get("benchmarkAssignmentOwned") != "lotus-core" or any(v is not False for k, v in claims.items() if k != "benchmarkAssignmentOwned"):
        return False
    request = execution.get("requestReceipt")
    source = execution.get("sourceReceipt")
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if not isinstance(request, Mapping) or set(request) != _REQUEST_KEYS or not isinstance(source, Mapping) or set(source) != _SOURCE_KEYS or evaluated is None:
        return False
    request_material = {k: request[k] for k in _REQUEST_KEYS if k != "requestDigest"}
    source_material = {k: source[k] for k in _SOURCE_KEYS if k != "receiptDigest"}
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except ValueError:
        return False
    if (request.get("requestDigest") != _sha256_json(request_material)
            or source.get("receiptDigest") != _sha256_json(source_material)
            or request.get("evaluatedAtUtc") != execution.get("evaluatedAtUtc")
            or request.get("asOfDate") != source.get("asOfDate")
            or source.get("productId") != "lotus-core:BenchmarkAssignment:v1"
            or source.get("sourceSystem") != SourceSystem.LOTUS_CORE.value
            or source.get("freshness") != EvidenceFreshness.CURRENT.value
            or source_generated is None or source_generated > evaluated or generated < evaluated
            or execution.get("status") != "completed"
            or execution.get("assignmentStatus") != "active"
            or tuple(execution.get("qualificationBlockers") or ())):
        return False
    if tuple(payload.get("aggregateBlockersSatisfied") or ()) != CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS or tuple(payload.get("evidenceRefs") or ()) != CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS:
        return False
    return evidence_class_can_clear(actual=EvidenceClass.RUNTIME_EXECUTION, required=EvidenceClass.RUNTIME_EXECUTION)
