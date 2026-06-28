from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness, SignalEvaluationOutcome


MISSING_BENCHMARK_LIVE_PROOF_ENV = "LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF"
MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.missing-benchmark.live-proof.v1"

MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_missing_benchmark_live_core_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_performance_benchmark_readiness_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MISSING_BENCHMARK_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_missing_benchmark_live_proof.py",
    "src/app/domain/missing_benchmark_signal.py",
    "src/app/application/missing_benchmark_signal.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_benchmark_assignment_change",
    "no_benchmark_methodology_certification",
    "no_benchmark_composition_or_return_calculation",
    "no_performance_benchmark_readiness_source_ref",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_missing_benchmark_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evaluation_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(evaluation_summary)
    evaluation_outcome = _text(evaluation_summary.get("evaluationOutcome"), "")
    proof_blockers = _proof_blockers(
        evaluation_summary=evaluation_summary,
        evaluation_outcome=evaluation_outcome,
        live_core_source_attempted=live_core_source_attempted,
    )
    return {
        "schemaVersion": MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "missing-benchmark-review",
        "sourceAuthority": _text(evaluation_summary.get("sourceAuthority"), "lotus-core"),
        "sourceProductId": _text(
            evaluation_summary.get("sourceProductId"),
            "lotus-core:BenchmarkAssignment:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": run_status,
        "evaluationOutcome": evaluation_outcome,
        "candidateGenerated": _candidate_generated(evaluation_outcome),
        "benchmarkAssignmentRefPresent": bool(
            evaluation_summary.get("benchmarkAssignmentRefPresent")
        ),
        "benchmarkIdentityResolved": bool(evaluation_summary.get("benchmarkIdentityResolved")),
        "assignmentEffectiveForAsOfDate": bool(
            evaluation_summary.get("assignmentEffectiveForAsOfDate")
        ),
        "assignmentStatus": _text(evaluation_summary.get("assignmentStatus"), "unknown"),
        "assignmentVersionPresent": bool(evaluation_summary.get("assignmentVersionPresent")),
        "sourceEvidenceCurrent": bool(evaluation_summary.get("sourceEvidenceCurrent")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("sourceDiagnosticCodes")))
        ),
        "reasonCodes": list(dict.fromkeys(_text_sequence(evaluation_summary.get("reasonCodes")))),
        "unsupportedReasons": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("unsupportedReasons")))
        ),
        "benchmarkAssignmentAuthorityGranted": False,
        "benchmarkMethodologyCertified": False,
        "performanceBenchmarkReadinessCertified": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MISSING_BENCHMARK_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def missing_benchmark_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "missing-benchmark-review"
        and payload.get("sourceAuthority") == "lotus-core"
        and payload.get("sourceProductId") == "lotus-core:BenchmarkAssignment:v1"
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("candidateGenerated") is True
        and payload.get("benchmarkAssignmentRefPresent") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("benchmarkAssignmentAuthorityGranted") is False
        and payload.get("benchmarkMethodologyCertified") is False
        and payload.get("performanceBenchmarkReadinessCertified") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and not _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evaluation_summary: Mapping[str, Any],
    evaluation_outcome: str,
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("missing_benchmark_live_core_source_proof_missing")
    if _run_status(evaluation_summary) != "completed":
        blockers.append("missing_benchmark_core_source_run_blocked")
        error_code = _text(evaluation_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evaluation_summary.get("benchmarkAssignmentRefPresent")):
        blockers.append("missing_benchmark_core_source_ref_missing")
    if not bool(evaluation_summary.get("sourceEvidenceCurrent")):
        blockers.append("missing_benchmark_core_source_evidence_not_current")
    if not _candidate_generated(evaluation_outcome):
        blockers.append("no_missing_benchmark_candidate_generated")
    return list(dict.fromkeys(blockers))


def core_source_ref_is_current(value: object) -> bool:
    return getattr(value, "freshness", None) is EvidenceFreshness.CURRENT


def _run_status(summary: Mapping[str, Any]) -> str:
    explicit_status = _text(summary.get("runStatus") or summary.get("status"), "")
    if explicit_status:
        return explicit_status
    return "completed" if summary else "unknown"


def _candidate_generated(evaluation_outcome: str) -> bool:
    return evaluation_outcome == SignalEvaluationOutcome.CANDIDATE_CREATED.value


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
