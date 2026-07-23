from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from app.application.downstream_realization.advise_intake_runtime_execution import (
    advise_intake_runtime_execution_is_valid,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    manage_intake_runtime_execution_is_valid,
)
from app.application.downstream_realization.intake_runtime_execution_common import (
    non_proof_claims_are_retained as shared_non_proof_claims_are_retained,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.report.materialization_runtime_execution import (
    report_materialization_runtime_execution_is_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.domain.proof_evidence import EvidenceClass

OUTBOX_CONSUMER_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_EXECUTION_PROOF"
OUTBOX_CONSUMER_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.outbox-consumer-runtime-execution.v1"
OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED = ("downstream_consumer_runtime_proof_missing",)
REMAINING_OUTBOX_CONSUMER_RUNTIME_BLOCKERS = (
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS = (
    "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json",
    "src/app/application/outbox/consumer_runtime.py",
    "scripts/outbox/generate_consumer_runtime_execution.py",
    "scripts/outbox/consumer_runtime_execution_gate.py",
    "tests/unit/outbox/test_outbox_consumer_runtime_execution.py",
    "tests/unit/outbox/test_outbox_consumer_runtime_readiness.py",
    "make outbox-consumer-runtime-execution-proof-gate",
    "GET /api/v1/outbox-delivery/readiness",
    "GET /api/v1/implementation-proof/readiness",
)
REQUIRED_DOMAIN_CONSUMERS = ("lotus-advise", "lotus-manage", "lotus-report")

_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "runtimeProofValid",
        "consumerCoverage",
        "consumerRuntimeEvidence",
        "runtimeChecks",
        "evidenceRefs",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "nonProofClaims",
    }
)
_CONSUMER_EVIDENCE_FIELDS = frozenset(
    {
        "consumerRepository",
        "proofType",
        "proofScope",
        "proofRef",
        "proofDigest",
        "evidenceClass",
        "runtimeMode",
        "generatedAtUtc",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
    }
)
_RUNTIME_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "adviseConsumerRuntimeObserved",
        "manageConsumerRuntimeObserved",
        "reportConsumerRuntimeObserved",
        "consumerProofRefsBound",
        "consumerProofDigestsBound",
        "domainConsumerCoverageComplete",
        "gatewayWorkbenchProofSeparated",
        "platformMeshPublicationProofSeparated",
        "nonProofClaimsRetained",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "gatewayWorkbenchProofPresent",
        "platformMeshEventCertified",
        "supportedFeaturePromoted",
        "productionCertificationGranted",
        "certificationClosed",
    }
)
_EXPECTED_PROOF_TYPE = "outbox_consumer_runtime_execution"
_EXPECTED_PROOF_SCOPE = "advise_manage_report_runtime_receipts_with_gateway_workbench_separated"
_VALIDATORS: Mapping[str, Callable[[Mapping[str, Any]], bool]] = {
    "lotus-advise": advise_intake_runtime_execution_is_valid,
    "lotus-manage": manage_intake_runtime_execution_is_valid,
    "lotus-report": report_materialization_runtime_execution_is_valid,
}


def build_outbox_consumer_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    advise_intake_runtime_execution_proof: Mapping[str, Any],
    advise_intake_runtime_execution_proof_ref: str,
    manage_intake_runtime_execution_proof: Mapping[str, Any],
    manage_intake_runtime_execution_proof_ref: str,
    report_materialization_runtime_execution_proof: Mapping[str, Any],
    report_materialization_runtime_execution_proof_ref: str,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    consumer_evidence = {
        "lotus-advise": _consumer_evidence(
            "lotus-advise",
            advise_intake_runtime_execution_proof,
            advise_intake_runtime_execution_proof_ref,
        ),
        "lotus-manage": _consumer_evidence(
            "lotus-manage",
            manage_intake_runtime_execution_proof,
            manage_intake_runtime_execution_proof_ref,
        ),
        "lotus-report": _consumer_evidence(
            "lotus-report",
            report_materialization_runtime_execution_proof,
            report_materialization_runtime_execution_proof_ref,
        ),
    }
    runtime_checks = {
        "timezoneAwareGeneratedAtUtc": True,
        "adviseConsumerRuntimeObserved": _consumer_payload_is_valid(
            "lotus-advise",
            advise_intake_runtime_execution_proof,
        ),
        "manageConsumerRuntimeObserved": _consumer_payload_is_valid(
            "lotus-manage",
            manage_intake_runtime_execution_proof,
        ),
        "reportConsumerRuntimeObserved": _consumer_payload_is_valid(
            "lotus-report",
            report_materialization_runtime_execution_proof,
        ),
        "consumerProofRefsBound": _consumer_refs_are_bound(consumer_evidence),
        "consumerProofDigestsBound": _consumer_digests_are_bound(consumer_evidence),
        "domainConsumerCoverageComplete": tuple(consumer_evidence) == REQUIRED_DOMAIN_CONSUMERS,
        "gatewayWorkbenchProofSeparated": True,
        "platformMeshPublicationProofSeparated": True,
        "nonProofClaimsRetained": True,
    }
    return {
        "schemaVersion": OUTBOX_CONSUMER_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": all(runtime_checks.values()),
        "consumerCoverage": {
            "domainConsumersCovered": REQUIRED_DOMAIN_CONSUMERS,
            "gatewayWorkbenchRuntimeProofRequiredSeparately": True,
            "platformMeshPublicationProofRequiredSeparately": True,
        },
        "consumerRuntimeEvidence": consumer_evidence,
        "runtimeChecks": runtime_checks,
        "evidenceRefs": OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS,
        "aggregateBlockersSatisfied": OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_OUTBOX_CONSUMER_RUNTIME_BLOCKERS,
        "nonProofClaims": {
            "gatewayWorkbenchProofPresent": False,
            "platformMeshEventCertified": False,
            "supportedFeaturePromoted": False,
            "productionCertificationGranted": False,
            "certificationClosed": False,
        },
    }


