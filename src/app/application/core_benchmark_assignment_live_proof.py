from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness


CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_ENV = "LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF"
CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION = (
    "lotus-idea.core-benchmark-assignment.live-proof.v1"
)

CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_benchmark_assignment_source_ref_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_live_performance_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
)

CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_core_benchmark_assignment_live_proof.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
)

NON_PROOF_BOUNDARIES = (
    "no_performance_methodology_proof",
    "no_benchmark_assignment_change",
    "no_benchmark_composition_or_return_calculation",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_core_benchmark_assignment_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(evidence_summary)
    proof_blockers = _proof_blockers(
        evidence_summary=evidence_summary,
        live_core_source_attempted=live_core_source_attempted,
    )
    return {
        "schemaVersion": CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "core-benchmark-assignment",
        "sourceAuthority": _text(evidence_summary.get("sourceAuthority"), "lotus-core"),
        "sourceProductId": _text(
            evidence_summary.get("sourceProductId"),
            "lotus-core:BenchmarkAssignment:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": run_status,
        "benchmarkAssignmentRefPresent": bool(
            evidence_summary.get("benchmarkAssignmentRefPresent")
        ),
        "benchmarkIdentityResolved": bool(evidence_summary.get("benchmarkIdentityResolved")),
        "assignmentEffectiveForAsOfDate": bool(
            evidence_summary.get("assignmentEffectiveForAsOfDate")
        ),
        "assignmentStatus": _text(evidence_summary.get("assignmentStatus"), "unknown"),
        "assignmentVersionPresent": bool(evidence_summary.get("assignmentVersionPresent")),
        "sourceEvidenceCurrent": bool(evidence_summary.get("sourceEvidenceCurrent")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evidence_summary.get("sourceDiagnosticCodes")))
        ),
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def core_benchmark_assignment_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "core-benchmark-assignment"
        and payload.get("sourceAuthority") == "lotus-core"
        and payload.get("sourceProductId") == "lotus-core:BenchmarkAssignment:v1"
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("benchmarkAssignmentRefPresent") is True
        and payload.get("benchmarkIdentityResolved") is True
        and payload.get("assignmentEffectiveForAsOfDate") is True
        and payload.get("assignmentVersionPresent") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "core_benchmark_assignment_source_proof_missing"
        not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("core_benchmark_assignment_source_proof_missing")
    if _run_status(evidence_summary) != "completed":
        blockers.append("core_benchmark_assignment_source_run_blocked")
        error_code = _text(evidence_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evidence_summary.get("benchmarkAssignmentRefPresent")):
        blockers.append("core_benchmark_assignment_source_ref_missing")
    if not bool(evidence_summary.get("benchmarkIdentityResolved")):
        blockers.append("core_benchmark_identity_missing")
    if not bool(evidence_summary.get("assignmentEffectiveForAsOfDate")):
        blockers.append("core_benchmark_assignment_not_effective_for_as_of_date")
    if not bool(evidence_summary.get("assignmentVersionPresent")):
        blockers.append("core_benchmark_assignment_version_missing")
    if not bool(evidence_summary.get("sourceEvidenceCurrent")):
        blockers.append("core_benchmark_assignment_evidence_not_current")
    return list(dict.fromkeys(blockers))


def core_source_ref_is_current(value: object) -> bool:
    return getattr(value, "freshness", None) is EvidenceFreshness.CURRENT


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
