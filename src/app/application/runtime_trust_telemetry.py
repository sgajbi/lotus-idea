from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

from app.domain import CandidatePersistenceRecord, EvidenceFreshness
from app.ports.idea_repository import CandidateSnapshotRepository


PRODUCT_ID = "lotus-idea:IdeaCandidate:v1"
PRODUCT_NAME = "IdeaCandidate"
PRODUCT_VERSION = "v1"
REPOSITORY = "lotus-idea"
RUNTIME_TELEMETRY_OUTPUT_PATH = "output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json"
DAILY_MAX_ALLOWED_AGE_SECONDS = 86_400


@dataclass(frozen=True)
class RuntimeTrustTelemetryPreview:
    repository: str
    product_id: str
    generated_at_utc: datetime
    candidate_snapshot_count: int
    current_source_ref_count: int
    stale_or_unavailable_source_ref_count: int
    source_authority_counts: MappingProxyType[str, int]
    freshness_counts: MappingProxyType[str, int]
    supportability_counts: MappingProxyType[str, int]
    lifecycle_counts: MappingProxyType[str, int]
    review_decision_count: int
    feedback_event_count: int
    conversion_intent_count: int
    conversion_outcome_count: int
    report_evidence_pack_count: int
    lineage_materialized: bool
    runtime_telemetry_backed: bool
    platform_certified: bool
    certification_status: str
    certification_ready: bool
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool


