from __future__ import annotations

from app.application.downstream_realization.route_source_contract import (
    ADVISE_ROUTE_PROFILE,
    MANAGE_ROUTE_PROFILE,
    ROUTE_SOURCE_CONTRACT_SCHEMA_VERSION,
    RouteSourceContractProfile,
)
from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS,
    ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
    REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS,
    source_safe_receipt_digest,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    MANAGE_INTAKE_RUNTIME_EVIDENCE_REFS,
    MANAGE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
    REMAINING_MANAGE_INTAKE_RUNTIME_BLOCKERS,
    source_safe_manage_receipt_digest,
)
from app.domain.proof_evidence import EvidenceClass


def valid_advise_route_source_contract() -> dict[str, object]:
    return _valid_route_source_contract(ADVISE_ROUTE_PROFILE)


def valid_manage_route_source_contract() -> dict[str, object]:
    return _valid_route_source_contract(MANAGE_ROUTE_PROFILE)


def valid_advise_intake_runtime_execution() -> dict[str, object]:
    receipt_evidence = _valid_advise_intake_receipt_evidence()
    return {
        "schemaVersion": ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-07-22T00:00:00Z",
        "proofType": "lotus_advise_idea_proposal_intake_runtime_execution",
        "proofScope": "advise_intake_route_serving_and_receipt_behavior",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "sourceRepository": "lotus-idea",
        "downstreamAuthority": "lotus-advise",
        "targetRoute": "POST /advisory/proposals/idea-intake",
        "runtimeMode": "local_asgi_testclient",
        "sourceAuthority": tuple(
            {
                "repository": ADVISE_ROUTE_PROFILE.owner_repository,
                "ref": f"../{ADVISE_ROUTE_PROFILE.owner_repository}/{ref}",
                "sha256": "b" * 64,
            }
            for ref in ADVISE_ROUTE_PROFILE.source_refs
        ),
        "evidenceRefs": ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS,
        "receiptEvidence": receipt_evidence,
        "runtimeChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "sourceAuthorityDigestBound": True,
            "routeServingObserved": True,
            "requestAuthorizationObserved": True,
            "tenantIsolationObserved": True,
            "runtimeExecutionObserved": True,
            "acceptedReceiptObserved": True,
            "replayReceiptObserved": True,
            "rejectedReceiptObserved": True,
            "idempotencyConflictObserved": True,
            "proposalAuthorityRetained": True,
            "suitabilityAuthorityRetained": True,
            "clientPublicationAuthorityRetained": True,
            "supportedFeatureNotPromoted": True,
        },
        "aggregateBlockersSatisfied": ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": (
            "suitability_policy_authority_remains_lotus_advise",
            "advisory_proposal_creation_not_certified",
            "proposal_lifecycle_persistence_not_certified",
            "client_publication_authority_blocked",
        ),
        "nonProofClaims": {
            "proposalRecordCreated": False,
            "suitabilityAuthorityGranted": False,
            "orderCreated": False,
            "clientPublicationAuthorized": False,
            "productionIdentityCertified": False,
            "productionCertificationGranted": False,
            "supportedFeaturePromoted": False,
            "certificationClosed": False,
        },
    }


def valid_manage_intake_runtime_execution() -> dict[str, object]:
    receipt_evidence = _valid_manage_intake_receipt_evidence()
    return {
        "schemaVersion": MANAGE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-07-22T00:00:00Z",
        "proofType": "lotus_manage_idea_action_intake_runtime_execution",
        "proofScope": "manage_action_intake_route_serving_and_receipt_behavior",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "sourceRepository": "lotus-idea",
        "downstreamAuthority": "lotus-manage",
        "targetRoute": "POST /api/v1/rebalance/idea-action-intake",
        "runtimeMode": "local_asgi_testclient",
        "sourceAuthority": tuple(
            {
                "repository": MANAGE_ROUTE_PROFILE.owner_repository,
                "ref": f"../{MANAGE_ROUTE_PROFILE.owner_repository}/{ref}",
                "sha256": "c" * 64,
            }
            for ref in MANAGE_ROUTE_PROFILE.source_refs
        ),
        "evidenceRefs": MANAGE_INTAKE_RUNTIME_EVIDENCE_REFS,
        "receiptEvidence": receipt_evidence,
        "runtimeChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "sourceAuthorityDigestBound": True,
            "routeServingObserved": True,
            "requestAuthorizationObserved": True,
            "tenantIsolationObserved": True,
            "runtimeExecutionObserved": True,
            "acceptedReceiptObserved": True,
            "replayReceiptObserved": True,
            "rejectedReceiptObserved": True,
            "idempotencyConflictObserved": True,
            "actionRegisterAuthorityRetained": True,
            "rebalanceExecutionAuthorityRetained": True,
            "clientPublicationAuthorityRetained": True,
            "supportedFeatureNotPromoted": True,
        },
        "aggregateBlockersSatisfied": MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_MANAGE_INTAKE_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": (
            "rebalance_execution_authority_remains_lotus_manage",
            "action_register_persistence_not_certified",
            "oms_execution_not_certified",
            "client_publication_authority_blocked",
        ),
        "nonProofClaims": {
            "actionRegisterCreated": False,
            "rebalanceExecutionAuthorityGranted": False,
            "orderCreated": False,
            "clientPublicationAuthorized": False,
            "productionIdentityCertified": False,
            "productionCertificationGranted": False,
            "supportedFeaturePromoted": False,
            "certificationClosed": False,
        },
    }


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


