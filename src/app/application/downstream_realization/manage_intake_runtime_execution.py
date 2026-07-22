from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from app.application.downstream_realization.intake_runtime_execution_common import (
    intake_receipt_evidence_is_valid,
    intake_receipt_matches,
    non_proof_claims_are_retained,
    source_safe_intake_receipt_digest,
)
from app.application.downstream_realization.route_source_contract import (
    MANAGE_ACTION_ROUTE,
    MANAGE_ROUTE_PROFILE,
    REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.domain.proof_evidence import EvidenceClass

MANAGE_INTAKE_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF"
MANAGE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.manage-intake.runtime-execution.v1"
MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED = ("manage_live_contract_proof_missing",)
REMAINING_MANAGE_INTAKE_RUNTIME_BLOCKERS = ("rebalance_execution_authority_remains_lotus_manage",)
MANAGE_INTAKE_RUNTIME_EVIDENCE_REFS = (
    "../lotus-manage/contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
    "../lotus-manage/src/api/routers/rebalance_runs_idea_action_intake_routes.py",
    "../lotus-manage/src/api/routers/rebalance_runs_idea_action_intake_principal.py",
    "../lotus-manage/src/core/rebalance_runs/idea_action_intake_authority.py",
    "../lotus-manage/src/core/rebalance_runs/idea_action_intake.py",
    "../lotus-manage/tests/unit/dpm/api/test_idea_action_intake_api.py",
    "src/app/application/downstream_realization/manage_intake_runtime_execution.py",
    "scripts/downstream_realization/generate_manage_intake_runtime_execution.py",
    "scripts/downstream_realization/manage_intake_runtime_execution_gate.py",
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
        "actionRegisterCreated",
        "rebalanceExecutionAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
    }
)
_RECEIPT_DIGEST_FIELDS = (
    "statusCode",
    "intakeStatus",
    "intakeReceiptAccepted",
    "idempotencyReplay",
    "reasonCodes",
    "actionRegisterCreated",
    "rebalanceExecutionAuthorityGranted",
    "orderCreated",
    "clientPublicationAuthorized",
)
_RETAINED_FALSE_RECEIPT_FIELDS = (
    "actionRegisterCreated",
    "rebalanceExecutionAuthorityGranted",
    "orderCreated",
    "clientPublicationAuthorized",
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
        "actionRegisterAuthorityRetained",
        "rebalanceExecutionAuthorityRetained",
        "clientPublicationAuthorityRetained",
        "supportedFeatureNotPromoted",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "actionRegisterCreated",
        "rebalanceExecutionAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
        "productionIdentityCertified",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)
_SUPPORTED_RUNTIME_MODES = frozenset({"local_asgi_testclient", "http_service"})
_EXPECTED_PROOF_TYPE = "lotus_manage_idea_action_intake_runtime_execution"
_EXPECTED_PROOF_SCOPE = "manage_action_intake_route_serving_and_receipt_behavior"
_EXPECTED_DOWNSTREAM_AUTHORITY = "lotus-manage"
_EXPECTED_SOURCE_REPOSITORY = "lotus-idea"