@dataclass(frozen=True)
class RuntimeTrustTelemetrySnapshot:
    payload: MappingProxyType[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def build_runtime_trust_telemetry_preview(
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    generated_at_utc: datetime | None = None,
) -> RuntimeTrustTelemetryPreview:
    observed_at = generated_at_utc or datetime.now(UTC)
    _require_aware_utc(observed_at, "generated_at_utc")
    snapshot = repository.snapshot()
    records = tuple(snapshot.candidate_records.values())
    source_refs = tuple(
        source_ref
        for record in records
        for source_ref in record.candidate.evidence_packet.source_refs
    )

    freshness_counts = Counter(source_ref.freshness.value for source_ref in source_refs)
    current_source_ref_count = freshness_counts.get(EvidenceFreshness.CURRENT.value, 0)
    stale_or_unavailable_source_ref_count = len(source_refs) - current_source_ref_count
    blockers = _certification_blockers(
        durable_storage_backed=durable_storage_backed,
        candidate_snapshot_count=len(records),
        stale_or_unavailable_source_ref_count=stale_or_unavailable_source_ref_count,
    )

    return RuntimeTrustTelemetryPreview(
        repository="lotus-idea",
        product_id="lotus-idea:IdeaCandidate:v1",
        generated_at_utc=observed_at,
        candidate_snapshot_count=len(records),
        current_source_ref_count=current_source_ref_count,
        stale_or_unavailable_source_ref_count=stale_or_unavailable_source_ref_count,
        source_authority_counts=_mapping_proxy(
            Counter(source_ref.source_system.value for source_ref in source_refs)
        ),
        freshness_counts=_mapping_proxy(freshness_counts),
        supportability_counts=_mapping_proxy(
            Counter(record.candidate.evidence_packet.supportability.value for record in records)
        ),
        lifecycle_counts=_mapping_proxy(
            Counter(record.candidate.lifecycle_status.value for record in records)
        ),
        review_decision_count=sum(len(record.review_decisions) for record in records),
        feedback_event_count=sum(len(record.feedback_events) for record in records),
        conversion_intent_count=sum(len(record.conversion_intents) for record in records),
        conversion_outcome_count=sum(len(record.conversion_outcomes) for record in records),
        report_evidence_pack_count=sum(len(record.report_evidence_packs) for record in records),
        lineage_materialized=bool(records)
        and all(_record_lineage_materialized(record) for record in records),
        runtime_telemetry_backed=True,
        platform_certified=False,
        certification_status="not_certified",
        certification_ready=False,
        certification_blockers=blockers,
        supported_feature_promoted=False,
    )


def build_runtime_trust_telemetry_snapshot(
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    generated_at_utc: datetime | None = None,
    source_artifact_uri: str = f"lotus-idea://{RUNTIME_TELEMETRY_OUTPUT_PATH}",
) -> RuntimeTrustTelemetrySnapshot:
    preview = build_runtime_trust_telemetry_preview(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        generated_at_utc=generated_at_utc,
    )
    records = tuple(repository.snapshot().candidate_records.values())
    source_refs = tuple(
        source_ref
        for record in records
        for source_ref in record.candidate.evidence_packet.source_refs
    )
    freshness = _snapshot_freshness(preview=preview, source_refs=source_refs)
    completeness_status = _completeness_status(preview)
    reconciliation_status = _reconciliation_status(preview)
    data_quality_status = _data_quality_status(source_refs)
    lineage_evidence_uris = (
        ["lotus-idea://runtime/idea-candidate/source-owned-lineage"]
        if preview.lineage_materialized
        else []
    )

    return RuntimeTrustTelemetrySnapshot(
        payload=_mapping_proxy(
            {
                "contract_id": "lotus-domain-product-trust-telemetry-snapshot",
                "contract_version": "1.0.0",
                "governed_by_rfcs": ["RFC-0087", "RFC-0091", "RFC-0002"],
                "emitted_at_utc": _format_utc(preview.generated_at_utc),
                "product_id": PRODUCT_ID,
                "producer_repository": REPOSITORY,
                "product_name": PRODUCT_NAME,
                "product_version": PRODUCT_VERSION,
                "source_repository": REPOSITORY,
                "freshness": freshness,
                "completeness_status": completeness_status,
                "reconciliation_status": reconciliation_status,
                "data_quality_status": data_quality_status,
                "lineage": {
                    "lineage_materialized": preview.lineage_materialized,
                    "evidence_access_class": "operator_only",
                    "evidence_uris": lineage_evidence_uris,
                },
                "blocking": {
                    "blocked": True,
                    "blocked_reason": _blocked_reason(preview),
                },
                "observed_trust_metadata": _observed_trust_metadata(
                    preview=preview,
                    records=records,
                    completeness_status=completeness_status,
                    reconciliation_status=reconciliation_status,
                    data_quality_status=data_quality_status,
                ),
                "evidence": {
                    "correlation_id": "lotus-idea-runtime-trust-telemetry-snapshot",
                    "validation_lanes": [
                        "feature",
                        "pr-merge",
                        "main-releasability",
                    ],
                    "source_artifact_uri": source_artifact_uri,
                },
            }
        )
    )


def _certification_blockers(
    *,
    durable_storage_backed: bool,
    candidate_snapshot_count: int,
    stale_or_unavailable_source_ref_count: int,
) -> tuple[str, ...]:
    blockers = [
        "platform_source_manifest_inclusion_missing",
        "platform_mesh_certification_missing",
        "gateway_workbench_discovery_proof_missing",
        "supported_feature_promotion_missing",
    ]
    if not durable_storage_backed:
        blockers.insert(0, "durable_repository_not_configured")
    if candidate_snapshot_count == 0:
        blockers.insert(0, "runtime_candidate_snapshot_missing")
    if stale_or_unavailable_source_ref_count > 0:
        blockers.insert(0, "stale_or_unavailable_source_refs_present")
    return tuple(blockers)


def _snapshot_freshness(
    *,
    preview: RuntimeTrustTelemetryPreview,
    source_refs: tuple[Any, ...],
) -> dict[str, Any]:
    freshness: dict[str, Any] = {
        "freshness_class": "daily",
        "freshness_state": _freshness_state(preview),
        "evaluated_at_utc": _format_utc(preview.generated_at_utc),
    }
    latest_generated_at = max(
        (source_ref.generated_at_utc for source_ref in source_refs),
        default=None,
    )
    if latest_generated_at is not None:
        age_seconds = int((preview.generated_at_utc - latest_generated_at).total_seconds())
        freshness["age_seconds"] = max(age_seconds, 0)
        freshness["max_allowed_age_seconds"] = DAILY_MAX_ALLOWED_AGE_SECONDS
    return freshness


def _freshness_state(preview: RuntimeTrustTelemetryPreview) -> str:
    if preview.candidate_snapshot_count == 0:
        return "unknown"
    if preview.stale_or_unavailable_source_ref_count > 0:
        return "stale"
    return "current"


def _completeness_status(preview: RuntimeTrustTelemetryPreview) -> str:
    if preview.candidate_snapshot_count == 0:
        return "unknown"
    if preview.stale_or_unavailable_source_ref_count > 0:
        return "stale"
    return "partial"


def _reconciliation_status(preview: RuntimeTrustTelemetryPreview) -> str:
    if preview.candidate_snapshot_count == 0:
        return "unknown"
    if preview.stale_or_unavailable_source_ref_count > 0:
        return "partial"
    return "not_applicable"


def _data_quality_status(source_refs: tuple[Any, ...]) -> str:
    if not source_refs:
        return "quality_unknown"
    if all(source_ref.data_quality_status == "complete" for source_ref in source_refs):
        return "quality_passed"
    return "quality_warning"


def _blocked_reason(preview: RuntimeTrustTelemetryPreview) -> str:
    blockers = ", ".join(preview.certification_blockers)
    if preview.candidate_snapshot_count == 0:
        return (
            "Runtime trust telemetry snapshot generated for IdeaCandidate:v1, but no "
            f"candidate runtime snapshot exists; blockers: {blockers}."
        )
    return (
        "Runtime trust telemetry snapshot generated for IdeaCandidate:v1, but platform source "
        "manifest inclusion, platform mesh certification, Gateway/Workbench discovery proof, and "
        f"supported-feature promotion remain pending; blockers: {blockers}."
    )


def _observed_trust_metadata(
    *,
    preview: RuntimeTrustTelemetryPreview,
    records: tuple[CandidatePersistenceRecord, ...],
    completeness_status: str,
    reconciliation_status: str,
    data_quality_status: str,
) -> dict[str, str]:
    if not records:
        return {}
    source_refs = tuple(
        source_ref
        for record in records
        for source_ref in record.candidate.evidence_packet.source_refs
    )
    as_of_dates = sorted({source_ref.as_of_date.isoformat() for source_ref in source_refs})
    metadata = {
        "product_name": PRODUCT_NAME,
        "product_version": PRODUCT_VERSION,
        "generated_at": _format_utc(preview.generated_at_utc),
        "reconciliation_status": reconciliation_status,
        "data_quality_status": data_quality_status,
        "lineage_bundle_id": "lotus-idea:IdeaCandidate:v1:runtime-lineage",
        "correlation_id": "lotus-idea-runtime-trust-telemetry-snapshot",
    }
    if len(as_of_dates) == 1:
        metadata["as_of_date"] = as_of_dates[0]
    if completeness_status != "unknown":
        metadata["source_batch_fingerprint"] = "source-safe-runtime-aggregate"
    return metadata


def _record_lineage_materialized(record: CandidatePersistenceRecord) -> bool:
    packet = record.candidate.evidence_packet
    return bool(packet.lineage_ref.lineage_id and packet.lineage_ref.source_refs)


def _mapping_proxy(counter: Mapping[str, Any]) -> MappingProxyType[str, Any]:
    return MappingProxyType(dict(sorted(counter.items())))


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