def _valid_advise_intake_receipt_evidence() -> dict[str, dict[str, object]]:
    receipts = {
        "accepted": _receipt(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=("idea_intake_receipt_accepted",),
        ),
        "acceptedReplay": _receipt(
            status_code=202,
            intake_status="ACCEPTED_REPLAYED",
            accepted=True,
            replay=True,
            reason_codes=("idea_intake_receipt_replayed",),
        ),
        "rejected": _receipt(
            status_code=202,
            intake_status="REJECTED",
            accepted=False,
            replay=False,
            reason_codes=(
                "advisory_proposal_creation_not_certified",
                "idea_intake_receipt_rejected_no_proposal_created",
            ),
        ),
        "idempotencyConflict": _receipt(
            status_code=409,
            intake_status=None,
            accepted=None,
            replay=None,
            reason_codes=("IDEA_PROPOSAL_INTAKE_IDEMPOTENCY_CONFLICT",),
        ),
        "authorizationDenied": _receipt(
            status_code=403,
            intake_status=None,
            accepted=None,
            replay=None,
            reason_codes=("IDEA_PROPOSAL_INTAKE_CAPABILITY_REQUIRED",),
        ),
        "tenantScopedIdempotency": _receipt(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=("idea_intake_receipt_accepted",),
        ),
    }
    for receipt in receipts.values():
        receipt["receiptDigest"] = source_safe_receipt_digest(receipt)
    return receipts


def _valid_manage_intake_receipt_evidence() -> dict[str, dict[str, object]]:
    receipts = {
        "accepted": _manage_receipt(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=("idea_action_intake_receipt_accepted",),
        ),
        "acceptedReplay": _manage_receipt(
            status_code=202,
            intake_status="ACCEPTED_REPLAYED",
            accepted=True,
            replay=True,
            reason_codes=("idea_action_intake_receipt_replayed",),
        ),
        "rejected": _manage_receipt(
            status_code=202,
            intake_status="REJECTED",
            accepted=False,
            replay=False,
            reason_codes=(
                "action_register_persistence_not_certified",
                "idea_action_intake_receipt_rejected_no_action_created",
            ),
        ),
        "idempotencyConflict": _manage_receipt(
            status_code=409,
            intake_status=None,
            accepted=None,
            replay=None,
            reason_codes=("IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT",),
        ),
        "authorizationDenied": _manage_receipt(
            status_code=403,
            intake_status=None,
            accepted=None,
            replay=None,
            reason_codes=("IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED",),
        ),
        "tenantScopedIdempotency": _manage_receipt(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=("idea_action_intake_receipt_accepted",),
        ),
    }
    for receipt in receipts.values():
        receipt["receiptDigest"] = source_safe_manage_receipt_digest(receipt)
    return receipts


def _receipt(
    *,
    status_code: int,
    intake_status: str | None,
    accepted: bool | None,
    replay: bool | None,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "statusCode": status_code,
        "intakeStatus": intake_status,
        "intakeReceiptAccepted": accepted,
        "idempotencyReplay": replay,
        "receiptDigest": None,
        "reasonCodes": reason_codes,
        "proposalRecordCreated": False,
        "suitabilityAuthorityGranted": False,
        "orderCreated": False,
        "clientPublicationAuthorized": False,
    }


def _manage_receipt(
    *,
    status_code: int,
    intake_status: str | None,
    accepted: bool | None,
    replay: bool | None,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "statusCode": status_code,
        "intakeStatus": intake_status,
        "intakeReceiptAccepted": accepted,
        "idempotencyReplay": replay,
        "receiptDigest": None,
        "reasonCodes": reason_codes,
        "actionRegisterCreated": False,
        "rebalanceExecutionAuthorityGranted": False,
        "orderCreated": False,
        "clientPublicationAuthorized": False,
    }
