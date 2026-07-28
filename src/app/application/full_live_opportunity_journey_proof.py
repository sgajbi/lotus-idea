from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.workbench.runtime_execution import (
    GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED,
    validate_gateway_workbench_runtime_execution_proof,
)
from app.domain.proof_evidence import EvidenceClass


FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_ENV = "LOTUS_IDEA_FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF"
FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_SCHEMA_VERSION = (
    "lotus-idea.full-live-opportunity-journey-proof.v1"
)

REQUIRED_JOURNEY_CAPABILITY_IDS = (
    "source-ingestion",
    "advisor-review-queue",
    "workbench-product-proof",
    "downstream-realization",
    "outbox-delivery",
    "data-mesh-certification",
    "runtime-trust-telemetry-preview",
    "supported-feature-promotion",
)

REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS = (
    "src/app/application/full_live_opportunity_journey_proof.py",
    "scripts/generate_full_live_opportunity_journey_proof.py",
    "scripts/full_live_opportunity_journey_proof_gate.py",
    "src/app/application/implementation_proof_readiness.py",
    "src/app/application/workbench/runtime_execution.py",
    (
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-17-implementation-proof-and-live-validation.md"
    ),
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Supported-Features.md",
    "wiki/Validation-and-CI.md",
    "make full-live-opportunity-journey-proof-gate",
)

REQUIRED_FULL_LIVE_JOURNEY_NON_CLAIMS = (
    "production_identity_provider",
    "client_publication_authority",
    "suitability_or_execution_authority",
    "data_product_certification",
    "supported_feature_promotion",
    "full_demo_readiness",
)

EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "rfc",
        "sliceIds",
        "trackingIssues",
        "proofType",
        "proofScope",
        "evidenceClass",
        "aggregateJourneyProofValid",
        "fullLiveJourneyCertified",
        "canonicalPortfolioId",
        "canonicalBenchmarkCode",
        "implementationProofReadinessDigest",
        "gatewayWorkbenchRuntimeExecutionDigest",
        "evidenceRefs",
        "journeyCapabilityCoverage",
        "proofChecks",
        "aggregateBlockersCleared",
        "remainingCertificationBlockers",
        "nonProofClaims",
        "aggregateProofProvenance",
        "productionIdentityImplemented",
        "clientPublicationAuthorized",
        "suitabilityOrExecutionAuthorized",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "fullDemoReadinessCertified",
        "proofClosed",
    }
)


def build_full_live_opportunity_journey_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    implementation_proof_readiness: Mapping[str, Any],
    implementation_proof_readiness_ref: str,
    gateway_workbench_runtime_execution_proof: Mapping[str, Any] | None = None,
    gateway_workbench_runtime_execution_proof_ref: str | None = None,
) -> dict[str, Any]:
    readiness_blockers = _readiness_blockers(implementation_proof_readiness)
    gateway_workbench_runtime_valid = gateway_workbench_runtime_execution_proof is not None and (
        not validate_gateway_workbench_runtime_execution_proof(
            gateway_workbench_runtime_execution_proof
        )
    )
    gateway_runtime_digest = (
        _digest_mapping(gateway_workbench_runtime_execution_proof)
        if gateway_workbench_runtime_execution_proof
        else None
    )
    evidence_refs = _evidence_refs(
        implementation_proof_readiness_ref=implementation_proof_readiness_ref,
        gateway_workbench_runtime_execution_proof_ref=(
            gateway_workbench_runtime_execution_proof_ref
            if gateway_workbench_runtime_valid
            else None
        ),
    )
    proof_checks = {
        "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None,
        "localEvidencePresent": _local_evidence_present(repository_root),
        "makeTargetEvidencePresent": _local_make_targets_present(repository_root),
        "implementationProofReadinessValid": _implementation_proof_readiness_valid(
            implementation_proof_readiness
        ),
        "requiredJourneyCapabilitiesPresent": _required_capabilities_present(
            implementation_proof_readiness
        ),
        "gatewayWorkbenchRuntimeEvidenceValid": gateway_workbench_runtime_valid,
        "remainingBlockersPreserved": bool(readiness_blockers),
        "supportedFeaturesRemainUnpromoted": (
            implementation_proof_readiness.get("supportedFeaturesPromoted") is False
        ),
    }
    aggregate_valid = all(value is True for value in proof_checks.values())
    full_live_certified = (
        aggregate_valid
        and implementation_proof_readiness.get("certificationReady") is True
        and not readiness_blockers
    )
    return {
        "schemaVersion": FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "rfc": "RFC-0002",
        "sliceIds": ["RFC-0002/slice-17"],
        "trackingIssues": [
            "sgajbi/lotus-idea#680",
            "sgajbi/lotus-idea#699",
        ],
        "proofType": "full_live_opportunity_journey",
        "proofScope": "api_gateway_workbench_downstream_handoff_aggregate_journey",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "aggregateJourneyProofValid": aggregate_valid,
        "fullLiveJourneyCertified": full_live_certified,
        "canonicalPortfolioId": "PB_SG_GLOBAL_BAL_001",
        "canonicalBenchmarkCode": "BMK_PB_GLOBAL_BALANCED_60_40",
        "implementationProofReadinessDigest": _digest_mapping(implementation_proof_readiness),
        "gatewayWorkbenchRuntimeExecutionDigest": gateway_runtime_digest,
        "evidenceRefs": evidence_refs,
        "journeyCapabilityCoverage": _journey_capability_coverage(implementation_proof_readiness),
        "proofChecks": proof_checks,
        "aggregateBlockersCleared": list(GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED)
        if gateway_workbench_runtime_valid
        else [],
        "remainingCertificationBlockers": list(readiness_blockers),
        "nonProofClaims": list(REQUIRED_FULL_LIVE_JOURNEY_NON_CLAIMS),
        "productionIdentityImplemented": False,
        "clientPublicationAuthorized": False,
        "suitabilityOrExecutionAuthorized": False,
        "dataProductCertified": False,
        "supportedFeaturePromoted": False,
        "fullDemoReadinessCertified": False,
        "proofClosed": False,
    }


