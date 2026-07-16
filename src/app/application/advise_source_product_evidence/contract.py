from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.advise_source_product_evidence.profiles import (
    ADVISE_SOURCE_PRODUCT_CONTRACT_REF,
    ADVISE_SOURCE_PRODUCT_ID,
    ADVISE_SOURCE_TELEMETRY_CONTRACT_REF,
    AdviseSourceProductProfile,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    load_json_object,
    source_authority_records_are_valid,
    source_authority_records_digest,
)
from app.domain.proof_evidence import (
    EvidenceClass,
    evidence_class_can_clear,
    is_timezone_aware_datetime_text,
)


SCHEMA_VERSION = "lotus-idea.advise-source-product-evidence.v2"
MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV = "LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF"
MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV = (
    "LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF"
)

_PRODUCT_CONTRACT_PATH = "contracts/domain-data-products/lotus-advise-products.v1.json"
_TELEMETRY_CONTRACT_PATH = (
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)
_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "capability",
        "evidenceClass",
        "sourceContractValid",
        "sourceContractBlockersSatisfied",
        "requiredBlockerEvidenceClasses",
        "sourceRepository",
        "sourceProductId",
        "sourceProductContractRef",
        "sourceTelemetryContractRef",
        "sourceAuthority",
        "sourceAuthorityDigest",
        "contractChecks",
        "diagnosticContract",
        "authorityClaims",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "nonProofBoundaries",
    }
)
_CONTRACT_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "producerDeclarationValid",
        "producerApprovesLotusIdeaConsumer",
        "producerTrustTelemetryIdentityValid",
        "producerTrustTelemetryBlockedPosturePreserved",
        "requiredDiagnosticsDefined",
        "ideaAuthorityBoundaryPreserved",
    }
)
_DIAGNOSTIC_CONTRACT_FIELDS = frozenset(
    {
        "diagnosticFamily",
        "requiredDiagnostics",
        "diagnosticsOwnedBy",
        "consumerInterpretation",
    }
)
_AUTHORITY_CLAIM_FIELDS = frozenset(
    {
        "liveAdviseSourceObserved",
        "mandateStateChangeGranted",
        "restrictionClearanceGranted",
        "riskProfileApprovalGranted",
        "suitabilityApprovalGranted",
        "policyApprovalGranted",
        "proposalApprovalGranted",
        "rebalanceAuthorityGranted",
        "orderAuthorityGranted",
        "clientPublicationAuthorityGranted",
        "deploymentCertified",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)


def build_advise_source_product_source_contract(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    profile: AdviseSourceProductProfile,
    advise_root: Path | None = None,
) -> dict[str, Any]:
    source_root = advise_root or repository_root.parent / "lotus-advise"
    product_contract = load_json_object(source_root / _PRODUCT_CONTRACT_PATH)
    telemetry_contract = load_json_object(source_root / _TELEMETRY_CONTRACT_PATH)
    source_authority = build_source_authority_records(_source_authority_sources(source_root))
    source_authority_digest = source_authority_records_digest(source_authority)
    contract_checks = {
        "timezoneAwareGeneratedAtUtc": _timezone_aware(generated_at_utc),
        "sourceAuthorityDigestBound": (
            source_authority_digest is not None
            and all(isinstance(item["sha256"], str) for item in source_authority)
        ),
        "producerDeclarationValid": _producer_declaration_is_valid(product_contract),
        "producerApprovesLotusIdeaConsumer": _producer_approves_lotus_idea(product_contract),
        "producerTrustTelemetryIdentityValid": _telemetry_identity_is_valid(telemetry_contract),
        "producerTrustTelemetryBlockedPosturePreserved": (
            _telemetry_blocked_posture_is_preserved(telemetry_contract)
        ),
        "requiredDiagnosticsDefined": bool(profile.required_diagnostics),
        "ideaAuthorityBoundaryPreserved": True,
    }
    source_contract_valid = all(contract_checks.values())
    required_classes = {
        blocker: EvidenceClass.SOURCE_CONTRACT.value for blocker in profile.blockers_satisfied
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": _format_utc(generated_at_utc),
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        "capability": profile.capability,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": source_contract_valid,
        "sourceContractBlockersSatisfied": list(profile.blockers_satisfied),
        "requiredBlockerEvidenceClasses": required_classes,
        "sourceRepository": "lotus-advise",
        "sourceProductId": ADVISE_SOURCE_PRODUCT_ID,
        "sourceProductContractRef": ADVISE_SOURCE_PRODUCT_CONTRACT_REF,
        "sourceTelemetryContractRef": ADVISE_SOURCE_TELEMETRY_CONTRACT_REF,
        "sourceAuthority": source_authority,
        "sourceAuthorityDigest": source_authority_digest,
        "contractChecks": contract_checks,
        "diagnosticContract": {
            "diagnosticFamily": profile.diagnostic_family,
            "requiredDiagnostics": list(profile.required_diagnostics),
            "diagnosticsOwnedBy": "lotus-advise",
            "consumerInterpretation": "opportunity_review_posture_only",
        },
        "authorityClaims": {field: False for field in sorted(_AUTHORITY_CLAIM_FIELDS)},
        "remainingCertificationBlockers": list(profile.remaining_blockers),
        "evidenceRefs": list(profile.evidence_refs),
        "nonProofBoundaries": list(profile.non_proof_boundaries),
    }


def advise_source_product_source_contract_is_valid(
    payload: Mapping[str, Any],
    *,
    profile: AdviseSourceProductProfile,
) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        "capability": profile.capability,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": True,
        "sourceContractBlockersSatisfied": list(profile.blockers_satisfied),
        "requiredBlockerEvidenceClasses": {
            blocker: EvidenceClass.SOURCE_CONTRACT.value for blocker in profile.blockers_satisfied
        },
        "sourceRepository": "lotus-advise",
        "sourceProductId": ADVISE_SOURCE_PRODUCT_ID,
        "sourceProductContractRef": ADVISE_SOURCE_PRODUCT_CONTRACT_REF,
        "sourceTelemetryContractRef": ADVISE_SOURCE_TELEMETRY_CONTRACT_REF,
        "remainingCertificationBlockers": list(profile.remaining_blockers),
        "evidenceRefs": list(profile.evidence_refs),
        "nonProofBoundaries": list(profile.non_proof_boundaries),
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if not _source_authority_is_valid(payload.get("sourceAuthority")):
        return False
    if payload.get("sourceAuthorityDigest") != source_authority_records_digest(
        payload.get("sourceAuthority")
    ):
        return False
    checks = payload.get("contractChecks")
    if (
        not isinstance(checks, Mapping)
        or set(checks) != _CONTRACT_CHECK_FIELDS
        or any(checks.get(field) is not True for field in _CONTRACT_CHECK_FIELDS)
    ):
        return False
    diagnostic = payload.get("diagnosticContract")
    if not isinstance(diagnostic, Mapping) or set(diagnostic) != _DIAGNOSTIC_CONTRACT_FIELDS:
        return False
    if diagnostic != {
        "diagnosticFamily": profile.diagnostic_family,
        "requiredDiagnostics": list(profile.required_diagnostics),
        "diagnosticsOwnedBy": "lotus-advise",
        "consumerInterpretation": "opportunity_review_posture_only",
    }:
        return False
    claims = payload.get("authorityClaims")
    if (
        not isinstance(claims, Mapping)
        or set(claims) != _AUTHORITY_CLAIM_FIELDS
        or any(claims.get(field) is not False for field in _AUTHORITY_CLAIM_FIELDS)
    ):
        return False
    return all(
        evidence_class_can_clear(
            actual=EvidenceClass.SOURCE_CONTRACT,
            required=EvidenceClass(required_class),
        )
        for required_class in payload["requiredBlockerEvidenceClasses"].values()
    )


def _source_authority_sources(root: Path) -> tuple[SourceAuthoritySource, ...]:
    return (
        SourceAuthoritySource(
            repository="lotus-advise",
            ref=_PRODUCT_CONTRACT_PATH,
            path=root / _PRODUCT_CONTRACT_PATH,
        ),
        SourceAuthoritySource(
            repository="lotus-advise",
            ref=_TELEMETRY_CONTRACT_PATH,
            path=root / _TELEMETRY_CONTRACT_PATH,
        ),
    )


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=_source_authority_sources(Path()),
    )