def outbox_consumer_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": OUTBOX_CONSUMER_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS:
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != REMAINING_OUTBOX_CONSUMER_RUNTIME_BLOCKERS
    ):
        return False
    if not _consumer_coverage_is_valid(payload.get("consumerCoverage")):
        return False
    if not _consumer_runtime_evidence_is_valid(payload.get("consumerRuntimeEvidence")):
        return False
    if not _runtime_checks_are_valid(payload.get("runtimeChecks")):
        return False
    return _non_proof_claims_are_retained(payload.get("nonProofClaims"))


def _consumer_evidence(
    consumer_repository: str,
    proof: Mapping[str, Any],
    proof_ref: str,
) -> dict[str, Any]:
    return {
        "consumerRepository": consumer_repository,
        "proofType": proof.get("proofType"),
        "proofScope": proof.get("proofScope"),
        "proofRef": proof_ref,
        "proofDigest": _payload_digest(proof),
        "evidenceClass": proof.get("evidenceClass"),
        "runtimeMode": proof.get("runtimeMode"),
        "generatedAtUtc": proof.get("generatedAtUtc"),
        "aggregateBlockersSatisfied": tuple(proof.get("aggregateBlockersSatisfied") or ()),
        "remainingCertificationBlockers": tuple(proof.get("remainingCertificationBlockers") or ()),
    }


def _consumer_payload_is_valid(consumer_repository: str, proof: Mapping[str, Any]) -> bool:
    validator = _VALIDATORS.get(consumer_repository)
    return bool(validator and validator(proof))


def _payload_digest(proof: Mapping[str, Any]) -> str:
    encoded = json.dumps(proof, sort_keys=True, separators=(",", ":"), default=list).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _consumer_refs_are_bound(consumer_evidence: Mapping[str, Mapping[str, Any]]) -> bool:
    refs = tuple(evidence.get("proofRef") for evidence in consumer_evidence.values())
    return all(isinstance(ref, str) and ref.strip() for ref in refs) and len(set(refs)) == len(refs)


def _consumer_digests_are_bound(consumer_evidence: Mapping[str, Mapping[str, Any]]) -> bool:
    return all(
        isinstance(evidence.get("proofDigest"), str)
        and str(evidence["proofDigest"]).startswith("sha256:")
        and len(str(evidence["proofDigest"])) == 71
        for evidence in consumer_evidence.values()
    )


def _consumer_coverage_is_valid(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and tuple(value.get("domainConsumersCovered") or ()) == REQUIRED_DOMAIN_CONSUMERS
        and value.get("gatewayWorkbenchRuntimeProofRequiredSeparately") is True
        and value.get("platformMeshPublicationProofRequiredSeparately") is True
    )


def _consumer_runtime_evidence_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or tuple(value) != REQUIRED_DOMAIN_CONSUMERS:
        return False
    return all(
        _consumer_evidence_is_valid(consumer_repository, value.get(consumer_repository))
        for consumer_repository in REQUIRED_DOMAIN_CONSUMERS
    )


def _consumer_evidence_is_valid(consumer_repository: str, value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _CONSUMER_EVIDENCE_FIELDS:
        return False
    return (
        value.get("consumerRepository") == consumer_repository
        and value.get("evidenceClass") == EvidenceClass.RUNTIME_EXECUTION.value
        and isinstance(value.get("proofType"), str)
        and isinstance(value.get("proofScope"), str)
        and isinstance(value.get("proofRef"), str)
        and bool(str(value["proofRef"]).strip())
        and isinstance(value.get("runtimeMode"), str)
        and is_timezone_aware_datetime_text(value.get("generatedAtUtc"))
        and isinstance(value.get("proofDigest"), str)
        and str(value["proofDigest"]).startswith("sha256:")
        and len(str(value["proofDigest"])) == 71
        and isinstance(value.get("aggregateBlockersSatisfied"), tuple | list)
        and bool(tuple(value.get("aggregateBlockersSatisfied") or ()))
        and isinstance(value.get("remainingCertificationBlockers"), tuple | list)
    )


def _runtime_checks_are_valid(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _RUNTIME_CHECK_FIELDS
        and all(value.get(key) is True for key in _RUNTIME_CHECK_FIELDS)
    )


def _non_proof_claims_are_retained(value: object) -> bool:
    return shared_non_proof_claims_are_retained(
        value,
        expected_fields=_NON_PROOF_CLAIM_FIELDS,
    )