def full_live_opportunity_journey_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return not validate_full_live_opportunity_journey_proof(payload)


def validate_full_live_opportunity_journey_proof(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_top_level_claims(payload, errors)
    _validate_exact_sequence(
        payload,
        "sliceIds",
        ("RFC-0002/slice-17",),
        errors,
    )
    _validate_exact_sequence(
        payload,
        "trackingIssues",
        ("sgajbi/lotus-idea#680", "sgajbi/lotus-idea#699"),
        errors,
    )
    _validate_exact_sequence(
        payload,
        "nonProofClaims",
        REQUIRED_FULL_LIVE_JOURNEY_NON_CLAIMS,
        errors,
    )
    _validate_journey_capability_coverage(payload, errors)
    _validate_proof_checks(payload, errors)
    _validate_blocker_posture(payload, errors)
    return errors


def _validate_top_level_claims(payload: Mapping[str, Any], errors: list[str]) -> None:
    unknown_keys = sorted(set(payload) - EXPECTED_TOP_LEVEL_KEYS)
    if unknown_keys:
        errors.append(f"unknown full-live journey proof fields: {unknown_keys}")
    if payload.get("schemaVersion") != FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_SCHEMA_VERSION:
        errors.append("schemaVersion must be the full-live opportunity journey schema")
    if payload.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        errors.append("generatedAtUtc must be timezone-aware")
    if payload.get("rfc") != "RFC-0002":
        errors.append("rfc must be RFC-0002")
    if payload.get("proofType") != "full_live_opportunity_journey":
        errors.append("proofType must be full_live_opportunity_journey")
    if payload.get("proofScope") != "api_gateway_workbench_downstream_handoff_aggregate_journey":
        errors.append("proofScope must be the governed aggregate journey boundary")
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        errors.append("evidenceClass must be runtime_execution")
    if payload.get("aggregateJourneyProofValid") is not True:
        errors.append("aggregateJourneyProofValid must be true")
    if payload.get("canonicalPortfolioId") != "PB_SG_GLOBAL_BAL_001":
        errors.append("canonicalPortfolioId must be PB_SG_GLOBAL_BAL_001")
    if payload.get("canonicalBenchmarkCode") != "BMK_PB_GLOBAL_BALANCED_60_40":
        errors.append("canonicalBenchmarkCode must be BMK_PB_GLOBAL_BALANCED_60_40")
    if not _is_sha256_digest(payload.get("implementationProofReadinessDigest")):
        errors.append("implementationProofReadinessDigest must be a sha256 digest")
    gateway_digest = payload.get("gatewayWorkbenchRuntimeExecutionDigest")
    if gateway_digest is not None and not _is_sha256_digest(gateway_digest):
        errors.append("gatewayWorkbenchRuntimeExecutionDigest must be null or a sha256 digest")
    if not _non_empty_text_array(payload.get("evidenceRefs")):
        errors.append("evidenceRefs must contain source-safe evidence refs")
    for field_name in (
        "productionIdentityImplemented",
        "clientPublicationAuthorized",
        "suitabilityOrExecutionAuthorized",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "fullDemoReadinessCertified",
        "proofClosed",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"{field_name} must be false")


def _validate_proof_checks(payload: Mapping[str, Any], errors: list[str]) -> None:
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        errors.append("proofChecks must be an object")
        return
    required_checks = (
        "timezoneAwareGeneratedAtUtc",
        "localEvidencePresent",
        "makeTargetEvidencePresent",
        "implementationProofReadinessValid",
        "requiredJourneyCapabilitiesPresent",
        "gatewayWorkbenchRuntimeEvidenceValid",
        "remainingBlockersPreserved",
        "supportedFeaturesRemainUnpromoted",
    )
    unknown_checks = sorted(set(proof_checks) - set(required_checks))
    if unknown_checks:
        errors.append(f"unknown proofChecks fields: {unknown_checks}")
    for check in required_checks:
        if proof_checks.get(check) is not True:
            errors.append(f"proofChecks.{check} must be true")


def _validate_journey_capability_coverage(
    payload: Mapping[str, Any],
    errors: list[str],
) -> None:
    coverage = payload.get("journeyCapabilityCoverage")
    if not isinstance(coverage, list):
        errors.append("journeyCapabilityCoverage must be a JSON array")
        return
    observed_ids: list[str] = []
    for item in coverage:
        if not isinstance(item, Mapping):
            errors.append("journeyCapabilityCoverage entries must be objects")
            return
        capability_id = item.get("capabilityId")
        if not isinstance(capability_id, str):
            errors.append("journeyCapabilityCoverage capabilityId must be text")
            return
        observed_ids.append(capability_id)
        if item.get("supportedFeaturePromoted") is not False:
            errors.append(f"{capability_id} must not be promoted as a supported feature")
        blockers = item.get("blockers")
        if not isinstance(blockers, list):
            errors.append(f"{capability_id} blockers must be a JSON array")
    if tuple(observed_ids) != REQUIRED_JOURNEY_CAPABILITY_IDS:
        errors.append("journeyCapabilityCoverage must match the required Slice 17 legs")


def _validate_blocker_posture(payload: Mapping[str, Any], errors: list[str]) -> None:
    blockers = payload.get("remainingCertificationBlockers")
    if not isinstance(blockers, list) or not blockers:
        errors.append("remainingCertificationBlockers must preserve unresolved blockers")
    if payload.get("fullLiveJourneyCertified") is not False:
        errors.append("fullLiveJourneyCertified must remain false while blockers remain")
    cleared = payload.get("aggregateBlockersCleared")
    if not isinstance(cleared, list):
        errors.append("aggregateBlockersCleared must be a JSON array")
        return
    if tuple(cleared) not in ((), GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED):
        errors.append("aggregateBlockersCleared may clear only the Gateway/Workbench BFF proof")


def _implementation_proof_readiness_valid(snapshot: Mapping[str, Any]) -> bool:
    return (
        snapshot.get("repository") == "lotus-idea"
        and snapshot.get("readinessStatus") in {"blocked", "ready"}
        and snapshot.get("supportabilityStatus") in {"not_certified", "supported"}
        and isinstance(snapshot.get("certificationReady"), bool)
        and isinstance(snapshot.get("capabilities"), Sequence)
        and not isinstance(snapshot.get("capabilities"), (str, bytes))
    )


def _required_capabilities_present(snapshot: Mapping[str, Any]) -> bool:
    capabilities = snapshot.get("capabilities")
    if not isinstance(capabilities, Sequence) or isinstance(capabilities, (str, bytes)):
        return False
    observed = {
        capability.get("capabilityId")
        for capability in capabilities
        if isinstance(capability, Mapping)
    }
    return all(capability_id in observed for capability_id in REQUIRED_JOURNEY_CAPABILITY_IDS)


def _journey_capability_coverage(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    capabilities = snapshot.get("capabilities")
    if not isinstance(capabilities, Sequence) or isinstance(capabilities, (str, bytes)):
        return []
    by_id = {
        capability.get("capabilityId"): capability
        for capability in capabilities
        if isinstance(capability, Mapping)
    }
    coverage: list[dict[str, Any]] = []
    for capability_id in REQUIRED_JOURNEY_CAPABILITY_IDS:
        capability = by_id.get(capability_id, {})
        blockers = capability.get("blockers")
        coverage.append(
            {
                "capabilityId": capability_id,
                "readinessStatus": capability.get("readinessStatus", "missing"),
                "supportabilityStatus": capability.get("supportabilityStatus", "missing"),
                "supportedFeaturePromoted": capability.get("supportedFeaturePromoted") is True,
                "blockers": list(blockers) if isinstance(blockers, list) else [],
            }
        )
    return coverage


def _readiness_blockers(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    blockers = snapshot.get("overallBlockers")
    if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes)):
        return ()
    return tuple(str(blocker) for blocker in blockers if isinstance(blocker, str) and blocker)


def _evidence_refs(
    *,
    implementation_proof_readiness_ref: str,
    gateway_workbench_runtime_execution_proof_ref: str | None,
) -> list[str]:
    refs = [implementation_proof_readiness_ref]
    if gateway_workbench_runtime_execution_proof_ref:
        refs.append(gateway_workbench_runtime_execution_proof_ref)
    return refs


def _validate_exact_sequence(
    payload: Mapping[str, Any],
    field_name: str,
    expected: Sequence[object],
    errors: list[str],
) -> None:
    value = payload.get(field_name)
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a JSON array")
        return
    if tuple(value) != tuple(expected):
        errors.append(f"{field_name} must match the governed full-live journey contract")


def _local_evidence_present(repository_root: Path) -> bool:
    return required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS,
        non_file_ref_prefixes=("make ",),
    )


def _local_make_targets_present(repository_root: Path) -> bool:
    return required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS,
    )


def _digest_mapping(payload: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{hashlib.sha256(rendered.encode('utf-8')).hexdigest()}"


def _is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _non_empty_text_array(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )
