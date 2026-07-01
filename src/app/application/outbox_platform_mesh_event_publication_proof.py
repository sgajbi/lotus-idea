from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text
_required_file_evidence_present = required_file_evidence_present
_required_make_target_evidence_present = required_make_target_evidence_present


OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_ENV = (
    "LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF"
)
OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION = (
    "lotus-idea.outbox-platform-mesh-event-publication-proof.v1"
)

OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED = (
    "platform_mesh_event_publication_proof_missing",
)

REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS = (
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS = (
    "contracts/outbox-events/lotus-idea-outbox-events.v1.json",
    "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
    "../lotus-platform/platform-contracts/domain-data-products/domain-product-source-manifest.v1.json",
    "../lotus-platform/generated/domain-product-catalog.json",
    "../lotus-platform/docs/operations/enterprise-mesh-completion-handoff.md",
    "src/app/domain/events.py",
    "src/app/application/outbox_delivery.py",
    "src/app/application/outbox_delivery_readiness.py",
    "src/app/application/outbox_platform_mesh_event_publication_proof.py",
    "scripts/outbox_event_contract_gate.py",
    "scripts/outbox_platform_mesh_event_publication_proof_contract_gate.py",
    "tests/unit/test_outbox_platform_mesh_event_publication_proof.py",
    "make outbox-event-contract-gate",
    "make outbox-platform-mesh-event-publication-proof-contract-gate",
    "GET /api/v1/outbox-delivery/readiness",
    "POST /api/v1/outbox-delivery/run-once",
)

REQUIRED_OUTBOX_EVENT_TYPES = (
    "idea.candidate.persisted.v1",
    "idea.lifecycle.transitioned.v1",
    "idea.review.decision_recorded.v1",
    "idea.feedback.recorded.v1",
    "idea.conversion.intent_requested.v1",
    "idea.conversion.outcome_recorded.v1",
    "idea.report_evidence_pack.requested.v1",
)

REQUIRED_PLATFORM_PRODUCT_IDS = (
    "lotus-idea:AdvisorOpportunityQueue:v1",
    "lotus-idea:IdeaCandidate:v1",
    "lotus-idea:IdeaConversionIntent:v1",
    "lotus-idea:IdeaConversionOutcome:v1",
    "lotus-idea:IdeaEvidencePacket:v1",
    "lotus-idea:IdeaFeedbackEvent:v1",
    "lotus-idea:IdeaReviewDecision:v1",
)


def build_outbox_platform_mesh_event_publication_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    platform_root: Path | None = None,
) -> dict[str, Any]:
    platform_root = platform_root or repository_root.parent / "lotus-platform"
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={"../lotus-platform/": platform_root},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("GET ", "POST ", "make "),
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    event_contract = _load_json_object(
        repository_root / "contracts/outbox-events/lotus-idea-outbox-events.v1.json"
    )
    consumer_contract = _load_json_object(
        repository_root / "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json"
    )
    source_manifest = _load_json_object(
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    catalog = _load_json_object(platform_root / "generated/domain-product-catalog.json")
    event_contract_source_safe = _event_contract_is_source_safe(event_contract)
    event_family_coverage = _event_family_coverage_present(event_contract)
    consumer_contract_links_events = _consumer_contract_links_declared_events(
        consumer_contract=consumer_contract,
        event_contract=event_contract,
    )
    platform_onboarding_present = _platform_source_manifest_includes_lotus_idea(source_manifest)
    platform_catalog_maps_idea_products = _platform_catalog_maps_idea_products(catalog)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and event_contract_source_safe
        and event_family_coverage
        and consumer_contract_links_events
        and platform_onboarding_present
        and platform_catalog_maps_idea_products
    )
    return {
        "schemaVersion": OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "outbox_platform_mesh_event_publication_contract",
        "proofScope": "bounded_source_safe_event_contract_and_platform_onboarding",
        "outboxPlatformMeshEventPublicationProofValid": proof_valid,
        "aggregateBlockersCleared": OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "eventTypeCount": len(REQUIRED_OUTBOX_EVENT_TYPES),
        "platformProductCount": len(REQUIRED_PLATFORM_PRODUCT_IDS),
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "eventContractSourceSafe": event_contract_source_safe,
            "eventFamilyCoveragePresent": event_family_coverage,
            "consumerContractLinksDeclaredEvents": consumer_contract_links_events,
            "platformSourceManifestIncludesLotusIdea": platform_onboarding_present,
            "platformCatalogMapsIdeaProducts": platform_catalog_maps_idea_products,
        },
        "remainingCertificationBlockers": (
            REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS
        ),
        "externalBrokerPublicationSupported": False,
        "downstreamConsumersCertified": False,
        "gatewayWorkbenchProofPresent": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def outbox_platform_mesh_event_publication_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "outbox_platform_mesh_event_publication_contract":
        return False
    if payload.get("proofScope") != "bounded_source_safe_event_contract_and_platform_onboarding":
        return False
    if payload.get("outboxPlatformMeshEventPublicationProofValid") is not True:
        return False
    if payload.get("externalBrokerPublicationSupported") is not False:
        return False
    if payload.get("downstreamConsumersCertified") is not False:
        return False
    if payload.get("gatewayWorkbenchProofPresent") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS
    ):
        return False
    if payload.get("eventTypeCount") != len(REQUIRED_OUTBOX_EVENT_TYPES):
        return False
    if payload.get("platformProductCount") != len(REQUIRED_PLATFORM_PRODUCT_IDS):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "makeTargetEvidencePresent",
            "eventContractSourceSafe",
            "eventFamilyCoveragePresent",
            "consumerContractLinksDeclaredEvents",
            "platformSourceManifestIncludesLotusIdea",
            "platformCatalogMapsIdeaProducts",
        )
    )


