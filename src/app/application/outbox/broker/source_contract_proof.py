from __future__ import annotations

import ast
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear


OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_ENV = "LOTUS_IDEA_OUTBOX_BROKER_SOURCE_CONTRACT_PROOF"
OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.outbox-broker-source-contract-proof.v2"
)

OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES: tuple[tuple[str, str], ...] = ()
OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED: tuple[str, ...] = ()

REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS = (
    "outbox_broker_not_configured",
    "external_broker_runtime_proof_missing",
    "downstream_consumer_runtime_proof_missing",
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS = (
    "src/app/application/outbox/delivery.py",
    "src/app/application/outbox/readiness.py",
    "src/app/application/outbox/broker/source_contract_proof.py",
    "src/app/ports/outbox/publisher.py",
    "src/app/infrastructure/outbox/publisher.py",
    "contracts/outbox-events/lotus-idea-outbox-events.v1.json",
    "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
    "scripts/outbox/broker/generate_source_contract_proof.py",
    "scripts/outbox/broker/source_contract_proof_gate.py",
    "tests/unit/outbox/broker/test_source_contract_proof.py",
    "tests/unit/outbox/broker/test_readiness_consumption.py",
    "tests/integration/outbox/test_delivery_readiness_api.py",
    "make outbox-event-contract-gate",
    "make outbox-consumer-contract-gate",
    "make outbox-broker-source-contract-proof-gate",
    "GET /api/v1/outbox-delivery/readiness",
    "POST /api/v1/outbox-delivery/run-once",
)


def build_outbox_broker_source_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_refs = tuple(REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS)
    file_evidence_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ", "GET ", "POST "),
    )
    make_target_evidence_present = required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    publisher_port_contract_present = _python_class_declares_methods(
        repository_root / "src/app/ports/outbox/publisher.py",
        class_name="OutboxEventPublisher",
        required_methods=("publish",),
    )
    publisher_adapter_contract_present = _python_class_declares_methods(
        repository_root / "src/app/infrastructure/outbox/publisher.py",
        class_name="HttpOutboxEventPublisher",
        required_methods=("publish", "close"),
    )
    evidence_class_matches_blockers = all(
        evidence_class_can_clear(
            actual=EvidenceClass.SOURCE_CONTRACT,
            required=EvidenceClass(required_class),
        )
        for _blocker, required_class in (
            OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES
        )
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and publisher_port_contract_present
        and publisher_adapter_contract_present
        and evidence_class_matches_blockers
    )
    return {
        "schemaVersion": OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "outbox_broker_source_contract",
        "proofScope": "publisher_port_adapter_and_operator_api_source_contract",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "requiredBlockerEvidenceClasses": dict(
            OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES
        ),
        "outboxBrokerSourceContractValid": proof_valid,
        "aggregateBlockersCleared": OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "publisherPortContractPresent": publisher_port_contract_present,
            "publisherAdapterContractPresent": publisher_adapter_contract_present,
            "evidenceClassMatchesBlockers": evidence_class_matches_blockers,
        },
        "remainingCertificationBlockers": (REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS),
        "sourceContractStatus": "valid" if proof_valid else "invalid",
        "runtimeExecutionObserved": False,
        "externalBrokerConfigured": False,
        "externalBrokerPublicationObserved": False,
        "deploymentObserved": False,
        "productionCertificationGranted": False,
        "externalBrokerPublicationSupported": False,
        "platformMeshEventCertified": False,
        "downstreamConsumersCertified": False,
        "gatewayWorkbenchProofPresent": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def outbox_broker_source_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    expected_values = {
        "schemaVersion": OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": "outbox_broker_source_contract",
        "proofScope": "publisher_port_adapter_and_operator_api_source_contract",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "outboxBrokerSourceContractValid": True,
        "sourceContractStatus": "valid",
    }
    if any(payload.get(key) != value for key, value in expected_values.items()):
        return False
    false_claims = (
        "runtimeExecutionObserved",
        "externalBrokerConfigured",
        "externalBrokerPublicationObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "externalBrokerPublicationSupported",
        "platformMeshEventCertified",
        "downstreamConsumersCertified",
        "gatewayWorkbenchProofPresent",
        "supportedFeaturePromoted",
        "proofClosed",
    )
    if any(payload.get(field_name) is not False for field_name in false_claims):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    required_classes = payload.get("requiredBlockerEvidenceClasses")
    if not isinstance(required_classes, Mapping):
        return False
    if tuple(required_classes.items()) != (
        OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    ):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS
    ):
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
            "publisherPortContractPresent",
            "publisherAdapterContractPresent",
            "evidenceClassMatchesBlockers",
        )
    )


def _python_class_declares_methods(
    path: Path,
    *,
    class_name: str,
    required_methods: tuple[str, ...],
) -> bool:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return False
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        declared_methods = {
            child.name
            for child in node.body
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        return set(required_methods) <= declared_methods
    return False
