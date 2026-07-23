from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.domain.proof_evidence import EvidenceClass

OUTBOX_BROKER_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_OUTBOX_BROKER_RUNTIME_EXECUTION_PROOF"
OUTBOX_BROKER_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.outbox-broker-runtime-execution.v1"
OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED = ("external_broker_runtime_proof_missing",)
REMAINING_OUTBOX_BROKER_RUNTIME_BLOCKERS = (
    "downstream_consumer_runtime_proof_missing",
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
OUTBOX_BROKER_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/outbox/delivery.py",
    "src/app/application/outbox/readiness.py",
    "src/app/application/outbox/broker/runtime_execution.py",
    "src/app/infrastructure/outbox/publisher.py",
    "src/app/runtime/outbox/publisher_state.py",
    "scripts/outbox/broker/generate_runtime_execution.py",
    "scripts/outbox/broker/runtime_execution_gate.py",
    "tests/unit/outbox/broker/test_runtime_execution.py",
    "tests/unit/outbox/test_outbox_delivery.py",
    "tests/unit/outbox/test_outbox_publisher_adapter.py",
    "make outbox-broker-runtime-execution-proof-gate",
    "POST /api/v1/outbox-delivery/run-once",
)

_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "runtimeProofValid",
        "runtimeMode",
        "brokerDependency",
        "publisherAdapter",
        "publishPath",
        "eventType",
        "evidenceRefs",
        "publicationReceipt",
        "runtimeChecks",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "nonProofClaims",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "outcomeAccepted",
        "failureReasonCode",
        "sourceSafeEnvelopePublished",
        "supportabilityStatusPublished",
    }
)
_RUNTIME_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "httpServiceRuntimeMode",
        "brokerConfigured",
        "publisherAdapterObserved",
        "sourceSafeEnvelopePublished",
        "publicationAccepted",
        "failureReasonBounded",
        "supportabilityStatusNotPromoted",
        "nonProofClaimsRetained",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "downstreamConsumersCertified",
        "platformMeshEventCertified",
        "gatewayWorkbenchProofPresent",
        "supportedFeaturePromoted",
        "productionCertificationGranted",
        "certificationClosed",
    }
)
_BOUNDED_FAILURE_REASONS = frozenset(
    {
        "publisher_permission_denied",
        "publisher_rejected",
        "publisher_timeout",
        "publisher_malformed_response",
        "publisher_unavailable",
    }
)
_EXPECTED_PROOF_TYPE = "outbox_broker_runtime_execution"
_EXPECTED_PROOF_SCOPE = "configured_http_broker_publication"
_EXPECTED_RUNTIME_MODE = "http_service"
_EXPECTED_BROKER_DEPENDENCY = "lotus-platform-broker"
_EXPECTED_PUBLISHER_ADAPTER = "HttpOutboxEventPublisher"
_EXPECTED_PUBLISH_PATH = "/events/lotus-idea/outbox"


def build_outbox_broker_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    broker_configured: bool,
    publication_receipt: Mapping[str, Any],
    runtime_mode: str = _EXPECTED_RUNTIME_MODE,
    broker_dependency: str = _EXPECTED_BROKER_DEPENDENCY,
    publisher_adapter: str = _EXPECTED_PUBLISHER_ADAPTER,
    publish_path: str = _EXPECTED_PUBLISH_PATH,
    event_type: str = "idea.candidate.persisted.v1",
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    receipt = _publication_receipt(publication_receipt)
    runtime_checks = {
        "timezoneAwareGeneratedAtUtc": True,
        "httpServiceRuntimeMode": runtime_mode == _EXPECTED_RUNTIME_MODE,
        "brokerConfigured": broker_configured is True,
        "publisherAdapterObserved": publisher_adapter == _EXPECTED_PUBLISHER_ADAPTER,
        "sourceSafeEnvelopePublished": receipt["sourceSafeEnvelopePublished"] is True,
        "publicationAccepted": receipt["outcomeAccepted"] is True,
        "failureReasonBounded": _failure_reason_is_bounded(receipt["failureReasonCode"]),
        "supportabilityStatusNotPromoted": (
            receipt["supportabilityStatusPublished"] == "not_certified"
        ),
        "nonProofClaimsRetained": True,
    }
    return {
        "schemaVersion": OUTBOX_BROKER_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": all(runtime_checks.values()),
        "runtimeMode": runtime_mode,
        "brokerDependency": broker_dependency,
        "publisherAdapter": publisher_adapter,
        "publishPath": publish_path,
        "eventType": event_type,
        "evidenceRefs": OUTBOX_BROKER_RUNTIME_EVIDENCE_REFS,
        "publicationReceipt": receipt,
        "runtimeChecks": runtime_checks,
        "aggregateBlockersSatisfied": OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_OUTBOX_BROKER_RUNTIME_BLOCKERS,
        "nonProofClaims": {
            "downstreamConsumersCertified": False,
            "platformMeshEventCertified": False,
            "gatewayWorkbenchProofPresent": False,
            "supportedFeaturePromoted": False,
            "productionCertificationGranted": False,
            "certificationClosed": False,
        },
    }


def outbox_broker_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": OUTBOX_BROKER_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "runtimeMode": _EXPECTED_RUNTIME_MODE,
        "brokerDependency": _EXPECTED_BROKER_DEPENDENCY,
        "publisherAdapter": _EXPECTED_PUBLISHER_ADAPTER,
        "publishPath": _EXPECTED_PUBLISH_PATH,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != OUTBOX_BROKER_RUNTIME_EVIDENCE_REFS:
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != REMAINING_OUTBOX_BROKER_RUNTIME_BLOCKERS
    ):
        return False
    if not _publication_receipt_is_valid(payload.get("publicationReceipt")):
        return False
    if not _runtime_checks_are_valid(payload.get("runtimeChecks")):
        return False
    return _non_proof_claims_are_retained(payload.get("nonProofClaims"))


def _publication_receipt(publication_receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "outcomeAccepted": publication_receipt.get("outcomeAccepted") is True,
        "failureReasonCode": publication_receipt.get("failureReasonCode"),
        "sourceSafeEnvelopePublished": (
            publication_receipt.get("sourceSafeEnvelopePublished") is True
        ),
        "supportabilityStatusPublished": str(
            publication_receipt.get("supportabilityStatusPublished", "")
        ),
    }


def _publication_receipt_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_FIELDS:
        return False
    return (
        value.get("outcomeAccepted") is True
        and value.get("failureReasonCode") is None
        and value.get("sourceSafeEnvelopePublished") is True
        and value.get("supportabilityStatusPublished") == "not_certified"
    )


def _runtime_checks_are_valid(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _RUNTIME_CHECK_FIELDS
        and all(value.get(field_name) is True for field_name in _RUNTIME_CHECK_FIELDS)
    )


def _non_proof_claims_are_retained(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _NON_PROOF_CLAIM_FIELDS
        and all(value.get(field_name) is False for field_name in _NON_PROOF_CLAIM_FIELDS)
    )


def _failure_reason_is_bounded(value: object) -> bool:
    return value is None or value in _BOUNDED_FAILURE_REASONS
