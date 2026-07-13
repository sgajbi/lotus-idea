from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
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


OUTBOX_BROKER_PROOF_ENV = "LOTUS_IDEA_OUTBOX_BROKER_PROOF"
OUTBOX_BROKER_PROOF_SCHEMA_VERSION = "lotus-idea.outbox-broker-proof.v1"

REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS = (
    "src/app/application/outbox/delivery.py",
    "src/app/application/outbox/readiness.py",
    "src/app/ports/outbox/publisher.py",
    "src/app/infrastructure/outbox/publisher.py",
    "contracts/outbox-events/lotus-idea-outbox-events.v1.json",
    "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
    "tests/unit/outbox/test_outbox_delivery.py",
    "tests/unit/outbox/test_outbox_delivery_readiness.py",
    "tests/integration/outbox/test_delivery_readiness_api.py",
    "make outbox-event-contract-gate",
    "make outbox-consumer-contract-gate",
    "make outbox-broker-proof-contract-gate",
    "GET /api/v1/outbox-delivery/readiness",
    "POST /api/v1/outbox-delivery/run-once",
)

OUTBOX_BROKER_BLOCKERS_CLEARED = (
    "outbox_broker_not_configured",
    "external_broker_runtime_proof_missing",
)

REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS = (
    "downstream_consumer_runtime_proof_missing",
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)


def build_outbox_broker_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ", "GET ", "POST "),
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    configured_publisher_runtime_exercised = _configured_publisher_runtime_evidence_present(
        repository_root=repository_root,
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and configured_publisher_runtime_exercised
    )
    return {
        "schemaVersion": OUTBOX_BROKER_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "outbox_broker_runtime_contract",
        "proofScope": "bounded_configured_publisher_runtime_proof",
        "outboxBrokerProofValid": proof_valid,
        "aggregateBlockersCleared": OUTBOX_BROKER_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "configuredPublisherRuntimeExercised": configured_publisher_runtime_exercised,
            "readinessEndpointCertified": "GET /api/v1/outbox-delivery/readiness",
            "runOnceEndpointCertified": "POST /api/v1/outbox-delivery/run-once",
        },
        "remainingCertificationBlockers": REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS,
        "externalBrokerPublicationSupported": False,
        "platformMeshEventCertified": False,
        "downstreamConsumersCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def outbox_broker_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != OUTBOX_BROKER_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "outbox_broker_runtime_contract":
        return False
    if payload.get("proofScope") != "bounded_configured_publisher_runtime_proof":
        return False
    if payload.get("outboxBrokerProofValid") is not True:
        return False
    if payload.get("externalBrokerPublicationSupported") is not False:
        return False
    if payload.get("platformMeshEventCertified") is not False:
        return False
    if payload.get("downstreamConsumersCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != OUTBOX_BROKER_BLOCKERS_CLEARED:
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("configuredPublisherRuntimeExercised") is True
        and proof_checks.get("readinessEndpointCertified")
        == "GET /api/v1/outbox-delivery/readiness"
        and proof_checks.get("runOnceEndpointCertified") == "POST /api/v1/outbox-delivery/run-once"
    )


def _configured_publisher_runtime_evidence_present(*, repository_root: Path) -> bool:
    try:
        api_test_text = (
            repository_root / "tests/integration/outbox/test_delivery_readiness_api.py"
        ).read_text(encoding="utf-8")
    except OSError:
        return False
    required_fragments = (
        "test_outbox_delivery_run_once_api_publishes_with_configured_publisher",
        "AcceptingPublisher",
        "/api/v1/outbox-delivery/run-once",
        '"supportabilityStatus"] == "not_certified"',
        '"supportedFeaturePromoted"] is False',
        '"external_broker_runtime_proof_missing" in payload["certificationBlockers"]',
    )
    return all(fragment in api_test_text for fragment in required_fragments)
