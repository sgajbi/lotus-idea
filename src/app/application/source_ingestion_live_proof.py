from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.source-ingestion.live-proof.v1"

HIGH_CASH_LIVE_CORE_BLOCKERS_CLEARED = ("opportunity_archetype_live_core_source_proof_missing",)

REMAINING_CERTIFICATION_BLOCKERS = (
    "scheduled_worker_deploy_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
)

LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_source_ingestion_live_proof.py",
    "scripts/run_source_ingestion_worker.py",
    "src/app/application/source_ingestion.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "docs/operations/source-ingestion-run-once.md",
)

NON_PROOF_BOUNDARIES = (
    "no_scheduled_worker_deployment_proof",
    "no_data_mesh_runtime_certification",
    "no_gateway_or_workbench_proof",
    "no_supported_feature_promotion",
)


def build_source_ingestion_live_proof_payload(
    *,
    generated_at_utc: datetime,
    worker_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(worker_summary)
    decision_counts = _decision_counts(worker_summary)
    proof_blockers = _proof_blockers(
        worker_summary=worker_summary,
        decision_counts=decision_counts,
        live_core_source_attempted=live_core_source_attempted,
    )
    return {
        "schemaVersion": LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "source-ingestion",
        "sourceAuthority": _text(worker_summary.get("sourceAuthority"), "lotus-core"),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "workerSchemaVersion": _text(worker_summary.get("schemaVersion"), ""),
        "workerMode": _text(worker_summary.get("mode"), ""),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": run_status,
        "durableStorageBacked": bool(worker_summary.get("durableStorageBacked")),
        "supportedFeaturePromoted": False,
        "proofClosed": not proof_blockers,
        "totalCount": _non_negative_int(worker_summary.get("totalCount")),
        "decisionCounts": decision_counts,
        "blockReasonCounts": _reason_counts(worker_summary.get("blockReasonCounts")),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def live_core_source_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "source-ingestion"
        and payload.get("sourceAuthority") == "lotus-core"
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("durableStorageBacked") is True
        and payload.get("supportedFeaturePromoted") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "live_core_source_proof_missing" not in _text_sequence(payload.get("proofBlockers"))
        and _has_ingestion_evidence(payload.get("decisionCounts"))
    )


def _proof_blockers(
    *,
    worker_summary: Mapping[str, Any],
    decision_counts: Mapping[str, int],
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("live_core_source_proof_missing")
    if _run_status(worker_summary) != "completed":
        blockers.append("live_core_source_run_blocked")
        error_code = _text(worker_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(worker_summary.get("durableStorageBacked")):
        blockers.append("durable_repository_not_configured")
    if not _has_ingestion_evidence(decision_counts):
        blockers.append("no_candidate_ingestion_evidence")
    blockers.extend(REMAINING_CERTIFICATION_BLOCKERS)
    return list(dict.fromkeys(blockers))


def _has_ingestion_evidence(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        _non_negative_int(value.get("accepted")) > 0 or _non_negative_int(value.get("replayed")) > 0
    )


def _decision_counts(worker_summary: Mapping[str, Any]) -> dict[str, int]:
    raw_counts = worker_summary.get("decisionCounts")
    if not isinstance(raw_counts, Mapping):
        return {}
    return {str(key): _non_negative_int(value) for key, value in raw_counts.items()}


def _reason_counts(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): _non_negative_int(count)
        for key, count in sorted(value.items(), key=lambda item: str(item[0]))
        if str(key).strip()
    }


def _run_status(worker_summary: Mapping[str, Any]) -> str:
    explicit_status = _text(worker_summary.get("status"), "")
    if explicit_status == "blocked":
        return "blocked"
    if _text(worker_summary.get("mode"), "") == "run_once":
        return "completed"
    return explicit_status or "unknown"


def _text_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
