from __future__ import annotations

from app.application.downstream_realization.route_source_contract import (
    ADVISE_ROUTE_PROFILE,
    MANAGE_ROUTE_PROFILE,
    ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
    RouteSourceContractProfile,
)
from app.domain.proof_evidence import EvidenceClass


def valid_advise_route_source_contract() -> dict[str, object]:
    return _valid_route_source_contract(ADVISE_ROUTE_PROFILE)


def valid_manage_route_source_contract() -> dict[str, object]:
    return _valid_route_source_contract(MANAGE_ROUTE_PROFILE)


def _valid_route_source_contract(profile: RouteSourceContractProfile) -> dict[str, object]:
    prefix = f"../{profile.owner_repository}/"
    return {
        "schemaVersion": ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-07-15T00:00:00+00:00",
        "proofType": profile.proof_type,
        "proofScope": profile.proof_scope,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": True,
        "sourceContractBlockersSatisfied": (),
        "evidenceRefs": profile.evidence_refs,
        "sourceAuthority": tuple(
            {
                "repository": profile.owner_repository,
                "ref": f"{prefix}{ref}",
                "sha256": "a" * 64,
            }
            for ref in profile.source_refs
        ),
        "sourceRepository": profile.source_repository,
        "downstreamAuthority": profile.downstream_authority,
        "targetRoute": profile.target_route,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "sourceAuthorityDigestBound": True,
            "downstreamContractDeclaresRoute": True,
            "downstreamContractPreservesBoundaries": True,
            "downstreamContractRetainsBlockers": True,
        },
        "remainingCertificationBlockers": profile.remaining_blockers,
        "routeServingObserved": False,
        "requestAuthorizationObserved": False,
        "tenantIsolationObserved": False,
        "runtimeExecutionObserved": False,
        "downstreamRecordAccepted": False,
        "suitabilityAuthorityGranted": False,
        "rebalanceExecutionAuthorityGranted": False,
        "clientPublicationAuthorityGranted": False,
        "productionCertificationGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }
