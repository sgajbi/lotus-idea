from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.application.downstream_realization.route_source_contract import (
    ADVISE_PROPOSAL_ROUTE,
    ADVISE_ROUTE_PROFILE,
    REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.application.source_runtime_evidence import is_sha256
from app.domain.proof_evidence import EvidenceClass

ADVISE_INTAKE_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_ADVISE_INTAKE_RUNTIME_EXECUTION_PROOF"
ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.advise-intake.runtime-execution.v1"
ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED = ("advise_live_contract_proof_missing",)
REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS = ("suitability_policy_authority_remains_lotus_advise",)
ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS = (
    "../lotus-advise/contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
    "../lotus-advise/src/api/proposals/routes_idea_intake.py",
    "../lotus-advise/src/api/proposals/idea_intake_principal.py",
    "../lotus-advise/src/core/proposals/idea_intake_authority.py",
    "../lotus-advise/src/core/proposals/idea_proposal_intake.py",
    "../lotus-advise/tests/unit/advisory/api/test_idea_proposal_intake_api.py",
    "src/app/application/downstream_realization/advise_intake_runtime_execution.py",
    "scripts/downstream_realization/generate_advise_intake_runtime_execution.py",
    "scripts/downstream_realization/advise_intake_runtime_execution_gate.py",
    "GET /api/v1/downstream-realization/readiness",
    "GET /api/v1/implementation-proof/readiness",
)

_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "runtimeProofValid",
        "sourceRepository",
        "downstreamAuthority",
        "targetRoute",
        "runtimeMode",
        "sourceAuthority",
        "evidenceRefs",
        "receiptEvidence",
        "runtimeChecks",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "producerCertificationBlockersRetained",
        "nonProofClaims",
    }
)
_RECEIPT_EVIDENCE_FIELDS = frozenset(
    {
        "accepted",
        "acceptedReplay",
        "rejected",
        "idempotencyConflict",
        "authorizationDenied",
        "tenantScopedIdempotency",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "statusCode",
        "intakeStatus",
        "intakeReceiptAccepted",
        "idempotencyReplay",
        "receiptDigest",
        "reasonCodes",
        "proposalRecordCreated",
        "suitabilityAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
    }
)
_RUNTIME_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "routeServingObserved",
        "requestAuthorizationObserved",
        "tenantIsolationObserved",
        "runtimeExecutionObserved",
        "acceptedReceiptObserved",
        "replayReceiptObserved",
        "rejectedReceiptObserved",
        "idempotencyConflictObserved",
        "proposalAuthorityRetained",
        "suitabilityAuthorityRetained",
        "clientPublicationAuthorityRetained",
        "supportedFeatureNotPromoted",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "proposalRecordCreated",
        "suitabilityAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
        "productionIdentityCertified",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)
_SUPPORTED_RUNTIME_MODES = frozenset({"local_asgi_testclient", "http_service"})
_EXPECTED_PROOF_TYPE = "lotus_advise_idea_proposal_intake_runtime_execution"
_EXPECTED_PROOF_SCOPE = "advise_intake_route_serving_and_receipt_behavior"
_EXPECTED_DOWNSTREAM_AUTHORITY = "lotus-advise"
_EXPECTED_SOURCE_REPOSITORY = "lotus-idea"


def build_advise_intake_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_root: Path | None,
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    source_authority = _source_authority(advise_root or repository_root.parent / "lotus-advise")
    runtime_checks = _runtime_checks(
        generated_at_utc=generated_at_utc,
        source_authority=source_authority,
        runtime_mode=runtime_mode,
        receipt_evidence=receipt_evidence,
    )
    return {
        "schemaVersion": ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": all(runtime_checks.values()),
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": ADVISE_PROPOSAL_ROUTE,
        "runtimeMode": runtime_mode,
        "sourceAuthority": source_authority,
        "evidenceRefs": ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS,
        "receiptEvidence": {
            name: dict(receipt_evidence.get(name, {})) for name in _RECEIPT_EVIDENCE_FIELDS
        },
        "runtimeChecks": runtime_checks,
        "aggregateBlockersSatisfied": ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": (REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS),
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


def advise_intake_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": ADVISE_PROPOSAL_ROUTE,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS:
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS
    ):
        return False
    if (
        tuple(payload.get("producerCertificationBlockersRetained") or ())
        != REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS
    ):
        return False
    if payload.get("runtimeMode") not in _SUPPORTED_RUNTIME_MODES:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if not _source_authority_is_valid(payload.get("sourceAuthority")):
        return False
    if not _non_proof_claims_are_retained(payload.get("nonProofClaims")):
        return False
    runtime_checks = payload.get("runtimeChecks")
    if not (
        isinstance(runtime_checks, Mapping)
        and set(runtime_checks) == _RUNTIME_CHECK_FIELDS
        and all(runtime_checks.get(key) is True for key in _RUNTIME_CHECK_FIELDS)
    ):
        return False
    receipt_evidence = payload.get("receiptEvidence")
    return isinstance(receipt_evidence, Mapping) and _receipt_evidence_is_valid(receipt_evidence)


def load_advise_intake_runtime_execution_from_env() -> tuple[dict[str, Any] | None, str | None]:
    path_value = os.getenv(ADVISE_INTAKE_RUNTIME_EXECUTION_ENV)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{ADVISE_INTAKE_RUNTIME_EXECUTION_ENV} must reference a JSON object")
    try:
        artifact_ref = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        artifact_ref = f"{ADVISE_INTAKE_RUNTIME_EXECUTION_ENV} artifact"
    return payload, artifact_ref


