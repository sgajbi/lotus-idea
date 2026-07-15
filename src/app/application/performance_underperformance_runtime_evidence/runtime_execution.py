from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.performance_runtime_evidence import (
    build_performance_runtime_command_fingerprint,
    source_ref_matches_performance_request,
)
from app.application.source_runtime_evidence import (
    SourceRuntimeExecutionBuilder,
    build_runtime_receipts,
)
from app.application.underperformance_signal import (
    EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    UnderperformanceSignalPersistenceResult,
)
from app.domain import OpportunityFamily, SourceSystem
from app.domain.proof_evidence import EvidenceClass

PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_ENV = (
    "LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF"
)
PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.performance-underperformance.runtime-execution.v2"
)
PERFORMANCE_UNDERPERFORMANCE_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_performance_source_proof_missing",
)
PERFORMANCE_UNDERPERFORMANCE_REMAINING_BLOCKERS = (
    "opportunity_archetype_benchmark_assignment_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/performance_underperformance_runtime_evidence/runtime_execution.py",
    "src/app/application/performance_underperformance_runtime_evidence/contract.py",
    "src/app/application/underperformance_signal.py",
    "src/app/application/performance_runtime_evidence/request_identity.py",
    "src/app/application/source_runtime_evidence/receipts.py",
    "src/app/ports/performance_sources.py",
    "src/app/infrastructure/lotus_performance_sources.py",
    "scripts/performance_underperformance_runtime_evidence/generate_runtime_execution.py",
    "make performance-underperformance-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-performance:ReturnsSeriesBundle:v1"


def _payload(
    generated_at_utc: datetime,
    command: EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    status: str,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    request = command.evaluation
    return {
        "schemaVersion": PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "performance_underperformance",
        "proofType": "lotus_performance_underperformance_review_candidate_persistence",
        "sourceAuthority": SourceSystem.LOTUS_PERFORMANCE.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "asOfDate": request.as_of_date.isoformat(),
            "periodName": request.period_name,
            "requestFingerprint": build_performance_runtime_command_fingerprint(command),
            "sourceReceipt": source_receipt,
            "persistenceReceipt": persistence_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(PERFORMANCE_UNDERPERFORMANCE_RUNTIME_BLOCKERS_SATISFIED)
            if not blockers
            else []
        ),
        "remainingCertificationBlockers": list(
            PERFORMANCE_UNDERPERFORMANCE_REMAINING_BLOCKERS
        ),
        "evidenceRefs": list(PERFORMANCE_UNDERPERFORMANCE_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialPerformanceCalculationOwned": "lotus-performance",
            "benchmarkAssignmentCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
        },
    }


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


_RUNTIME_EXECUTION_BUILDER: SourceRuntimeExecutionBuilder[
    EvaluateAndPersistUnderperformanceFromPerformanceCommand,
    UnderperformanceSignalPersistenceResult,
] = SourceRuntimeExecutionBuilder(
    build_receipts=lambda command, result: build_runtime_receipts(
        candidate=result.evaluation.candidate,
        persistence=result.persistence,
        expected_family=OpportunityFamily.UNDERPERFORMANCE,
        expected_portfolio_id=command.evaluation.portfolio_id,
        request_fingerprint=build_performance_runtime_command_fingerprint(command),
        source_ref_is_authoritative=lambda source_ref: source_ref_matches_performance_request(
            source_ref,
            product_id=_PRODUCT_ID,
            as_of_date=command.evaluation.as_of_date,
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
        ),
    ),
    build_payload=_payload,
    read_diagnostics=lambda result: result.source_diagnostic_codes,
    blocking_diagnostic_codes=frozenset(
        {"performance_source_unavailable", "performance_source_entitlement_denied"}
    ),
    source_execution_blocker="performance_source_execution_blocked",
    default_source_error="performance_source_unavailable",
)
build_performance_underperformance_runtime_execution = (
    _RUNTIME_EXECUTION_BUILDER.build_completed
)
build_blocked_performance_underperformance_runtime_execution = (
    _RUNTIME_EXECUTION_BUILDER.build_blocked
)