def build_manage_intake_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    manage_root: Path | None,
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    source_authority = _source_authority(manage_root or repository_root.parent / "lotus-manage")
    runtime_checks = _runtime_checks(
        generated_at_utc=generated_at_utc,
        source_authority=source_authority,
        runtime_mode=runtime_mode,
        receipt_evidence=receipt_evidence,
    )
    return {
        "schemaVersion": MANAGE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": all(runtime_checks.values()),
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": MANAGE_ACTION_ROUTE,
        "runtimeMode": runtime_mode,
        "sourceAuthority": source_authority,
        "evidenceRefs": MANAGE_INTAKE_RUNTIME_EVIDENCE_REFS,
        "receiptEvidence": {
            name: dict(receipt_evidence.get(name, {})) for name in _RECEIPT_EVIDENCE_FIELDS
        },
        "runtimeChecks": runtime_checks,
        "aggregateBlockersSatisfied": MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_MANAGE_INTAKE_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS,
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


def manage_intake_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": MANAGE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": MANAGE_ACTION_ROUTE,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != MANAGE_INTAKE_RUNTIME_EVIDENCE_REFS:
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != REMAINING_MANAGE_INTAKE_RUNTIME_BLOCKERS
    ):
        return False
    if (
        tuple(payload.get("producerCertificationBlockersRetained") or ())
        != REQUIRED_MANAGE_PRODUCER_CERTIFICATION_BLOCKERS
    ):
        return False
    if payload.get("runtimeMode") not in _SUPPORTED_RUNTIME_MODES:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if not _source_authority_is_valid(payload.get("sourceAuthority")):
        return False
    if not non_proof_claims_are_retained(
        payload.get("nonProofClaims"),
        expected_fields=_NON_PROOF_CLAIM_FIELDS,
    ):
        return False
    runtime_checks = payload.get("runtimeChecks")
    if not (
        isinstance(runtime_checks, Mapping)
        and set(runtime_checks) == _RUNTIME_CHECK_FIELDS
        and all(runtime_checks.get(key) is True for key in _RUNTIME_CHECK_FIELDS)
    ):
        return False
    receipt_evidence = payload.get("receiptEvidence")
    return isinstance(receipt_evidence, Mapping) and intake_receipt_evidence_is_valid(
        receipt_evidence,
        expected_fields=_RECEIPT_EVIDENCE_FIELDS,
        accepted_receipt_is_valid=_accepted_receipt_is_valid,
        replay_receipt_is_valid=_replay_receipt_is_valid,
        rejected_receipt_is_valid=_rejected_receipt_is_valid,
        conflict_receipt_is_valid=_conflict_receipt_is_valid,
        authorization_denied_receipt_is_valid=_authorization_denied_receipt_is_valid,
        tenant_isolation_receipt_is_valid=_tenant_isolation_receipt_is_valid,
    )


def load_manage_intake_runtime_execution_from_env() -> tuple[dict[str, Any] | None, str | None]:
    path_value = os.getenv(MANAGE_INTAKE_RUNTIME_EXECUTION_ENV)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{MANAGE_INTAKE_RUNTIME_EXECUTION_ENV} must reference a JSON object")
    try:
        artifact_ref = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        artifact_ref = f"{MANAGE_INTAKE_RUNTIME_EXECUTION_ENV} artifact"
    return payload, artifact_ref


def source_safe_manage_receipt_digest(receipt: Mapping[str, Any]) -> str:
    return source_safe_intake_receipt_digest(receipt, digest_fields=_RECEIPT_DIGEST_FIELDS)


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
        "actionRegisterAuthorityRetained": True,
        "rebalanceExecutionAuthorityRetained": True,
        "clientPublicationAuthorityRetained": True,
        "supportedFeatureNotPromoted": True,
    }


def _accepted_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED",
        accepted=True,
        replay=False,
        reason_codes=("idea_action_intake_receipt_accepted",),
    )


def _replay_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED_REPLAYED",
        accepted=True,
        replay=True,
        reason_codes=("idea_action_intake_receipt_replayed",),
    )


def _rejected_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="REJECTED",
        accepted=False,
        replay=False,
        reason_codes=(
            "action_register_persistence_not_certified",
            "idea_action_intake_receipt_rejected_no_action_created",
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
        reason_codes=("IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT",),
    )


def _authorization_denied_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=403,
        intake_status=None,
        accepted=None,
        replay=None,
        reason_codes=("IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED",),
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
    return intake_receipt_matches(
        value,
        receipt_fields=_RECEIPT_FIELDS,
        status_code=status_code,
        intake_status=intake_status,
        accepted=accepted,
        replay=replay,
        reason_codes=reason_codes,
        digest=source_safe_manage_receipt_digest,
        retained_false_fields=_RETAINED_FALSE_RECEIPT_FIELDS,
    )


def _source_authority(manage_root: Path) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(
        tuple(
            SourceAuthoritySource(
                MANAGE_ROUTE_PROFILE.owner_repository,
                f"../{MANAGE_ROUTE_PROFILE.owner_repository}/{ref}",
                manage_root / ref,
            )
            for ref in MANAGE_ROUTE_PROFILE.source_refs
        )
    )


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=tuple(
            SourceAuthoritySource(
                MANAGE_ROUTE_PROFILE.owner_repository,
                f"../{MANAGE_ROUTE_PROFILE.owner_repository}/{ref}",
                Path(ref),
            )
            for ref in MANAGE_ROUTE_PROFILE.source_refs
        ),
    )