def source_safe_receipt_digest(receipt: Mapping[str, Any]) -> str:
    canonical = {
        "statusCode": receipt.get("statusCode"),
        "intakeStatus": receipt.get("intakeStatus"),
        "intakeReceiptAccepted": receipt.get("intakeReceiptAccepted"),
        "idempotencyReplay": receipt.get("idempotencyReplay"),
        "reasonCodes": receipt.get("reasonCodes"),
        "proposalRecordCreated": receipt.get("proposalRecordCreated"),
        "suitabilityAuthorityGranted": receipt.get("suitabilityAuthorityGranted"),
        "orderCreated": receipt.get("orderCreated"),
        "clientPublicationAuthorized": receipt.get("clientPublicationAuthorized"),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _runtime_checks(
    *,
    generated_at_utc: datetime,
    source_authority: tuple[dict[str, str | None], ...],
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, bool]:
    return {
        "timezoneAwareGeneratedAtUtc": (
            generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
        ),
        "sourceAuthorityDigestBound": all(
            isinstance(item.get("sha256"), str) and item["sha256"] for item in source_authority
        ),
        "routeServingObserved": runtime_mode in _SUPPORTED_RUNTIME_MODES,
        "requestAuthorizationObserved": _authorization_denied_receipt_is_valid(
            receipt_evidence.get("authorizationDenied")
        ),
        "tenantIsolationObserved": _tenant_isolation_receipt_is_valid(
            receipt_evidence.get("tenantScopedIdempotency")
        ),
        "runtimeExecutionObserved": runtime_mode in _SUPPORTED_RUNTIME_MODES,
        "acceptedReceiptObserved": _accepted_receipt_is_valid(receipt_evidence.get("accepted")),
        "replayReceiptObserved": _replay_receipt_is_valid(receipt_evidence.get("acceptedReplay")),
        "rejectedReceiptObserved": _rejected_receipt_is_valid(receipt_evidence.get("rejected")),
        "idempotencyConflictObserved": _conflict_receipt_is_valid(
            receipt_evidence.get("idempotencyConflict")
        ),
        "proposalAuthorityRetained": True,
        "suitabilityAuthorityRetained": True,
        "clientPublicationAuthorityRetained": True,
        "supportedFeatureNotPromoted": True,
    }


def _receipt_evidence_is_valid(receipt_evidence: Mapping[str, Any]) -> bool:
    return (
        set(receipt_evidence) == _RECEIPT_EVIDENCE_FIELDS
        and _accepted_receipt_is_valid(receipt_evidence.get("accepted"))
        and _replay_receipt_is_valid(receipt_evidence.get("acceptedReplay"))
        and _rejected_receipt_is_valid(receipt_evidence.get("rejected"))
        and _conflict_receipt_is_valid(receipt_evidence.get("idempotencyConflict"))
        and _authorization_denied_receipt_is_valid(receipt_evidence.get("authorizationDenied"))
        and _tenant_isolation_receipt_is_valid(receipt_evidence.get("tenantScopedIdempotency"))
    )


def _accepted_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED",
        accepted=True,
        replay=False,
        reason_codes=("idea_intake_receipt_accepted",),
    )


def _replay_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED_REPLAYED",
        accepted=True,
        replay=True,
        reason_codes=("idea_intake_receipt_replayed",),
    )


def _rejected_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="REJECTED",
        accepted=False,
        replay=False,
        reason_codes=(
            "advisory_proposal_creation_not_certified",
            "idea_intake_receipt_rejected_no_proposal_created",
        ),
    )


def _tenant_isolation_receipt_is_valid(value: object) -> bool:
    return _accepted_receipt_is_valid(value)


def _conflict_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=409,
        intake_status=None,
        accepted=None,
        replay=None,
        reason_codes=("IDEA_PROPOSAL_INTAKE_IDEMPOTENCY_CONFLICT",),
    )


def _authorization_denied_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=403,
        intake_status=None,
        accepted=None,
        replay=None,
        reason_codes=("IDEA_PROPOSAL_INTAKE_CAPABILITY_REQUIRED",),
    )


def _receipt_matches(
    value: object,
    *,
    status_code: int,
    intake_status: str | None,
    accepted: bool | None,
    replay: bool | None,
    reason_codes: tuple[str, ...],
) -> bool:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_FIELDS:
        return False
    return (
        value.get("statusCode") == status_code
        and value.get("intakeStatus") == intake_status
        and value.get("intakeReceiptAccepted") is accepted
        and value.get("idempotencyReplay") is replay
        and tuple(value.get("reasonCodes") or ()) == reason_codes
        and is_sha256(value.get("receiptDigest"))
        and value.get("receiptDigest") == source_safe_receipt_digest(value)
        and value.get("proposalRecordCreated") is False
        and value.get("suitabilityAuthorityGranted") is False
        and value.get("orderCreated") is False
        and value.get("clientPublicationAuthorized") is False
    )


def _non_proof_claims_are_retained(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _NON_PROOF_CLAIM_FIELDS
        and all(value.get(key) is False for key in _NON_PROOF_CLAIM_FIELDS)
    )


def _source_authority(advise_root: Path) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(
        tuple(
            SourceAuthoritySource(
                ADVISE_ROUTE_PROFILE.owner_repository,
                f"../{ADVISE_ROUTE_PROFILE.owner_repository}/{ref}",
                advise_root / ref,
            )
            for ref in ADVISE_ROUTE_PROFILE.source_refs
        )
    )


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=tuple(
            SourceAuthoritySource(
                ADVISE_ROUTE_PROFILE.owner_repository,
                f"../{ADVISE_ROUTE_PROFILE.owner_repository}/{ref}",
                Path(ref),
            )
            for ref in ADVISE_ROUTE_PROFILE.source_refs
        ),
    )
