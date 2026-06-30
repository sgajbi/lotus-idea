from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.domain import CandidatePersistenceRecord, EvidenceFreshness
from app.ports.idea_repository import (
    CandidateSnapshotRepository,
    RuntimeTrustTelemetryProjectionRepository,
    RuntimeTrustTelemetryRepositorySummary,
)


PRODUCT_ID = "lotus-idea:IdeaCandidate:v1"
PRODUCT_NAME = "IdeaCandidate"
PRODUCT_VERSION = "v1"
REPOSITORY = "lotus-idea"
RUNTIME_TELEMETRY_OUTPUT_PATH = "output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json"
DAILY_MAX_ALLOWED_AGE_SECONDS = 86_400
PRODUCER_DECLARATION_PATH = Path("contracts/domain-data-products/lotus-idea-products.v1.json")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMMON_PRODUCT_CERTIFICATION_BLOCKERS = (
    "platform_source_manifest_inclusion_missing",
    "platform_mesh_certification_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)
PRODUCT_COVERAGE_CERTIFICATION_BLOCKERS = (
    "runtime_product_materialization_missing",
    "runtime_product_records_missing",
    "stale_or_unavailable_source_refs_present",
    "durable_repository_not_configured",
)
RUNTIME_BACKED_PRODUCT_IDS = {
    "lotus-idea:IdeaCandidate:v1",
    "lotus-idea:IdeaEvidencePacket:v1",
    "lotus-idea:AdvisorOpportunityQueue:v1",
    "lotus-idea:IdeaReviewDecision:v1",
    "lotus-idea:IdeaFeedbackEvent:v1",
    "lotus-idea:IdeaConversionIntent:v1",
    "lotus-idea:IdeaConversionOutcome:v1",
    "lotus-idea:IdeaTrustTelemetry:v1",
}


@dataclass(frozen=True)
class RuntimeTrustTelemetryProductPosture:
    product_id: str
    product_name: str
    product_version: str
    lifecycle_status: str
    freshness_class: str
    coverage_status: str
    runtime_backed: bool
    observed_record_count: int
    current_source_ref_count: int
    stale_or_unavailable_source_ref_count: int
    freshness_state: str
    completeness_status: str
    reconciliation_status: str
    data_quality_status: str
    lineage_materialized: bool
    source_batch_evidence_available: bool
    consumer_exposure_status: str
    certification_blockers: tuple[str, ...]


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
    product_postures: tuple[RuntimeTrustTelemetryProductPosture, ...]
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
    summary = _runtime_trust_telemetry_summary(repository)
    product_postures = _product_postures(
        summary=summary,
        generated_at_utc=observed_at,
        durable_storage_backed=durable_storage_backed,
    )
    blockers = _certification_blockers(
        durable_storage_backed=durable_storage_backed,
        candidate_snapshot_count=summary.candidate_snapshot_count,
        stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
        product_postures=product_postures,
    )

    return RuntimeTrustTelemetryPreview(
        repository="lotus-idea",
        product_id="lotus-idea:IdeaCandidate:v1",
        generated_at_utc=observed_at,
        candidate_snapshot_count=summary.candidate_snapshot_count,
        current_source_ref_count=summary.current_source_ref_count,
        stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
        source_authority_counts=_mapping_proxy(summary.source_authority_counts),
        freshness_counts=_mapping_proxy(summary.freshness_counts),
        supportability_counts=_mapping_proxy(summary.supportability_counts),
        lifecycle_counts=_mapping_proxy(summary.lifecycle_counts),
        review_decision_count=summary.review_decision_count,
        feedback_event_count=summary.feedback_event_count,
        conversion_intent_count=summary.conversion_intent_count,
        conversion_outcome_count=summary.conversion_outcome_count,
        report_evidence_pack_count=summary.report_evidence_pack_count,
        lineage_materialized=summary.lineage_materialized,
        runtime_telemetry_backed=True,
        platform_certified=False,
        certification_status="not_certified",
        certification_ready=False,
        certification_blockers=blockers,
        product_postures=product_postures,
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
    summary = _runtime_trust_telemetry_summary(repository)
    freshness = _snapshot_freshness(preview=preview, summary=summary)
    completeness_status = _completeness_status(preview)
    reconciliation_status = _reconciliation_status(preview)
    data_quality_status = summary.data_quality_status
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
                "product_coverage": [
                    _product_posture_payload(posture) for posture in preview.product_postures
                ],
                "observed_trust_metadata": _observed_trust_metadata(
                    preview=preview,
                    summary=summary,
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


def _product_postures(
    *,
    summary: RuntimeTrustTelemetryRepositorySummary,
    generated_at_utc: datetime,
    durable_storage_backed: bool,
) -> tuple[RuntimeTrustTelemetryProductPosture, ...]:
    declarations = _producer_product_declarations()
    observed_counts = _product_observed_counts(summary)
    return tuple(
        _product_posture(
            declaration=declaration,
            observed_record_count=observed_counts.get(declaration["product_id"], 0),
            summary=summary,
            generated_at_utc=generated_at_utc,
            durable_storage_backed=durable_storage_backed,
        )
        for declaration in declarations
    )


def _producer_product_declarations() -> tuple[dict[str, str], ...]:
    payload = json.loads((REPOSITORY_ROOT / PRODUCER_DECLARATION_PATH).read_text(encoding="utf-8"))
    products = payload.get("products")
    if not isinstance(products, list):
        raise ValueError("producer product declaration must contain products")
    declarations: list[dict[str, str]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        product_name = str(product.get("product_name", "unknown"))
        product_version = str(product.get("product_version", "unknown"))
        freshness_policy = product.get("freshness_policy")
        declarations.append(
            {
                "product_id": f"lotus-idea:{product_name}:{product_version}",
                "product_name": product_name,
                "product_version": product_version,
                "lifecycle_status": str(product.get("lifecycle_status", "unknown")),
                "freshness_class": (
                    str(freshness_policy.get("freshness_class", "unknown"))
                    if isinstance(freshness_policy, dict)
                    else "unknown"
                ),
            }
        )
    return tuple(declarations)


def _product_posture(
    *,
    declaration: Mapping[str, str],
    observed_record_count: int,
    summary: RuntimeTrustTelemetryRepositorySummary,
    generated_at_utc: datetime,
    durable_storage_backed: bool,
) -> RuntimeTrustTelemetryProductPosture:
    product_id = declaration["product_id"]
    runtime_backed = product_id in RUNTIME_BACKED_PRODUCT_IDS
    freshness_state = _product_freshness_state(
        runtime_backed=runtime_backed,
        observed_record_count=observed_record_count,
        stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
    )
    completeness_status = _product_completeness_status(
        runtime_backed=runtime_backed,
        observed_record_count=observed_record_count,
        stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
    )
    return RuntimeTrustTelemetryProductPosture(
        product_id=product_id,
        product_name=declaration["product_name"],
        product_version=declaration["product_version"],
        lifecycle_status=declaration["lifecycle_status"],
        freshness_class=declaration["freshness_class"],
        coverage_status=_product_coverage_status(
            runtime_backed=runtime_backed,
            observed_record_count=observed_record_count,
        ),
        runtime_backed=runtime_backed,
        observed_record_count=observed_record_count,
        current_source_ref_count=summary.current_source_ref_count if runtime_backed else 0,
        stale_or_unavailable_source_ref_count=(
            summary.stale_or_unavailable_source_ref_count if runtime_backed else 0
        ),
        freshness_state=freshness_state,
        completeness_status=completeness_status,
        reconciliation_status=_product_reconciliation_status(
            runtime_backed=runtime_backed,
            observed_record_count=observed_record_count,
            stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
        ),
        data_quality_status=summary.data_quality_status if runtime_backed else "quality_blocked",
        lineage_materialized=(
            _trust_telemetry_lineage_materialized(product_id, generated_at_utc)
            if product_id == "lotus-idea:IdeaTrustTelemetry:v1"
            else summary.lineage_materialized
        )
        if runtime_backed
        else False,
        source_batch_evidence_available=summary.source_batch_evidence_available
        if runtime_backed
        else False,
        consumer_exposure_status="not_exposed_platform_not_certified",
        certification_blockers=_product_certification_blockers(
            runtime_backed=runtime_backed,
            durable_storage_backed=durable_storage_backed,
            observed_record_count=observed_record_count,
            stale_or_unavailable_source_ref_count=summary.stale_or_unavailable_source_ref_count,
        ),
    )


def _product_observed_counts(
    summary: RuntimeTrustTelemetryRepositorySummary,
) -> dict[str, int]:
    return {
        "lotus-idea:IdeaCandidate:v1": summary.candidate_snapshot_count,
        "lotus-idea:IdeaEvidencePacket:v1": summary.candidate_snapshot_count,
        "lotus-idea:AdvisorOpportunityQueue:v1": summary.candidate_snapshot_count,
        "lotus-idea:IdeaReviewDecision:v1": summary.review_decision_count,
        "lotus-idea:IdeaFeedbackEvent:v1": summary.feedback_event_count,
        "lotus-idea:IdeaConversionIntent:v1": summary.conversion_intent_count,
        "lotus-idea:IdeaConversionOutcome:v1": summary.conversion_outcome_count,
        "lotus-idea:IdeaTrustTelemetry:v1": 1,
    }


def _product_coverage_status(*, runtime_backed: bool, observed_record_count: int) -> str:
    if not runtime_backed:
        return "blocked_not_runtime_backed"
    if observed_record_count == 0:
        return "runtime_backed_no_records"
    return "runtime_backed"


def _product_freshness_state(
    *,
    runtime_backed: bool,
    observed_record_count: int,
    stale_or_unavailable_source_ref_count: int,
) -> str:
    if not runtime_backed or observed_record_count == 0:
        return "unknown"
    if stale_or_unavailable_source_ref_count > 0:
        return "stale"
    return "current"


def _product_completeness_status(
    *,
    runtime_backed: bool,
    observed_record_count: int,
    stale_or_unavailable_source_ref_count: int,
) -> str:
    if not runtime_backed:
        return "blocked"
    if observed_record_count == 0:
        return "unknown"
    if stale_or_unavailable_source_ref_count > 0:
        return "stale"
    return "partial"


def _product_reconciliation_status(
    *,
    runtime_backed: bool,
    observed_record_count: int,
    stale_or_unavailable_source_ref_count: int,
) -> str:
    if not runtime_backed:
        return "blocked"
    if observed_record_count == 0:
        return "unknown"
    if stale_or_unavailable_source_ref_count > 0:
        return "partial"
    return "not_applicable"


def _product_certification_blockers(
    *,
    runtime_backed: bool,
    durable_storage_backed: bool,
    observed_record_count: int,
    stale_or_unavailable_source_ref_count: int,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not runtime_backed:
        blockers.append("runtime_product_materialization_missing")
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if runtime_backed and observed_record_count == 0:
        blockers.append("runtime_product_records_missing")
    if runtime_backed and stale_or_unavailable_source_ref_count > 0:
        blockers.append("stale_or_unavailable_source_refs_present")
    blockers.extend(COMMON_PRODUCT_CERTIFICATION_BLOCKERS)
    return tuple(dict.fromkeys(blockers))


def _trust_telemetry_lineage_materialized(product_id: str, generated_at_utc: datetime) -> bool:
    return product_id == "lotus-idea:IdeaTrustTelemetry:v1" and generated_at_utc.tzinfo is not None


def _product_posture_payload(posture: RuntimeTrustTelemetryProductPosture) -> dict[str, Any]:
    return {
        "product_id": posture.product_id,
        "product_name": posture.product_name,
        "product_version": posture.product_version,
        "lifecycle_status": posture.lifecycle_status,
        "freshness_class": posture.freshness_class,
        "coverage_status": posture.coverage_status,
        "runtime_backed": posture.runtime_backed,
        "observed_record_count": posture.observed_record_count,
        "current_source_ref_count": posture.current_source_ref_count,
        "stale_or_unavailable_source_ref_count": posture.stale_or_unavailable_source_ref_count,
        "freshness_state": posture.freshness_state,
        "completeness_status": posture.completeness_status,
        "reconciliation_status": posture.reconciliation_status,
        "data_quality_status": posture.data_quality_status,
        "lineage_materialized": posture.lineage_materialized,
        "source_batch_evidence_available": posture.source_batch_evidence_available,
        "consumer_exposure_status": posture.consumer_exposure_status,
        "certification_blockers": list(posture.certification_blockers),
    }


def _certification_blockers(
    *,
    durable_storage_backed: bool,
    candidate_snapshot_count: int,
    stale_or_unavailable_source_ref_count: int,
    product_postures: tuple[RuntimeTrustTelemetryProductPosture, ...],
) -> tuple[str, ...]:
    blockers = [
        "platform_source_manifest_inclusion_missing",
        "platform_mesh_certification_missing",
        "gateway_workbench_discovery_proof_missing",
        "supported_feature_promotion_missing",
    ]
    if _product_coverage_incomplete(product_postures):
        blockers.insert(0, "runtime_trust_telemetry_product_coverage_incomplete")
        blockers.insert(1, "certified_runtime_trust_telemetry_missing")
    if not durable_storage_backed:
        blockers.insert(0, "durable_repository_not_configured")
    if candidate_snapshot_count == 0:
        blockers.insert(0, "runtime_candidate_snapshot_missing")
    if stale_or_unavailable_source_ref_count > 0:
        blockers.insert(0, "stale_or_unavailable_source_refs_present")
    return tuple(dict.fromkeys(blockers))


def _product_coverage_incomplete(
    product_postures: tuple[RuntimeTrustTelemetryProductPosture, ...],
) -> bool:
    if not product_postures:
        return True
    for posture in product_postures:
        if posture.coverage_status != "runtime_backed":
            return True
        if set(posture.certification_blockers).intersection(
            PRODUCT_COVERAGE_CERTIFICATION_BLOCKERS
        ):
            return True
    return False


def _snapshot_freshness(
    *,
    preview: RuntimeTrustTelemetryPreview,
    summary: RuntimeTrustTelemetryRepositorySummary,
) -> dict[str, Any]:
    freshness: dict[str, Any] = {
        "freshness_class": "daily",
        "freshness_state": _freshness_state(preview),
        "evaluated_at_utc": _format_utc(preview.generated_at_utc),
    }
    latest_generated_at = summary.latest_source_generated_at_utc
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
    summary: RuntimeTrustTelemetryRepositorySummary,
    completeness_status: str,
    reconciliation_status: str,
    data_quality_status: str,
) -> dict[str, str]:
    if summary.candidate_snapshot_count == 0:
        return {}
    metadata = {
        "product_name": PRODUCT_NAME,
        "product_version": PRODUCT_VERSION,
        "generated_at": _format_utc(preview.generated_at_utc),
        "reconciliation_status": reconciliation_status,
        "data_quality_status": data_quality_status,
        "lineage_bundle_id": "lotus-idea:IdeaCandidate:v1:runtime-lineage",
        "correlation_id": "lotus-idea-runtime-trust-telemetry-snapshot",
    }
    if len(summary.source_as_of_dates) == 1:
        metadata["as_of_date"] = summary.source_as_of_dates[0]
    if completeness_status != "unknown":
        metadata["source_batch_fingerprint"] = "source-safe-runtime-aggregate"
    return metadata


def _runtime_trust_telemetry_summary(
    repository: CandidateSnapshotRepository,
) -> RuntimeTrustTelemetryRepositorySummary:
    if isinstance(repository, RuntimeTrustTelemetryProjectionRepository):
        return repository.runtime_trust_telemetry_summary()
    return _runtime_trust_telemetry_summary_from_records(
        tuple(repository.snapshot().candidate_records.values())
    )


def _runtime_trust_telemetry_summary_from_records(
    records: tuple[CandidatePersistenceRecord, ...],
) -> RuntimeTrustTelemetryRepositorySummary:
    source_refs = tuple(
        source_ref
        for record in records
        for source_ref in record.candidate.evidence_packet.source_refs
    )
    freshness_counts = Counter(source_ref.freshness.value for source_ref in source_refs)
    current_source_ref_count = freshness_counts.get(EvidenceFreshness.CURRENT.value, 0)
    stale_or_unavailable_source_ref_count = len(source_refs) - current_source_ref_count
    return RuntimeTrustTelemetryRepositorySummary(
        candidate_snapshot_count=len(records),
        current_source_ref_count=current_source_ref_count,
        stale_or_unavailable_source_ref_count=stale_or_unavailable_source_ref_count,
        source_authority_counts=Counter(
            source_ref.source_system.value for source_ref in source_refs
        ),
        freshness_counts=freshness_counts,
        supportability_counts=Counter(
            record.candidate.evidence_packet.supportability.value for record in records
        ),
        lifecycle_counts=Counter(record.candidate.lifecycle_status.value for record in records),
        review_decision_count=sum(len(record.review_decisions) for record in records),
        feedback_event_count=sum(len(record.feedback_events) for record in records),
        conversion_intent_count=sum(len(record.conversion_intents) for record in records),
        conversion_outcome_count=sum(len(record.conversion_outcomes) for record in records),
        report_evidence_pack_count=sum(len(record.report_evidence_packs) for record in records),
        lineage_materialized=bool(records)
        and all(_record_lineage_materialized(record) for record in records),
        source_batch_evidence_available=bool(source_refs),
        data_quality_status=_data_quality_status(source_refs),
        latest_source_generated_at_utc=max(
            (source_ref.generated_at_utc for source_ref in source_refs),
            default=None,
        ),
        source_as_of_dates=tuple(
            sorted({source_ref.as_of_date.isoformat() for source_ref in source_refs})
        ),
    )


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
