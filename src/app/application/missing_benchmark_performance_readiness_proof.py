from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_ENV = (
    "LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF"
)
MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION = (
    "lotus-idea.missing-benchmark.performance-readiness-proof.v1"
)

MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED = (
    "opportunity_archetype_performance_benchmark_readiness_source_ref_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_missing_benchmark_live_core_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MISSING_BENCHMARK_PERFORMANCE_READINESS_EVIDENCE_REFS = (
    "scripts/generate_missing_benchmark_performance_readiness_proof.py",
    "src/app/application/missing_benchmark_performance_readiness_proof.py",
    "src/app/infrastructure/lotus_performance_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_benchmark_assignment_change",
    "no_benchmark_return_calculation",
    "no_benchmark_methodology_certification",
    "no_performance_calculation_authority",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_missing_benchmark_performance_readiness_proof_payload(
    *,
    generated_at_utc: datetime,
    performance_summary: Mapping[str, Any],
    live_performance_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(performance_summary)
    diagnostic = _text(performance_summary.get("benchmarkReadinessDiagnostic"), "")
    source_ref_present = bool(
        performance_summary.get("performanceBenchmarkReadinessSourceRefPresent")
    )
    readiness_evaluated = source_ref_present and bool(diagnostic)
    proof_blockers = _proof_blockers(
        performance_summary=performance_summary,
        live_performance_source_attempted=live_performance_source_attempted,
        source_ref_present=source_ref_present,
        readiness_evaluated=readiness_evaluated,
    )
    return {
        "schemaVersion": MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "missing-benchmark-performance-readiness",
        "sourceAuthority": _text(performance_summary.get("sourceAuthority"), "lotus-performance"),
        "sourceProductId": _text(
            performance_summary.get("sourceProductId"),
            "lotus-performance:ReturnsSeriesBundle:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "livePerformanceSourceAttempted": live_performance_source_attempted,
        "runStatus": run_status,
        "sourceEvidenceCurrent": bool(performance_summary.get("sourceEvidenceCurrent")),
        "performanceBenchmarkReadinessSourceRefPresent": source_ref_present,
        "benchmarkReadinessEvaluated": readiness_evaluated,
        "benchmarkContextAvailable": bool(performance_summary.get("benchmarkContextAvailable")),
        "benchmarkReadinessDiagnostic": diagnostic,
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(performance_summary.get("sourceDiagnosticCodes")))
        ),
        "benchmarkAssignmentAuthorityGranted": False,
        "benchmarkReturnCalculationAuthorityGranted": False,
        "benchmarkMethodologyCertified": False,
        "performanceCalculationAuthorityGranted": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MISSING_BENCHMARK_PERFORMANCE_READINESS_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def missing_benchmark_performance_readiness_proof_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    return (
        payload.get("schemaVersion") == MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "missing-benchmark-performance-readiness"
        and payload.get("sourceAuthority") == "lotus-performance"
        and payload.get("sourceProductId") == "lotus-performance:ReturnsSeriesBundle:v1"
        and payload.get("livePerformanceSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("performanceBenchmarkReadinessSourceRefPresent") is True
        and payload.get("benchmarkReadinessEvaluated") is True
        and payload.get("benchmarkAssignmentAuthorityGranted") is False
        and payload.get("benchmarkReturnCalculationAuthorityGranted") is False
        and payload.get("benchmarkMethodologyCertified") is False
        and payload.get("performanceCalculationAuthorityGranted") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and not _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    performance_summary: Mapping[str, Any],
    live_performance_source_attempted: bool,
    source_ref_present: bool,
    readiness_evaluated: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_performance_source_attempted:
        blockers.append("missing_benchmark_performance_readiness_source_proof_missing")
    if _run_status(performance_summary) != "completed":
        blockers.append("missing_benchmark_performance_readiness_source_run_blocked")
        error_code = _text(performance_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not source_ref_present:
        blockers.append("missing_benchmark_performance_readiness_source_ref_missing")
    if not bool(performance_summary.get("sourceEvidenceCurrent")):
        blockers.append("missing_benchmark_performance_readiness_source_evidence_not_current")
    if not readiness_evaluated:
        blockers.append("missing_benchmark_performance_readiness_not_evaluated")
    return list(dict.fromkeys(blockers))


def _run_status(summary: Mapping[str, Any]) -> str:
    explicit_status = _text(summary.get("runStatus") or summary.get("status"), "")
    if explicit_status:
        return explicit_status
    return "completed" if summary else "unknown"


def _text_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
