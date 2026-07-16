from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.application.missing_benchmark_signal import (
    DEFAULT_MISSING_BENCHMARK_POLICY,
    EvaluateMissingBenchmarkFromCoreCommand,
    MissingBenchmarkSourceEvaluation,
    evaluate_missing_benchmark_readiness_from_core,
)
from app.application.runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
    source_ref_material,
)
from app.domain import (
    MissingBenchmarkSignalPolicy,
    SignalEvaluationOutcome,
    SourceSystem,
    benchmark_assignment_diagnostic,
)
from app.domain.proof_evidence import EvidenceClass
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentSourcePort,
)

CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF"
CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.core-missing-benchmark.runtime-execution.v2"
)
CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_missing_benchmark_live_core_source_proof_missing",
)
CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS = (
    "opportunity_archetype_performance_benchmark_readiness_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
CORE_MISSING_BENCHMARK_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/core_missing_benchmark_runtime_evidence/runtime_execution.py",
    "src/app/application/core_missing_benchmark_runtime_evidence/contract.py",
    "src/app/application/missing_benchmark_signal.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/core_missing_benchmark_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make missing-benchmark-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-core:BenchmarkAssignment:v1"
_ROUTE = "/integration/portfolios/{portfolio_id}/benchmark-assignment"


@dataclass(frozen=True)
class EvaluateCoreMissingBenchmark:
    tenant_id: str
    book_id: str
    portfolio_id: str
    client_id: str
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        required = {
            "tenant_id": self.tenant_id,
            "book_id": self.book_id,
            "portfolio_id": self.portfolio_id,
            "client_id": self.client_id,
            "evaluation_id": self.evaluation_id,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
        }
        for name, value in required.items():
            if value is None or not value.strip():
                raise ValueError(f"{name} is required")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        if self.reporting_currency is not None and (
            len(self.reporting_currency.strip()) != 3
            or not self.reporting_currency.strip().isalpha()
        ):
            raise ValueError("reporting_currency must be a three-letter currency code")


@dataclass(frozen=True)
class CoreMissingBenchmarkResult:
    command: EvaluateCoreMissingBenchmark
    source_evaluation: MissingBenchmarkSourceEvaluation
    policy: MissingBenchmarkSignalPolicy


def evaluate_core_missing_benchmark(
    command: EvaluateCoreMissingBenchmark,
    *,
    core_source: CoreBenchmarkAssignmentSourcePort,
    policy: MissingBenchmarkSignalPolicy = DEFAULT_MISSING_BENCHMARK_POLICY,
) -> CoreMissingBenchmarkResult:
    source_evaluation = evaluate_missing_benchmark_readiness_from_core(
        EvaluateMissingBenchmarkFromCoreCommand(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            reporting_currency=command.reporting_currency,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        ),
        core_source=core_source,
        policy=policy,
    )
    return CoreMissingBenchmarkResult(command, source_evaluation, policy)


def build_core_missing_benchmark_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: CoreMissingBenchmarkResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    request_receipt = _request_receipt(result)
    source_receipt = _source_receipt(result.source_evaluation.evidence)
    blockers = list(_qualification_blockers(result))
    return {
        "schemaVersion": CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "missing_benchmark",
        "proofType": "lotus_core_benchmark_assignment_gap_evaluation",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": "completed" if result.source_evaluation.evidence is not None else "blocked",
            "evaluatedAtUtc": format_utc(result.command.evaluated_at_utc),
            "requestReceipt": request_receipt,
            "sourceReceipt": source_receipt,
            "evaluationReceipt": _evaluation_receipt(
                result,
                request_receipt=request_receipt,
                source_receipt=source_receipt,
            ),
            "qualificationBlockers": blockers,
        },
        "aggregateBlockersSatisfied": (
            list(CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS),
        "evidenceRefs": list(CORE_MISSING_BENCHMARK_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "benchmarkAssignmentOwned": "lotus-core",
            "opportunityDetectionOwned": "lotus-idea",
            "benchmarkAssignmentChanged": False,
            "performanceBenchmarkReadinessCertified": False,
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


def _request_receipt(result: CoreMissingBenchmarkResult) -> dict[str, Any]:
    command = result.command
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "bookIdHash": identity_hash(command.book_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "clientIdHash": identity_hash(command.client_id),
        "evaluationIdHash": identity_hash(command.evaluation_id),
        "asOfDate": command.as_of_date.isoformat(),
        "reportingCurrency": (
            command.reporting_currency.strip().upper() if command.reporting_currency else None
        ),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": "lotus-idea",
        "correlationIdHash": identity_hash(command.correlation_id or ""),
        "traceIdHash": identity_hash(command.trace_id or ""),
        "policyVersion": result.policy.policy_version,
    }
    return {**material, "requestDigest": sha256_json(material)}


def _source_receipt(evidence: CoreBenchmarkAssignmentEvidence | None) -> dict[str, Any] | None:
    ref = evidence.benchmark_assignment_ref if evidence is not None else None
    if evidence is None or ref is None:
        return None
    material = {
        **source_ref_material(ref),
        "benchmarkIdentityResolved": evidence.benchmark_identity_resolved,
        "assignmentEffectiveForAsOfDate": evidence.assignment_effective_for_as_of_date,
        "assignmentStatus": _normalized_status(evidence.assignment_status),
        "assignmentVersionPresent": evidence.assignment_version_present,
        "assignmentDiagnostic": evidence.assignment_diagnostic,
        "entitlementAllowed": evidence.entitlement_allowed,
    }
    return {**material, "receiptDigest": sha256_json(material)}


def _evaluation_receipt(
    result: CoreMissingBenchmarkResult,
    *,
    request_receipt: dict[str, Any],
    source_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    evaluation = result.source_evaluation.evaluation
    candidate = evaluation.candidate
    signal = evaluation.signal
    material = {
        "family": evaluation.family.value,
        "outcome": evaluation.outcome.value,
        "reasonCodes": [code.value for code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "policyVersion": result.policy.policy_version,
        "candidateScore": str(result.policy.candidate_score),
        "requestReceiptDigest": request_receipt["requestDigest"],
        "assignmentStateDigest": _assignment_state_digest(source_receipt),
        "missingBenchmarkReviewRequired": (
            evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
        ),
        "candidateIdHash": identity_hash(candidate.candidate_id) if candidate else None,
        "signalIdHash": identity_hash(signal.signal_id) if signal else None,
        "evidencePacketIdHash": (
            identity_hash(candidate.evidence_packet.evidence_packet_id) if candidate else None
        ),
        "sourceRefsDigest": sha256_json([source_receipt] if source_receipt else []),
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _assignment_state_digest(source_receipt: dict[str, Any] | None) -> str:
    if source_receipt is None:
        return sha256_json(None)
    return sha256_json(
        {
            key: source_receipt[key]
            for key in (
                "benchmarkIdentityResolved",
                "assignmentEffectiveForAsOfDate",
                "assignmentStatus",
                "assignmentVersionPresent",
                "assignmentDiagnostic",
            )
        }
    )


def _qualification_blockers(result: CoreMissingBenchmarkResult) -> tuple[str, ...]:
    command = result.command
    source_evaluation = result.source_evaluation
    evidence = source_evaluation.evidence
    if evidence is None:
        return tuple(
            dict.fromkeys(
                (
                    "core_benchmark_assignment_source_execution_blocked",
                    source_evaluation.source_error_code
                    or "core_benchmark_assignment_source_evidence_missing",
                )
            )
        )
    ref = evidence.benchmark_assignment_ref
    blockers: list[str] = []
    if ref is None:
        blockers.append("core_benchmark_assignment_source_ref_missing")
    else:
        if ref.source_system is not SourceSystem.LOTUS_CORE or ref.product_id != _PRODUCT_ID:
            blockers.append("core_benchmark_assignment_source_authority_mismatch")
        if ref.route != _ROUTE:
            blockers.append("core_benchmark_assignment_route_mismatch")
        if ref.as_of_date != command.as_of_date:
            blockers.append("core_benchmark_assignment_as_of_date_mismatch")
        if ref.generated_at_utc > command.evaluated_at_utc:
            blockers.append("core_benchmark_assignment_evidence_from_future")
        if ref.freshness.value != "current":
            blockers.append("core_benchmark_assignment_evidence_not_current")
        if ref.data_quality_status.strip().lower() != "complete":
            blockers.append("core_benchmark_assignment_data_quality_incomplete")
    if not evidence.entitlement_allowed:
        blockers.append("core_benchmark_assignment_entitlement_denied")
    expected_diagnostic = benchmark_assignment_diagnostic(
        benchmark_identity_resolved=evidence.benchmark_identity_resolved,
        assignment_effective_for_as_of_date=evidence.assignment_effective_for_as_of_date,
        assignment_status=evidence.assignment_status,
        assignment_version_present=evidence.assignment_version_present,
    )
    if evidence.assignment_diagnostic != expected_diagnostic:
        blockers.append("core_benchmark_assignment_diagnostic_mismatch")
    expected_outcome = (
        SignalEvaluationOutcome.NOT_ELIGIBLE
        if expected_diagnostic == "core_benchmark_assignment_ready"
        else SignalEvaluationOutcome.CANDIDATE_CREATED
    )
    if source_evaluation.evaluation.outcome is not expected_outcome:
        blockers.append("missing_benchmark_evaluation_mismatch")
    return tuple(dict.fromkeys(blockers))


def _normalized_status(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None
