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


OUTBOX_CONSUMER_RUNTIME_PROOF_ENV = "LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF"
OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION = "lotus-idea.outbox-consumer-runtime-proof.v1"

OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED = ("downstream_consumer_runtime_proof_missing",)

REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS = (
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS = (
    "contracts/outbox-events/lotus-idea-outbox-events.v1.json",
    "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
    "scripts/outbox_consumer_contract_gate.py",
    "scripts/outbox_consumer_runtime_proof_contract_gate.py",
    "src/app/application/outbox_delivery_readiness.py",
    "src/app/application/outbox_consumer_runtime_proof.py",
    "tests/unit/test_outbox_delivery_readiness.py",
    "tests/unit/test_outbox_consumer_runtime_proof.py",
    "make outbox-consumer-contract-gate",
    "make outbox-consumer-runtime-proof-contract-gate",
)

REQUIRED_CONSUMERS = ("lotus-gateway", "lotus-advise", "lotus-manage", "lotus-report")


def build_outbox_consumer_runtime_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ",),
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    contract_payload = _load_json_object(
        repository_root / "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json"
    )
    event_contract_payload = _load_json_object(
        repository_root / "contracts/outbox-events/lotus-idea-outbox-events.v1.json"
    )
    declared_consumer_coverage = _declared_consumer_coverage_present(contract_payload)
    event_type_coverage = _declared_event_types_are_source_owned(
        contract_payload=contract_payload,
        event_contract_payload=event_contract_payload,
    )
    authority_boundaries_preserved = _authority_boundaries_preserved(contract_payload)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and declared_consumer_coverage
        and event_type_coverage
        and authority_boundaries_preserved
    )
    return {
        "schemaVersion": OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "outbox_downstream_consumer_runtime_contract",
        "proofScope": "bounded_declared_consumer_runtime_proof",
        "outboxConsumerRuntimeProofValid": proof_valid,
        "aggregateBlockersCleared": OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "declaredConsumerCoveragePresent": declared_consumer_coverage,
            "eventTypeCoverageSourceOwned": event_type_coverage,
            "authorityBoundariesPreserved": authority_boundaries_preserved,
        },
        "remainingCertificationBlockers": (
            REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS
        ),
        "externalBrokerPublicationSupported": False,
        "platformMeshEventCertified": False,
        "gatewayWorkbenchProofPresent": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def outbox_consumer_runtime_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "outbox_downstream_consumer_runtime_contract":
        return False
    if payload.get("proofScope") != "bounded_declared_consumer_runtime_proof":
        return False
    if payload.get("outboxConsumerRuntimeProofValid") is not True:
        return False
    if payload.get("externalBrokerPublicationSupported") is not False:
        return False
    if payload.get("platformMeshEventCertified") is not False:
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
        OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("declaredConsumerCoveragePresent") is True
        and proof_checks.get("eventTypeCoverageSourceOwned") is True
        and proof_checks.get("authorityBoundariesPreserved") is True
    )


def _load_json_object(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    return payload


def _declared_consumer_coverage_present(contract_payload: Mapping[str, Any] | None) -> bool:
    if contract_payload is None:
        return False
    consumers = contract_payload.get("declaredConsumers")
    if not isinstance(consumers, Sequence) or isinstance(consumers, (str, bytes)):
        return False
    repositories = tuple(
        consumer.get("consumerRepository")
        for consumer in consumers
        if isinstance(consumer, Mapping)
    )
    return repositories == REQUIRED_CONSUMERS and all(
        isinstance(consumer, Mapping)
        and consumer.get("certificationStatus") == "contract_declared_not_runtime_certified"
        for consumer in consumers
    )


def _declared_event_types_are_source_owned(
    *,
    contract_payload: Mapping[str, Any] | None,
    event_contract_payload: Mapping[str, Any] | None,
) -> bool:
    if contract_payload is None or event_contract_payload is None:
        return False
    event_types = set(_event_types_from_contract(event_contract_payload))
    if not event_types:
        return False
    consumers = contract_payload.get("declaredConsumers")
    if not isinstance(consumers, Sequence) or isinstance(consumers, (str, bytes)):
        return False
    for consumer in consumers:
        if not isinstance(consumer, Mapping):
            return False
        consumed_event_types = consumer.get("consumedEventTypes")
        if not isinstance(consumed_event_types, Sequence) or isinstance(
            consumed_event_types, (str, bytes)
        ):
            return False
        if not consumed_event_types:
            return False
        if any(event_type not in event_types for event_type in consumed_event_types):
            return False
    return True


def _event_types_from_contract(event_contract_payload: Mapping[str, Any]) -> tuple[str, ...]:
    event_families = event_contract_payload.get("eventFamilies")
    if not isinstance(event_families, Sequence) or isinstance(event_families, (str, bytes)):
        return ()
    return tuple(
        event_family["eventType"]
        for event_family in event_families
        if isinstance(event_family, Mapping) and isinstance(event_family.get("eventType"), str)
    )


def _authority_boundaries_preserved(contract_payload: Mapping[str, Any] | None) -> bool:
    if contract_payload is None:
        return False
    policy = contract_payload.get("consumerContractPolicy")
    if not isinstance(policy, Mapping):
        return False
    policy_text = " ".join(value for value in policy.values() if isinstance(value, str)).lower()
    required_policy_fragments = (
        "source-authoritative services",
        "must not require raw",
        "must not echo raw",
        "live contract tests",
    )
    if any(fragment not in policy_text for fragment in required_policy_fragments):
        return False
    consumers = contract_payload.get("declaredConsumers")
    if not isinstance(consumers, Sequence) or isinstance(consumers, (str, bytes)):
        return False
    required_boundary_terms = {
        "lotus-gateway": ("must not become", "suitability", "report"),
        "lotus-advise": ("suitability", "authoritative"),
        "lotus-manage": ("rebalance", "authoritative"),
        "lotus-report": ("report", "authoritative"),
    }
    for consumer in consumers:
        if not isinstance(consumer, Mapping):
            return False
        repository = consumer.get("consumerRepository")
        boundary = consumer.get("authorityBoundary")
        if not isinstance(repository, str) or not isinstance(boundary, str):
            return False
        boundary_text = boundary.lower()
        required_terms = required_boundary_terms.get(repository)
        if required_terms is None:
            return False
        if any(term not in boundary_text for term in required_terms):
            return False
    return True
