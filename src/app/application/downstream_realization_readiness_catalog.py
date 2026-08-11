from __future__ import annotations

from app.application.downstream_realization_contracts import (
    DownstreamRealizationContractPlanRecord,
    load_downstream_realization_contract_plan,
)
from app.application.downstream_realization_issue_refs import capability_blocker_issue_refs
from app.application.downstream_realization_readiness_models import (
    DownstreamReadinessComponents,
    DownstreamRealizationCapabilityReadiness,
    DownstreamRealizationContractReadiness,
    build_downstream_capability_readiness,
)


def initial_downstream_readiness_components() -> DownstreamReadinessComponents:
    contract_plan = load_downstream_realization_contract_plan()
    return (
        (
            _advise_conversion_capability(),
            _manage_conversion_capability(),
            _report_render_archive_capability(),
        ),
        tuple(_downstream_contract_from_plan(record) for record in contract_plan.contracts),
    )


def _advise_conversion_capability() -> DownstreamRealizationCapabilityReadiness:
    return build_downstream_capability_readiness(
        "advise-proposal-realization",
        "Advise proposal and suitability realization",
        "lotus-advise",
        evidence_refs=(
            "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
            "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "suitability_policy_authority_remains_lotus_advise",
            "advise_live_contract_proof_missing",
        ),
        blocker_issue_refs=capability_blocker_issue_refs("advise-proposal-realization"),
    )


def _manage_conversion_capability() -> DownstreamRealizationCapabilityReadiness:
    return build_downstream_capability_readiness(
        "manage-action-realization",
        "Manage action register and implementation realization",
        "lotus-manage",
        evidence_refs=(
            "POST /api/v1/idea-candidates/{candidateId}/conversion-intents",
            "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
            "POST /api/v1/conversion-intents/{conversionIntentId}/outcomes",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
        ),
        blockers=(
            "rebalance_execution_authority_remains_lotus_manage",
            "manage_live_contract_proof_missing",
        ),
        blocker_issue_refs=capability_blocker_issue_refs("manage-action-realization"),
    )


def _report_render_archive_capability() -> DownstreamRealizationCapabilityReadiness:
    return build_downstream_capability_readiness(
        "report-render-archive-realization",
        "Report, Render, and Archive evidence-pack materialization",
        "lotus-report",
        evidence_refs=(
            "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
            "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
            "lotus-render",
            "lotus-archive",
        ),
        blockers=(
            "report_evidence_pack_live_materialization_proof_missing",
            "rendered_output_creation_missing",
            "archive_record_creation_missing",
            "client_publication_authority_blocked",
        ),
        blocker_issue_refs=capability_blocker_issue_refs("report-render-archive-realization"),
    )


def _downstream_contract_from_plan(
    record: DownstreamRealizationContractPlanRecord,
) -> DownstreamRealizationContractReadiness:
    return DownstreamRealizationContractReadiness(
        contract_id=record.contract_id,
        owner_repository=record.owner_repository,
        source_authority=record.source_authority,
        target_route=record.target_route,
        route_fit_status=record.route_fit_status,
        adapter_status=record.adapter_status,
        evidence_refs=record.evidence_refs,
        blockers=record.blockers,
        blocker_issue_refs=record.blocker_issue_refs,
    )