def _load_json_object(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _event_contract_is_source_safe(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("sourceAuthority") != "lotus-idea":
        return False
    if payload.get("platformMeshEventContractAvailable") is not True:
        return False
    if payload.get("externalBrokerPublicationSupported") is not False:
        return False
    if payload.get("downstreamConsumersCertified") is not False:
        return False
    if payload.get("gatewayWorkbenchProofPresent") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    policy = payload.get("payloadSafetyPolicy")
    if not isinstance(policy, Mapping):
        return False
    forbidden_keys = policy.get("forbiddenPayloadKeys")
    if not isinstance(forbidden_keys, Sequence) or isinstance(forbidden_keys, (str, bytes)):
        return False
    required_forbidden = {
        "account_id",
        "client_id",
        "content_hash",
        "evidence_hash",
        "idempotency_key",
        "portfolio_id",
        "raw_source_payload",
        "request_body",
        "response_body",
        "source_route",
    }
    return required_forbidden <= set(forbidden_keys)


def _event_family_coverage_present(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    event_families = payload.get("eventFamilies")
    if not isinstance(event_families, Sequence) or isinstance(event_families, (str, bytes)):
        return False
    event_types = tuple(
        event_family.get("eventType")
        for event_family in event_families
        if isinstance(event_family, Mapping)
    )
    return event_types == REQUIRED_OUTBOX_EVENT_TYPES and all(
        isinstance(event_family, Mapping)
        and event_family.get("aggregateType") == "idea_candidate"
        and isinstance(event_family.get("description"), str)
        and len(event_family["description"].strip()) >= 24
        for event_family in event_families
    )


def _consumer_contract_links_declared_events(
    *,
    consumer_contract: Mapping[str, Any] | None,
    event_contract: Mapping[str, Any] | None,
) -> bool:
    if consumer_contract is None or event_contract is None:
        return False
    declared_event_types = set(_event_types(event_contract))
    if set(REQUIRED_OUTBOX_EVENT_TYPES) != declared_event_types:
        return False
    consumers = consumer_contract.get("declaredConsumers")
    if not isinstance(consumers, Sequence) or isinstance(consumers, (str, bytes)):
        return False
    for consumer in consumers:
        if not isinstance(consumer, Mapping):
            return False
        if consumer.get("certificationStatus") != "contract_declared_not_runtime_certified":
            return False
        consumed_types = consumer.get("consumedEventTypes")
        if not isinstance(consumed_types, Sequence) or isinstance(consumed_types, (str, bytes)):
            return False
        if not consumed_types or any(
            event_type not in declared_event_types for event_type in consumed_types
        ):
            return False
    return True


def _event_types(payload: Mapping[str, Any]) -> tuple[str, ...]:
    event_families = payload.get("eventFamilies")
    if not isinstance(event_families, Sequence) or isinstance(event_families, (str, bytes)):
        return ()
    return tuple(
        event_family["eventType"]
        for event_family in event_families
        if isinstance(event_family, Mapping) and isinstance(event_family.get("eventType"), str)
    )


def _platform_source_manifest_includes_lotus_idea(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    repositories = payload.get("repositories")
    if not isinstance(repositories, Sequence) or isinstance(repositories, (str, bytes)):
        return False
    for entry in repositories:
        if not isinstance(entry, Mapping) or entry.get("repository") != "lotus-idea":
            continue
        return (
            entry.get("source_mode") == "repo_native"
            and entry.get("catalog_inclusion") == "included"
            and entry.get("repo_native_status") == "implemented"
            and entry.get("repo_native_declaration_path") == "contracts/domain-data-products"
        )
    return False


def _platform_catalog_maps_idea_products(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    products = payload.get("products")
    if not isinstance(products, Sequence) or isinstance(products, (str, bytes)):
        return False
    by_id = {
        product.get("product_id"): product for product in products if isinstance(product, Mapping)
    }
    for product_id in REQUIRED_PLATFORM_PRODUCT_IDS:
        product = by_id.get(product_id)
        if not isinstance(product, Mapping):
            return False
        if product.get("producer_repository") != "lotus-idea":
            return False
        if product.get("lifecycle_status") != "proposed":
            return False
    return True
