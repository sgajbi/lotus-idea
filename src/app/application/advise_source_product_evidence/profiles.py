from __future__ import annotations

from dataclasses import dataclass


ADVISE_SOURCE_PRODUCT_ID = "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
ADVISE_SOURCE_PRODUCT_CONTRACT_REF = (
    "lotus-advise://contracts/domain-data-products/"
    "lotus-advise-products.v1.json#AdvisoryPolicyEvaluationRecord"
)
ADVISE_SOURCE_TELEMETRY_CONTRACT_REF = (
    "lotus-advise://contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)


@dataclass(frozen=True)
class AdviseSourceProductProfile:
    capability: str
    proof_type: str
    proof_scope: str
    diagnostic_family: str
    required_diagnostics: tuple[str, ...]
    blockers_satisfied: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    non_proof_boundaries: tuple[str, ...]


_COMMON_EVIDENCE_REFS = (
    "src/app/application/advise_source_product_evidence/contract.py",
    "src/app/application/advise_source_product_evidence/profiles.py",
    "scripts/advise_source_product_evidence/generate_source_contract.py",
    "scripts/advise_source_product_evidence/source_contract_gate.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "GET /api/v1/implementation-proof/readiness",
)

MANDATE_RESTRICTION_PROFILE = AdviseSourceProductProfile(
    capability="mandate-restriction",
    proof_type="advise_mandate_restriction_source_product_source_contract",
    proof_scope="opportunity-archetype.mandate-restriction-review",
    diagnostic_family="mandate_restriction",
    required_diagnostics=(
        "mandate_restriction_review_required",
        "product_restriction_review_required",
        "country_restriction_review_required",
        "suitability_policy_actionability_blocked",
    ),
    blockers_satisfied=("opportunity_archetype_typed_restriction_source_product_missing",),
    remaining_blockers=(
        "opportunity_archetype_live_restriction_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ),
    evidence_refs=(
        *_COMMON_EVIDENCE_REFS,
        "src/app/domain/mandate_restriction_signal.py",
        "src/app/application/mandate_restriction_signal.py",
        "src/app/ports/advise_sources.py",
        "src/app/infrastructure/lotus_advise_sources.py",
    ),
    non_proof_boundaries=(
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
        "no_deployment_certification",
        "no_production_certification",
        "no_supported_feature_promotion",
    ),
)

MISSING_RISK_PROFILE = AdviseSourceProductProfile(
    capability="missing-risk-profile",
    proof_type="advise_missing_risk_profile_source_product_source_contract",
    proof_scope="opportunity-archetype.missing-risk-profile-review",
    diagnostic_family="risk_profile",
    required_diagnostics=(
        "risk_profile_missing",
        "risk_profile_stale",
        "risk_profile_expired",
        "risk_profile_review_due",
    ),
    blockers_satisfied=("opportunity_archetype_typed_advise_risk_profile_source_product_missing",),
    remaining_blockers=(
        "opportunity_archetype_advise_risk_profile_live_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ),
    evidence_refs=(
        *_COMMON_EVIDENCE_REFS,
        "src/app/domain/missing_risk_profile_signal.py",
        "src/app/application/missing_risk_profile_signal.py",
        "src/app/ports/advise_sources.py",
        "src/app/infrastructure/lotus_advise_sources.py",
    ),
    non_proof_boundaries=(
        "no_live_advise_source_proof",
        "no_risk_profile_approval",
        "no_suitability_approval",
        "no_policy_approval",
        "no_proposal_approval",
        "no_client_publication_approval",
        "no_data_mesh_certification",
        "no_workbench_product_proof",
        "no_deployment_certification",
        "no_production_certification",
        "no_supported_feature_promotion",
    ),
)

PROFILES = {
    MANDATE_RESTRICTION_PROFILE.capability: MANDATE_RESTRICTION_PROFILE,
    MISSING_RISK_PROFILE.capability: MISSING_RISK_PROFILE,
}