def _producer_declaration_is_valid(payload: Mapping[str, Any] | None) -> bool:
    product = _producer_product(payload)
    if product is None:
        return False
    required_metadata = product.get("required_trust_metadata")
    return (
        product.get("product_name") == "AdvisoryPolicyEvaluationRecord"
        and product.get("product_version") == "v1"
        and product.get("owner_repository") == "lotus-advise"
        and product.get("authoritative_domain") == "advisory_workflow"
        and product.get("lifecycle_status") == "active"
        and isinstance(required_metadata, list)
        and {
            "product_name",
            "product_version",
            "generated_at",
            "content_hash",
            "correlation_id",
        }.issubset(required_metadata)
    )


def _producer_approves_lotus_idea(payload: Mapping[str, Any] | None) -> bool:
    product = _producer_product(payload)
    return bool(
        product
        and isinstance(product.get("approved_consumers"), list)
        and "lotus-idea" in product["approved_consumers"]
    )


def _producer_product(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if payload is None or not isinstance(payload.get("products"), list):
        return None
    for product in payload["products"]:
        if (
            isinstance(product, Mapping)
            and product.get("product_name") == "AdvisoryPolicyEvaluationRecord"
        ):
            return product
    return None


def _telemetry_identity_is_valid(payload: Mapping[str, Any] | None) -> bool:
    return bool(
        payload
        and payload.get("contract_id") == "lotus-domain-product-trust-telemetry-snapshot"
        and payload.get("product_id") == ADVISE_SOURCE_PRODUCT_ID
        and payload.get("producer_repository") == "lotus-advise"
        and payload.get("source_repository") == "lotus-advise"
        and payload.get("product_name") == "AdvisoryPolicyEvaluationRecord"
        and payload.get("product_version") == "v1"
    )


def _telemetry_blocked_posture_is_preserved(payload: Mapping[str, Any] | None) -> bool:
    if payload is None:
        return False
    blocking = payload.get("blocking")
    return bool(
        isinstance(blocking, Mapping)
        and blocking.get("blocked") is True
        and isinstance(blocking.get("blocked_reason"), str)
        and blocking["blocked_reason"].strip()
        and isinstance(blocking.get("blocked_summary"), str)
        and blocking["blocked_summary"].strip()
    )


def _timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
