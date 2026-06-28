from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_ENV = (
    "LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF"
)
MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.missing-risk-profile.source-product-proof.v1"
)

MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED = (
    "opportunity_archetype_typed_advise_risk_profile_source_product_missing",
)

ADVISE_RISK_PROFILE_SOURCE_PRODUCT_ID = "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
ADVISE_RISK_PROFILE_SOURCE_PRODUCT_CONTRACT_REF = (
    "lotus-advise://contracts/domain-data-products/"
    "lotus-advise-products.v1.json#AdvisoryPolicyEvaluationRecord"
)
ADVISE_RISK_PROFILE_TRUST_TELEMETRY_CONTRACT_REF = (
    "lotus-advise://contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)

REQUIRED_RISK_PROFILE_DIAGNOSTICS = (
    "risk_profile_missing",
    "risk_profile_stale",
    "risk_profile_expired",
    "risk_profile_review_due",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_advise_risk_profile_live_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MISSING_RISK_PROFILE_SOURCE_PRODUCT_EVIDENCE_REFS = (
    "scripts/generate_missing_risk_profile_source_product_proof.py",
    "src/app/application/missing_risk_profile_source_product_proof.py",
    "src/app/domain/missing_risk_profile_signal.py",
    "src/app/application/missing_risk_profile_signal.py",
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
    "no_risk_profile_approval",
    "no_suitability_approval",
    "no_policy_approval",
    "no_proposal_approval",
    "no_client_publication_approval",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_supported_feature_promotion",
)


def build_missing_risk_profile_source_product_proof_payload(
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
                summary.get("requiredRiskProfileDiagnostics"),
                default=REQUIRED_RISK_PROFILE_DIAGNOSTICS,
            )
        )
    )
    proof_blockers = _proof_blockers(summary=summary, diagnostics=diagnostics)
    return {
        "schemaVersion": MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "missing-risk-profile-source-product",
        "proofScope": "opportunity-archetype.missing-risk-profile-review",
        "sourceAuthority": _text(summary.get("sourceAuthority"), "lotus-advise"),
        "sourceProductId": _text(
            summary.get("sourceProductId"),
            ADVISE_RISK_PROFILE_SOURCE_PRODUCT_ID,
        ),
        "sourceProductContractRef": _text(
            summary.get("sourceProductContractRef"),
            ADVISE_RISK_PROFILE_SOURCE_PRODUCT_CONTRACT_REF,
        ),
        "sourceTelemetryContractRef": _text(
            summary.get("sourceTelemetryContractRef"),
            ADVISE_RISK_PROFILE_TRUST_TELEMETRY_CONTRACT_REF,
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "typedRiskProfileDiagnosticContractReady": bool(
            summary.get("typedRiskProfileDiagnosticContractReady", True)
        ),
        "requiredRiskProfileDiagnostics": list(diagnostics),
        "riskProfileDiagnosticsOwnedByAdvise": bool(
            summary.get("riskProfileDiagnosticsOwnedByAdvise", True)
        ),
        "lotusIdeaDoesNotApproveRiskProfile": bool(
            summary.get("lotusIdeaDoesNotApproveRiskProfile", True)
        ),
        "riskProfileAuthorityGranted": False,
        "suitabilityAuthorityGranted": False,
        "policyApprovalGranted": False,
        "proposalApprovalGranted": False,
        "liveAdviseSourceProofCertified": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MISSING_RISK_PROFILE_SOURCE_PRODUCT_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def missing_risk_profile_source_product_proof_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    return (
        payload.get("schemaVersion") == MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "missing-risk-profile-source-product"
        and payload.get("proofScope") == "opportunity-archetype.missing-risk-profile-review"
        and payload.get("sourceAuthority") == "lotus-advise"
        and payload.get("sourceProductId") == ADVISE_RISK_PROFILE_SOURCE_PRODUCT_ID
        and payload.get("sourceProductContractRef")
        == ADVISE_RISK_PROFILE_SOURCE_PRODUCT_CONTRACT_REF
        and payload.get("sourceTelemetryContractRef")
        == ADVISE_RISK_PROFILE_TRUST_TELEMETRY_CONTRACT_REF
        and payload.get("typedRiskProfileDiagnosticContractReady") is True
        and _has_required_diagnostics(payload.get("requiredRiskProfileDiagnostics"))
        and payload.get("riskProfileDiagnosticsOwnedByAdvise") is True
        and payload.get("lotusIdeaDoesNotApproveRiskProfile") is True
        and payload.get("riskProfileAuthorityGranted") is False
        and payload.get("suitabilityAuthorityGranted") is False
        and payload.get("policyApprovalGranted") is False
        and payload.get("proposalApprovalGranted") is False
        and payload.get("liveAdviseSourceProofCertified") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and not _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED
        and all(
            blocker in tuple(payload.get("remainingCertificationBlockers", ()))
            for blocker in REMAINING_CERTIFICATION_BLOCKERS
        )
    )


def _proof_blockers(*, summary: Mapping[str, Any], diagnostics: tuple[str, ...]) -> list[str]:
    blockers: list[str] = []
    if _text(summary.get("sourceAuthority"), "lotus-advise") != "lotus-advise":
        blockers.append("advise_risk_profile_source_authority_mismatch")
    if _text(summary.get("sourceProductId"), ADVISE_RISK_PROFILE_SOURCE_PRODUCT_ID) != (
        ADVISE_RISK_PROFILE_SOURCE_PRODUCT_ID
    ):
        blockers.append("advise_risk_profile_source_product_mismatch")
    if (
        _text(
            summary.get("sourceProductContractRef"),
            ADVISE_RISK_PROFILE_SOURCE_PRODUCT_CONTRACT_REF,
        )
        != ADVISE_RISK_PROFILE_SOURCE_PRODUCT_CONTRACT_REF
    ):
        blockers.append("advise_risk_profile_source_product_contract_missing")
    if (
        _text(
            summary.get("sourceTelemetryContractRef"),
            ADVISE_RISK_PROFILE_TRUST_TELEMETRY_CONTRACT_REF,
        )
        != ADVISE_RISK_PROFILE_TRUST_TELEMETRY_CONTRACT_REF
    ):
        blockers.append("advise_risk_profile_trust_telemetry_contract_missing")
    if not bool(summary.get("typedRiskProfileDiagnosticContractReady", True)):
        blockers.append("advise_risk_profile_diagnostic_contract_not_ready")
    if not _has_required_diagnostics(diagnostics):
        blockers.append("advise_risk_profile_required_diagnostics_missing")
    if not bool(summary.get("riskProfileDiagnosticsOwnedByAdvise", True)):
        blockers.append("advise_risk_profile_diagnostics_not_advise_owned")
    if not bool(summary.get("lotusIdeaDoesNotApproveRiskProfile", True)):
        blockers.append("lotus_idea_risk_profile_authority_boundary_missing")
    return list(dict.fromkeys(blockers))


def _has_required_diagnostics(value: object) -> bool:
    return set(REQUIRED_RISK_PROFILE_DIAGNOSTICS).issubset(
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
