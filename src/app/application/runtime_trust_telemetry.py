from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Mapping

from app.domain import CandidatePersistenceRecord, EvidenceFreshness
from app.ports.idea_repository import CandidateSnapshotRepository


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


def _record_lineage_materialized(record: CandidatePersistenceRecord) -> bool:
    packet = record.candidate.evidence_packet
    return bool(packet.lineage_ref.lineage_id and packet.lineage_ref.source_refs)


def _mapping_proxy(counter: Mapping[str, int]) -> MappingProxyType[str, int]:
    return MappingProxyType(dict(sorted(counter.items())))


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
