from __future__ import annotations

from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_ROUTE_BLOCKERS_CLEARED,
    DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION,
    MANAGE_ACTION_ROUTE,
    MANAGE_ROUTE_BLOCKERS_CLEARED,
    REMAINING_ADVISE_ROUTE_BLOCKERS,
    REMAINING_MANAGE_ROUTE_BLOCKERS,
)


def valid_advise_route_proof() -> dict[str, object]:
    return {
        "schemaVersion": DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_advise_idea_proposal_intake_route_contract",
        "proofScope": "source_safe_advise_proposal_route_only",
        "adviseProposalRouteProofValid": True,
        "aggregateBlockersCleared": ADVISE_ROUTE_BLOCKERS_CLEARED,
        "evidenceRefs": (
            "../lotus-advise/contracts/idea-proposal-intake/"
            "lotus-advise-idea-proposal-intake.v1.json",
            "../lotus-advise/src/api/proposals/router.py",
            "../lotus-advise/src/core/proposals/service.py",
            "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
            "RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
            "GET /api/v1/downstream-realization/readiness",
            "GET /api/v1/implementation-proof/readiness",
        ),
        "targetRoute": ADVISE_PROPOSAL_ROUTE,
        "sourceAuthority": "lotus-idea",
        "downstreamAuthority": "lotus-advise",
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "downstreamContractProvesRoute": True,
            "downstreamContractPreservesNonProofBoundaries": True,
            "downstreamContractRetainsAuthorityBlockers": True,
        },
        "remainingCertificationBlockers": REMAINING_ADVISE_ROUTE_BLOCKERS,
        "downstreamExecutionProven": False,
        "suitabilityAuthorityGranted": False,
        "rebalanceExecutionAuthorityGranted": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def valid_manage_route_proof() -> dict[str, object]:
    return {
        "schemaVersion": DOWNSTREAM_ROUTE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_manage_idea_action_intake_route_contract",
        "proofScope": "source_safe_manage_action_route_only",
        "manageActionRouteProofValid": True,
        "aggregateBlockersCleared": MANAGE_ROUTE_BLOCKERS_CLEARED,
        "evidenceRefs": (
            "../lotus-manage/contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
            "../lotus-manage/src/api/routers/rebalance_runs.py",
            "../lotus-manage/src/core/rebalance_runs/service.py",
            "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
            "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
            "RFC-0002-slice-12-advise-and-manage-conversion-realization.md",
            "GET /api/v1/downstream-realization/readiness",
            "GET /api/v1/implementation-proof/readiness",
        ),
        "targetRoute": MANAGE_ACTION_ROUTE,
        "sourceAuthority": "lotus-manage",
        "downstreamAuthority": "lotus-manage",
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "downstreamContractProvesRoute": True,
            "downstreamContractPreservesNonProofBoundaries": True,
            "downstreamContractRetainsAuthorityBlockers": True,
        },
        "remainingCertificationBlockers": REMAINING_MANAGE_ROUTE_BLOCKERS,
        "downstreamExecutionProven": False,
        "suitabilityAuthorityGranted": False,
        "rebalanceExecutionAuthorityGranted": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }
