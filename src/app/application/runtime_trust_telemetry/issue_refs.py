from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


ISSUE_RUNTIME_TRUST_TELEMETRY = "sgajbi/lotus-idea#692"
ISSUE_DATA_PRODUCT_PROMOTION = "sgajbi/lotus-idea#380"
ISSUE_FINAL_RFC_CLOSURE = "sgajbi/lotus-idea#683"
ISSUE_SUPPORTED_FEATURE_PROOF_PACK = "sgajbi/lotus-idea#697"
ISSUE_AGGREGATE_PROOF = "sgajbi/lotus-idea#680"
ISSUE_DATA_LIFECYCLE = "sgajbi/lotus-idea#344"
ISSUE_SOURCE_RUNTIME_PROOF = "sgajbi/lotus-idea#698"
ISSUE_PLATFORM_MESH_CERTIFICATION = "sgajbi/lotus-platform#598"
ISSUE_GATEWAY_PRODUCT_PROOF = "sgajbi/lotus-gateway#505"
ISSUE_WORKBENCH_PRODUCT_PROOF = "sgajbi/lotus-workbench#484"
ISSUE_CANONICAL_RUNTIME = "sgajbi/lotus-platform#563"


_BLOCKER_ISSUE_REFS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "runtime_candidate_snapshot_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_AGGREGATE_PROOF,
        ),
        "runtime_trust_telemetry_product_coverage_incomplete": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_DATA_PRODUCT_PROMOTION,
        ),
        "certified_runtime_trust_telemetry_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_DATA_PRODUCT_PROMOTION,
        ),
        "data_mesh_runtime_telemetry_not_certified": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_PLATFORM_MESH_CERTIFICATION,
        ),
        "runtime_product_materialization_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_DATA_PRODUCT_PROMOTION,
        ),
        "runtime_product_records_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_SOURCE_RUNTIME_PROOF,
        ),
        "stale_or_unavailable_source_refs_present": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_SOURCE_RUNTIME_PROOF,
        ),
        "durable_repository_not_configured": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_AGGREGATE_PROOF,
        ),
        "data_lifecycle_controls_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_DATA_LIFECYCLE,
        ),
        "platform_source_manifest_inclusion_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_PLATFORM_MESH_CERTIFICATION,
        ),
        "platform_mesh_certification_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_PLATFORM_MESH_CERTIFICATION,
        ),
        "gateway_workbench_discovery_proof_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_GATEWAY_PRODUCT_PROOF,
            ISSUE_WORKBENCH_PRODUCT_PROOF,
            ISSUE_CANONICAL_RUNTIME,
        ),
        "supported_feature_promotion_missing": (
            ISSUE_RUNTIME_TRUST_TELEMETRY,
            ISSUE_DATA_PRODUCT_PROMOTION,
            ISSUE_SUPPORTED_FEATURE_PROOF_PACK,
            ISSUE_FINAL_RFC_CLOSURE,
        ),
    }
)


def runtime_trust_telemetry_blocker_issue_refs(
    blockers: tuple[str, ...],
) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType({blocker: _BLOCKER_ISSUE_REFS.get(blocker, ()) for blocker in blockers})


def required_runtime_trust_telemetry_blocker_issue_refs() -> Mapping[str, tuple[str, ...]]:
    return _BLOCKER_ISSUE_REFS
