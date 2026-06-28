from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_ENV = "LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF"
MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.mandate-restriction.source-product-proof.v1"
)

MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED = (
    "opportunity_archetype_typed_restriction_source_product_missing",
)

ADVISE_RESTRICTION_SOURCE_PRODUCT_ID = "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
ADVISE_RESTRICTION_SOURCE_PRODUCT_CONTRACT_REF = (
    "lotus-advise://contracts/domain-data-products/"
    "lotus-advise-products.v1.json#AdvisoryPolicyEvaluationRecord"
)
ADVISE_RESTRICTION_TRUST_TELEMETRY_CONTRACT_REF = (
    "lotus-advise://contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)

REQUIRED_RESTRICTION_DIAGNOSTICS = (
    "mandate_restriction_review_required",
    "product_restriction_review_required",
    "country_restriction_review_required",
    "suitability_policy_actionability_blocked",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_live_restriction_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MANDATE_RESTRICTION_SOURCE_PRODUCT_EVIDENCE_REFS = (
    "scripts/generate_mandate_restriction_source_product_proof.py",
    "src/app/application/mandate_restriction_source_product_proof.py",
    "src/app/domain/mandate_restriction_signal.py",
    "src/app/application/mandate_restriction_signal.py",
    "src/app/ports/advise_sources.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-17-implementation-proof-and-live-validation.md",
)

NON_PROOF_BOUNDARIES = (
    "no_live_advise_source_proof",
    "no_mandate_state_change",
    "no_restriction_clearance",
    "no_suitability_approval",
    "no_policy_approval",
    "no_proposal_approval",
    "no_rebalance_authority",
    "no_order_authority",
    "no_client_publication_approval",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_supported_feature_promotion",
)


def build_mandate_restriction_source_product_proof_payload(
    *,
    generated_at_utc: datetime,
    source_product_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    summary = source_product_summary or {}
    diagnostics = tuple(
        dict.fromkeys(
            _text_sequence(
                summary.get("requiredRestrictionDiagnostics"),
                default=REQUIRED_RESTRICTION_DIAGNOSTICS,
            )
        )
    )
    proof_blockers = _proof_blockers(summary=summary, diagnostics=diagnostics)
    return {
        "schemaVersion": MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "mandate-restriction-source-product",
        "proofScope": "opportunity-archetype.mandate-restriction-review",
        "sourceAuthority": _text(summary.get("sourceAuthority"), "lotus-advise"),
        "sourceProductId": _text(
            summary.get("sourceProductId"),
            ADVISE_RESTRICTION_SOURCE_PRODUCT_ID,
        ),
        "sourceProductContractRef": _text(
            summary.get("sourceProductContractRef"),
            ADVISE_RESTRICTION_SOURCE_PRODUCT_CONTRACT_REF,
        ),
        "sourceTelemetryContractRef": _text(
            summary.get("sourceTelemetryContractRef"),
            ADVISE_RESTRICTION_TRUST_TELEMETRY_CONTRACT_REF,
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "typedRestrictionDiagnosticContractReady": bool(
            summary.get("typedRestrictionDiagnosticContractReady", True)
        ),
        "requiredRestrictionDiagnostics": list(diagnostics),
        "restrictionDiagnosticsOwnedByAdvise": bool(
            summary.get("restrictionDiagnosticsOwnedByAdvise", True)
        ),
        "lotusIdeaDoesNotClearRestrictions": bool(
            summary.get("lotusIdeaDoesNotClearRestrictions", True)
        ),
        "mandateStateAuthorityGranted": False,
        "restrictionClearanceAuthorityGranted": False,
        "suitabilityAuthorityGranted": False,
        "policyApprovalGranted": False,
        "proposalApprovalGranted": False,
        "rebalanceAuthorityGranted": False,
        "orderAuthorityGranted": False,
        "liveAdviseSourceProofCertified": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MANDATE_RESTRICTION_SOURCE_PRODUCT_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def mandate_restriction_source_product_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "mandate-restriction-source-product"
        and payload.get("proofScope") == "opportunity-archetype.mandate-restriction-review"
        and payload.get("sourceAuthority") == "lotus-advise"
        and payload.get("sourceProductId") == ADVISE_RESTRICTION_SOURCE_PRODUCT_ID
        and payload.get("sourceProductContractRef")
        == ADVISE_RESTRICTION_SOURCE_PRODUCT_CONTRACT_REF
        and payload.get("sourceTelemetryContractRef")
        == ADVISE_RESTRICTION_TRUST_TELEMETRY_CONTRACT_REF
        and payload.get("typedRestrictionDiagnosticContractReady") is True
        and _has_required_diagnostics(payload.get("requiredRestrictionDiagnostics"))
        and payload.get("restrictionDiagnosticsOwnedByAdvise") is True
        and payload.get("lotusIdeaDoesNotClearRestrictions") is True
        and payload.get("mandateStateAuthorityGranted") is False
        and payload.get("restrictionClearanceAuthorityGranted") is False
        and payload.get("suitabilityAuthorityGranted") is False
        and payload.get("policyApprovalGranted") is False
        and payload.get("proposalApprovalGranted") is False
        and payload.get("rebalanceAuthorityGranted") is False
        and payload.get("orderAuthorityGranted") is False
        and payload.get("liveAdviseSourceProofCertified") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and not _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED
        and all(
            blocker in tuple(payload.get("remainingCertificationBlockers", ()))
            for blocker in REMAINING_CERTIFICATION_BLOCKERS
        )
    )


def _proof_blockers(*, summary: Mapping[str, Any], diagnostics: tuple[str, ...]) -> list[str]:
    blockers: list[str] = []
    if _text(summary.get("sourceAuthority"), "lotus-advise") != "lotus-advise":
        blockers.append("advise_restriction_source_authority_mismatch")
    if _text(summary.get("sourceProductId"), ADVISE_RESTRICTION_SOURCE_PRODUCT_ID) != (
        ADVISE_RESTRICTION_SOURCE_PRODUCT_ID
    ):
        blockers.append("advise_restriction_source_product_mismatch")
    if (
        _text(
            summary.get("sourceProductContractRef"),
            ADVISE_RESTRICTION_SOURCE_PRODUCT_CONTRACT_REF,
        )
        != ADVISE_RESTRICTION_SOURCE_PRODUCT_CONTRACT_REF
    ):
        blockers.append("advise_restriction_source_product_contract_missing")
    if (
        _text(
            summary.get("sourceTelemetryContractRef"),
            ADVISE_RESTRICTION_TRUST_TELEMETRY_CONTRACT_REF,
        )
        != ADVISE_RESTRICTION_TRUST_TELEMETRY_CONTRACT_REF
    ):
        blockers.append("advise_restriction_trust_telemetry_contract_missing")
    if not bool(summary.get("typedRestrictionDiagnosticContractReady", True)):
        blockers.append("advise_restriction_diagnostic_contract_not_ready")
    if not _has_required_diagnostics(diagnostics):
        blockers.append("advise_restriction_required_diagnostics_missing")
    if not bool(summary.get("restrictionDiagnosticsOwnedByAdvise", True)):
        blockers.append("advise_restriction_diagnostics_not_advise_owned")
    if not bool(summary.get("lotusIdeaDoesNotClearRestrictions", True)):
        blockers.append("lotus_idea_restriction_authority_boundary_missing")
    return list(dict.fromkeys(blockers))


def _has_required_diagnostics(value: object) -> bool:
    return set(REQUIRED_RESTRICTION_DIAGNOSTICS).issubset(
        {diagnostic.strip().lower() for diagnostic in _text_sequence(value)}
    )


def _text_sequence(
    value: object,
    *,
    default: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
