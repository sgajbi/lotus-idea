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
ADVISE_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.advise-intake.runtime-execution.v5"
ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED = (
    "advise_live_contract_proof_missing",
    "advise_timeout_uncertainty_certification_missing",
    "advise_owner_correction_certification_missing",
    "advise_concurrent_owner_advancement_certification_missing",
    "advise_restart_replay_certification_missing",
)
REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS = ("suitability_policy_authority_remains_lotus_advise",)
ADVISE_REALIZATION_READ_ROUTE = "GET /advisory/proposals/idea-intake/{intake_id}/realization"
ADVISE_REALIZATION_RECOVERY_ROUTE = (
    "GET /advisory/proposals/idea-intake/realization?conversion_intent_id={id}"
)
ADVISE_PROPOSAL_RECONCILIATION_ROUTE = (
    "POST /advisory/proposals/idea-intake/{intake_id}/realization/proposal-reconciliation"
)
ADVISE_INTAKE_RUNTIME_SOURCE_REFS = (
    *ADVISE_ROUTE_PROFILE.source_refs,
    "src/api/proposals/router.py",
    "src/core/proposals/idea_realization_read_model.py",
    "src/core/proposals/idea_realization_commands.py",
    "src/core/proposals/idea_review_realization.py",
    "src/infrastructure/proposals/in_memory.py",
    "src/infrastructure/proposals/postgres_idea_intakes.py",
    "src/infrastructure/proposals/postgres_idea_repository.py",
    "src/infrastructure/postgres_migrations/proposals/0011_idea_proposal_intakes.sql",
    "src/infrastructure/postgres_migrations/proposals/0012_idea_review_realizations.sql",
    "src/infrastructure/postgres_migrations/proposals/0013_idea_proposal_outcomes.sql",
    "tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py",
)
IDEA_ADVISE_RECONCILIATION_SOURCE_REFS = (
    "src/app/application/advise_realization_reconciliation.py",
    "src/app/infrastructure/postgres_advise_realization.py",
    "scripts/downstream_realization/advise_postgres_restart_evidence.py",
    "tests/integration/test_postgres_downstream_submission_runtime.py",
)
ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS = (
    "../lotus-advise/contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
    "../lotus-advise/src/api/proposals/routes_idea_intake.py",
    "../lotus-advise/src/api/proposals/idea_intake_principal.py",
    "../lotus-advise/src/core/proposals/idea_intake_authority.py",
    "../lotus-advise/src/core/proposals/idea_proposal_intake.py",
    "../lotus-advise/src/core/proposals/idea_realization_read_model.py",
    "../lotus-advise/src/core/proposals/idea_realization_commands.py",
    "../lotus-advise/src/core/proposals/idea_review_realization.py",
    "../lotus-advise/src/api/proposals/router.py",
    "../lotus-advise/src/infrastructure/proposals/in_memory.py",
    "../lotus-advise/src/infrastructure/proposals/postgres_idea_intakes.py",
    "../lotus-advise/src/infrastructure/proposals/postgres_idea_repository.py",
    "../lotus-advise/tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py",
    "../lotus-advise/tests/unit/advisory/api/test_idea_proposal_intake_api.py",
    "src/app/application/downstream_realization/advise_intake_runtime_execution.py",
    "scripts/downstream_realization/advise_runtime_evidence_projection.py",
    "scripts/downstream_realization/generate_advise_intake_runtime_execution.py",
    "scripts/downstream_realization/advise_postgres_restart_evidence.py",
    "scripts/downstream_realization/advise_intake_runtime_execution_gate.py",
    "tests/integration/test_postgres_downstream_submission_runtime.py",
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
        "ownerReadRoute",
        "ownerRecoveryRoute",
        "ownerReconciliationRoute",
        "runtimeMode",
        "sourceAuthority",
        "evidenceRefs",
        "receiptEvidence",
        "submittedIntentEvidence",
        "ownerRealizationEvidence",
        "ownerAdvancementEvidence",
        "ownerRestartEvidence",
        "ideaReconciliationEvidence",
        "preCommitTimeoutEvidence",
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
        "concurrentAccepted",
        "concurrentReplay",
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
        "ownerIdentityDigest",
        "scopeDigest",
        "reviewWorkStatus",
        "sourceEvidenceFingerprint",
        "realizationStatus",
        "sourceEventVersion",
        "proposalRecordCreated",
        "suitabilityAuthorityGranted",
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
    "ownerIdentityDigest",
    "scopeDigest",
    "reviewWorkStatus",
    "sourceEvidenceFingerprint",
    "realizationStatus",
    "sourceEventVersion",
    "proposalRecordCreated",
    "suitabilityAuthorityGranted",
    "orderCreated",
    "clientPublicationAuthorized",
)
_RETAINED_FALSE_RECEIPT_FIELDS = (
    "proposalRecordCreated",
    "suitabilityAuthorityGranted",
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
        "concurrentDuplicateConvergenceObserved",
        "ownerRealizationReadbackObserved",
        "staleOwnerAdvancementRefused",
        "correctedOwnerAdvancementObserved",
        "concurrentOwnerAdvancementConverged",
        "postgresOwnerRestartReplayObserved",
        "postgresIdeaReconciliationReplayObserved",
        "timeoutBeforeOwnerCommitObserved",
        "automaticResubmissionPrevented",
        "proposalAuthorityRetained",
        "suitabilityAuthorityRetained",
        "clientPublicationAuthorityRetained",
        "supportedFeatureNotPromoted",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "ideaOwnedProposalRecordCreated",
        "suitabilityAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
        "productionIdentityCertified",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)
_SUPPORTED_RUNTIME_MODES = frozenset({"local_asgi_testclient"})
_EXPECTED_PROOF_TYPE = "lotus_advise_idea_proposal_intake_runtime_execution"
_EXPECTED_PROOF_SCOPE = "advise_intake_and_owner_progression_route_behavior"
_EXPECTED_DOWNSTREAM_AUTHORITY = "lotus-advise"
_EXPECTED_SOURCE_REPOSITORY = "lotus-idea"
_PRE_COMMIT_TIMEOUT_EVIDENCE_FIELDS = frozenset(
    {
        "failureStage",
        "sourceIntentDigest",
        "scopeDigest",
        "ownerLookupStatusCode",
        "ownerLookupReasonCodes",
        "repeatedOwnerLookupStatusCode",
        "repeatedOwnerLookupReasonCodes",
        "downstreamPostAttemptCount",
        "automaticResubmissionAttemptCount",
        "ownerStateObserved",
    }
)
_OWNER_REALIZATION_NOT_FOUND_REASON = "IDEA_PROPOSAL_REALIZATION_NOT_FOUND"
_OWNER_VERSION_CONFLICT_REASON = "IDEA_PROPOSAL_REALIZATION_VERSION_CONFLICT"
_OWNER_ADVANCEMENT_EVIDENCE_FIELDS = frozenset(
    {
        "ownerIdentityDigest",
        "scopeDigest",
        "sourceIntentDigest",
        "sourceEvidenceFingerprint",
        "linkedStatusCode",
        "linkedSourceEventVersion",
        "staleCorrectionStatusCode",
        "staleCorrectionReasonCodes",
        "sourceEventVersionAfterRefusal",
        "concurrentStatusCodes",
        "concurrentSourceEventVersions",
        "finalStatusCode",
        "finalStatus",
        "finalSourceEventVersion",
        "finalOutcomeVersions",
        "finalOutcomeStatuses",
        "proposalIdentityPresent",
        "proposalRecordCreated",
        "suitabilityAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
    }
)
ADVISE_OWNER_RESTART_TEST_NODES = (
    "tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py::test_live_postgres_idea_proposal_reconciliation_is_atomic_and_restart_safe",
    "tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py::test_live_postgres_idea_intake_claim_is_restart_safe_and_conflict_detecting",
)
_OWNER_RESTART_EVIDENCE_FIELDS = frozenset(
    {
        "evidenceClass",
        "databaseBackend",
        "testNodes",
        "testProcessExitCode",
        "testPassedCount",
        "testSourceDigest",
        "ownerRepositoryInstanceCount",
        "intakeAcceptedCount",
        "intakeReplayCount",
        "restartReadbackStatus",
        "restartReadbackVersion",
        "restartOutcomeVersions",
        "restartReplayCreatedNewState",
        "ownerHistoryUnchangedAcrossRestart",
        "ownerIdentitiesUnchangedAcrossRestart",
        "duplicateOwnerWorkCount",
        "rawDatabaseDsnRetained",
    }
)
IDEA_ADVISE_RECONCILIATION_TEST_NODES = (
    "tests/integration/test_postgres_downstream_submission_runtime.py::test_postgres_advise_reconciliation_is_one_time_and_exact_replay_is_zero_delta",
)
_IDEA_RECONCILIATION_EVIDENCE_FIELDS = frozenset(
    {
        "evidenceClass",
        "databaseBackend",
        "testNodes",
        "testProcessExitCode",
        "testPassedCount",
        "testSourceDigest",
        "ideaRepositoryInstanceCount",
        "firstReconciliationStatus",
        "firstReconciliationAppendedOutcomeCount",
        "exactReplayStatus",
        "exactReplayAppendedOutcomeCount",
        "submissionAttemptCount",
        "retainedOutcomeVersions",
        "ownerIdentityUnchanged",
        "governedTableCountsUnchangedOnReplay",
        "rawDatabaseDsnRetained",
    }
)


def build_advise_intake_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_root: Path | None,
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
    submitted_intent_evidence: Mapping[str, Any],
    owner_realization_evidence: Mapping[str, Any],
    owner_advancement_evidence: Mapping[str, Any],
    owner_restart_evidence: Mapping[str, Any],
    idea_reconciliation_evidence: Mapping[str, Any],
    pre_commit_timeout_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    source_authority = _source_authority(
        repository_root,
        advise_root or repository_root.parent / "lotus-advise",
    )
    runtime_checks = _runtime_checks(
        generated_at_utc=generated_at_utc,
        source_authority=source_authority,
        runtime_mode=runtime_mode,
        receipt_evidence=receipt_evidence,
        submitted_intent_evidence=submitted_intent_evidence,
        owner_realization_evidence=owner_realization_evidence,
        owner_advancement_evidence=owner_advancement_evidence,
        owner_restart_evidence=owner_restart_evidence,
        idea_reconciliation_evidence=idea_reconciliation_evidence,
        pre_commit_timeout_evidence=pre_commit_timeout_evidence,
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
        "ownerReadRoute": ADVISE_REALIZATION_READ_ROUTE,
        "ownerRecoveryRoute": ADVISE_REALIZATION_RECOVERY_ROUTE,
        "ownerReconciliationRoute": ADVISE_PROPOSAL_RECONCILIATION_ROUTE,
        "runtimeMode": runtime_mode,
        "sourceAuthority": source_authority,
        "evidenceRefs": ADVISE_INTAKE_RUNTIME_EVIDENCE_REFS,
        "receiptEvidence": {
            name: dict(receipt_evidence.get(name, {})) for name in _RECEIPT_EVIDENCE_FIELDS
        },
        "submittedIntentEvidence": dict(submitted_intent_evidence),
        "ownerRealizationEvidence": dict(owner_realization_evidence),
        "ownerAdvancementEvidence": dict(owner_advancement_evidence),
        "ownerRestartEvidence": dict(owner_restart_evidence),
        "ideaReconciliationEvidence": dict(idea_reconciliation_evidence),
        "preCommitTimeoutEvidence": dict(pre_commit_timeout_evidence),
        "runtimeChecks": runtime_checks,
        "aggregateBlockersSatisfied": ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": (REQUIRED_ADVISE_PRODUCER_CERTIFICATION_BLOCKERS),
        "nonProofClaims": {
            "ideaOwnedProposalRecordCreated": False,
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
        "ownerReadRoute": ADVISE_REALIZATION_READ_ROUTE,
        "ownerRecoveryRoute": ADVISE_REALIZATION_RECOVERY_ROUTE,
        "ownerReconciliationRoute": ADVISE_PROPOSAL_RECONCILIATION_ROUTE,
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
    submitted_intent = payload.get("submittedIntentEvidence")
    owner_realization = payload.get("ownerRealizationEvidence")
    owner_advancement = payload.get("ownerAdvancementEvidence")
    owner_restart = payload.get("ownerRestartEvidence")
    idea_reconciliation = payload.get("ideaReconciliationEvidence")
    pre_commit_timeout = payload.get("preCommitTimeoutEvidence")
    return (
        isinstance(receipt_evidence, Mapping)
        and intake_receipt_evidence_is_valid(
            receipt_evidence,
            expected_fields=_RECEIPT_EVIDENCE_FIELDS,
            accepted_receipt_is_valid=_accepted_receipt_is_valid,
            replay_receipt_is_valid=_replay_receipt_is_valid,
            rejected_receipt_is_valid=_rejected_receipt_is_valid,
            conflict_receipt_is_valid=_conflict_receipt_is_valid,
            authorization_denied_receipt_is_valid=_authorization_denied_receipt_is_valid,
            tenant_isolation_receipt_is_valid=_tenant_isolation_receipt_is_valid,
        )
        and _same_owner_identity(
            receipt_evidence.get("accepted"), receipt_evidence.get("acceptedReplay")
        )
        and _concurrent_duplicate_converges(receipt_evidence)
        and _owner_realization_matches(
            owner_realization, receipt_evidence.get("accepted"), submitted_intent
        )
        and _owner_advancement_matches(
            owner_advancement, receipt_evidence.get("accepted"), submitted_intent
        )
        and _owner_restart_evidence_is_valid(owner_restart)
        and _owner_restart_source_digest_matches(owner_restart, payload.get("sourceAuthority"))
        and _idea_reconciliation_evidence_is_valid(idea_reconciliation)
        and _idea_reconciliation_source_digest_matches(
            idea_reconciliation, payload.get("sourceAuthority")
        )
        and _pre_commit_timeout_evidence_is_valid(pre_commit_timeout)
    )


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
    return source_safe_intake_receipt_digest(receipt, digest_fields=_RECEIPT_DIGEST_FIELDS)


def _runtime_checks(
    *,
    generated_at_utc: datetime,
    source_authority: tuple[dict[str, str | None], ...],
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
    submitted_intent_evidence: Mapping[str, Any],
    owner_realization_evidence: Mapping[str, Any],
    owner_advancement_evidence: Mapping[str, Any],
    owner_restart_evidence: Mapping[str, Any],
    idea_reconciliation_evidence: Mapping[str, Any],
    pre_commit_timeout_evidence: Mapping[str, Any],
) -> dict[str, bool]:
    owner_advancement_valid = _owner_advancement_matches(
        owner_advancement_evidence,
        receipt_evidence.get("accepted"),
        submitted_intent_evidence,
    )
    return {
        "timezoneAwareGeneratedAtUtc": (
            generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
        ),
        "sourceAuthorityDigestBound": all(
            isinstance(item.get("sha256"), str) and item["sha256"] for item in source_authority
        )
        and _owner_restart_source_digest_matches(owner_restart_evidence, source_authority)
        and _idea_reconciliation_source_digest_matches(
            idea_reconciliation_evidence, source_authority
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
        "replayReceiptObserved": _replay_receipt_is_valid(receipt_evidence.get("acceptedReplay"))
        and _same_owner_identity(
            receipt_evidence.get("accepted"), receipt_evidence.get("acceptedReplay")
        ),
        "rejectedReceiptObserved": _rejected_receipt_is_valid(receipt_evidence.get("rejected")),
        "idempotencyConflictObserved": _conflict_receipt_is_valid(
            receipt_evidence.get("idempotencyConflict")
        ),
        "concurrentDuplicateConvergenceObserved": _concurrent_duplicate_converges(receipt_evidence),
        "ownerRealizationReadbackObserved": _owner_realization_matches(
            owner_realization_evidence,
            receipt_evidence.get("accepted"),
            submitted_intent_evidence,
        ),
        "staleOwnerAdvancementRefused": owner_advancement_valid,
        "correctedOwnerAdvancementObserved": owner_advancement_valid,
        "concurrentOwnerAdvancementConverged": owner_advancement_valid,
        "postgresOwnerRestartReplayObserved": _owner_restart_evidence_is_valid(
            owner_restart_evidence
        ),
        "postgresIdeaReconciliationReplayObserved": (
            _idea_reconciliation_evidence_is_valid(idea_reconciliation_evidence)
        ),
        "timeoutBeforeOwnerCommitObserved": _pre_commit_timeout_evidence_is_valid(
            pre_commit_timeout_evidence
        ),
        "automaticResubmissionPrevented": _pre_commit_timeout_evidence_is_valid(
            pre_commit_timeout_evidence
        ),
        "proposalAuthorityRetained": True,
        "suitabilityAuthorityRetained": True,
        "clientPublicationAuthorityRetained": True,
        "supportedFeatureNotPromoted": True,
    }


def _owner_restart_evidence_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _OWNER_RESTART_EVIDENCE_FIELDS:
        return False
    return (
        value.get("evidenceClass") == EvidenceClass.TEST_EXECUTION.value
        and value.get("databaseBackend") == "postgresql"
        and tuple(value.get("testNodes") or ()) == ADVISE_OWNER_RESTART_TEST_NODES
        and value.get("testProcessExitCode") == 0
        and value.get("testPassedCount") == 2
        and is_sha256(value.get("testSourceDigest"))
        and value.get("ownerRepositoryInstanceCount") == 2
        and value.get("intakeAcceptedCount") == 1
        and value.get("intakeReplayCount") == 1
        and value.get("restartReadbackStatus") == "ADVISORY_REJECTED"
        and value.get("restartReadbackVersion") == 3
        and tuple(value.get("restartOutcomeVersions") or ()) == (1, 2, 3)
        and value.get("restartReplayCreatedNewState") is False
        and value.get("ownerHistoryUnchangedAcrossRestart") is True
        and value.get("ownerIdentitiesUnchangedAcrossRestart") is True
        and value.get("duplicateOwnerWorkCount") == 0
        and value.get("rawDatabaseDsnRetained") is False
    )


def _owner_restart_source_digest_matches(value: object, source_authority: object) -> bool:
    if not isinstance(value, Mapping) or not isinstance(source_authority, (tuple, list)):
        return False
    expected_ref = (
        "../lotus-advise/tests/integration/advisory/engine/"
        "test_engine_proposal_repository_postgres_integration.py"
    )
    expected_digest = str(value.get("testSourceDigest") or "").removeprefix("sha256:")
    return any(
        isinstance(item, Mapping)
        and item.get("repository") == "lotus-advise"
        and item.get("ref") == expected_ref
        and item.get("sha256") == expected_digest
        for item in source_authority
    )


def _idea_reconciliation_evidence_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _IDEA_RECONCILIATION_EVIDENCE_FIELDS:
        return False
    return (
        value.get("evidenceClass") == EvidenceClass.TEST_EXECUTION.value
        and value.get("databaseBackend") == "postgresql"
        and tuple(value.get("testNodes") or ()) == IDEA_ADVISE_RECONCILIATION_TEST_NODES
        and value.get("testProcessExitCode") == 0
        and value.get("testPassedCount") == 1
        and is_sha256(value.get("testSourceDigest"))
        and value.get("ideaRepositoryInstanceCount") == 2
        and value.get("firstReconciliationStatus") == "accepted"
        and value.get("firstReconciliationAppendedOutcomeCount") == 3
        and value.get("exactReplayStatus") == "replayed"
        and value.get("exactReplayAppendedOutcomeCount") == 0
        and value.get("submissionAttemptCount") == 1
        and tuple(value.get("retainedOutcomeVersions") or ()) == (1, 2, 3)
        and value.get("ownerIdentityUnchanged") is True
        and value.get("governedTableCountsUnchangedOnReplay") is True
        and value.get("rawDatabaseDsnRetained") is False
    )


def _idea_reconciliation_source_digest_matches(value: object, source_authority: object) -> bool:
    if not isinstance(value, Mapping) or not isinstance(source_authority, (tuple, list)):
        return False
    expected_ref = "tests/integration/test_postgres_downstream_submission_runtime.py"
    expected_digest = str(value.get("testSourceDigest") or "").removeprefix("sha256:")
    return any(
        isinstance(item, Mapping)
        and item.get("repository") == "lotus-idea"
        and item.get("ref") == expected_ref
        and item.get("sha256") == expected_digest
        for item in source_authority
    )


def _owner_advancement_matches(value: object, accepted: object, submitted: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _OWNER_ADVANCEMENT_EVIDENCE_FIELDS:
        return False
    if not isinstance(accepted, Mapping):
        return False
    if not isinstance(submitted, Mapping) or set(submitted) != _SUBMITTED_INTENT_FIELDS:
        return False
    return (
        all(
            is_sha256(value.get(field))
            for field in (
                "ownerIdentityDigest",
                "scopeDigest",
                "sourceIntentDigest",
                "sourceEvidenceFingerprint",
            )
        )
        and value.get("ownerIdentityDigest") == accepted.get("ownerIdentityDigest")
        and value.get("scopeDigest") == accepted.get("scopeDigest")
        and value.get("scopeDigest") == submitted.get("scopeDigest")
        and value.get("sourceIntentDigest") == submitted.get("sourceIntentDigest")
        and value.get("sourceEvidenceFingerprint") == accepted.get("sourceEvidenceFingerprint")
        and value.get("linkedStatusCode") == 200
        and value.get("linkedSourceEventVersion") == 2
        and value.get("staleCorrectionStatusCode") == 409
        and tuple(value.get("staleCorrectionReasonCodes") or ())
        == (_OWNER_VERSION_CONFLICT_REASON,)
        and value.get("sourceEventVersionAfterRefusal") == 2
        and sorted(value.get("concurrentStatusCodes") or ()) == [200, 200]
        and sorted(value.get("concurrentSourceEventVersions") or ()) == [3, 3]
        and value.get("finalStatusCode") == 200
        and value.get("finalStatus") == "ADVISORY_REJECTED"
        and value.get("finalSourceEventVersion") == 3
        and tuple(value.get("finalOutcomeVersions") or ()) == (1, 2, 3)
        and tuple(value.get("finalOutcomeStatuses") or ())
        == ("ACCEPTED_FOR_REVIEW", "PROPOSAL_LINKED", "ADVISORY_REJECTED")
        and value.get("proposalIdentityPresent") is True
        and value.get("proposalRecordCreated") is True
        and all(
            value.get(field) is False
            for field in (
                "suitabilityAuthorityGranted",
                "orderCreated",
                "clientPublicationAuthorized",
            )
        )
    )


def _pre_commit_timeout_evidence_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _PRE_COMMIT_TIMEOUT_EVIDENCE_FIELDS:
        return False
    expected_reason_codes = (_OWNER_REALIZATION_NOT_FOUND_REASON,)
    return (
        value.get("failureStage") == "before_owner_request_dispatch"
        and is_sha256(value.get("sourceIntentDigest"))
        and is_sha256(value.get("scopeDigest"))
        and value.get("ownerLookupStatusCode") == 404
        and tuple(value.get("ownerLookupReasonCodes") or ()) == expected_reason_codes
        and value.get("repeatedOwnerLookupStatusCode") == 404
        and tuple(value.get("repeatedOwnerLookupReasonCodes") or ()) == expected_reason_codes
        and value.get("downstreamPostAttemptCount") == 0
        and value.get("automaticResubmissionAttemptCount") == 0
        and value.get("ownerStateObserved") is False
    )


def _accepted_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED",
        accepted=True,
        replay=False,
        reason_codes=("idea_intake_receipt_accepted",),
    ) and _receipt_has_owner_identity(value)


def _replay_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        intake_status="ACCEPTED_REPLAYED",
        accepted=True,
        replay=True,
        reason_codes=("idea_intake_receipt_replayed",),
    ) and _receipt_has_owner_identity(value)


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


def _receipt_has_owner_identity(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and all(
            isinstance(value.get(field), str) and bool(value.get(field))
            for field in (
                "reviewWorkStatus",
                "realizationStatus",
            )
        )
        and all(
            is_sha256(value.get(field))
            for field in (
                "ownerIdentityDigest",
                "scopeDigest",
                "sourceEvidenceFingerprint",
            )
        )
        and value.get("sourceEventVersion") == 1
    )


def _concurrent_duplicate_converges(receipts: Mapping[str, Any]) -> bool:
    accepted = receipts.get("concurrentAccepted")
    replay = receipts.get("concurrentReplay")
    return (
        _accepted_receipt_is_valid(accepted)
        and _replay_receipt_is_valid(replay)
        and _same_owner_identity(accepted, replay)
    )


def _same_owner_identity(left: object, right: object) -> bool:
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return False
    return all(
        left.get(field) == right.get(field)
        for field in (
            "ownerIdentityDigest",
            "scopeDigest",
            "sourceEvidenceFingerprint",
            "sourceEventVersion",
        )
    )


_OWNER_REALIZATION_FIELDS = frozenset(
    {
        "statusCode",
        "ownerIdentityDigest",
        "scopeDigest",
        "reviewWorkStatus",
        "sourceIntentDigest",
        "sourceEvidenceFingerprint",
        "currentStatus",
        "currentSourceEventVersion",
        "proposalIdentityPresent",
        "proposalRecordCreated",
        "suitabilityAuthorityGranted",
        "orderCreated",
        "clientPublicationAuthorized",
        "outcomes",
    }
)


_SUBMITTED_INTENT_FIELDS = frozenset({"scopeDigest", "sourceIntentDigest"})


def _owner_realization_matches(value: object, accepted: object, submitted: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _OWNER_REALIZATION_FIELDS:
        return False
    if not isinstance(accepted, Mapping):
        return False
    if not isinstance(submitted, Mapping) or set(submitted) != _SUBMITTED_INTENT_FIELDS:
        return False
    if not all(is_sha256(submitted.get(field)) for field in _SUBMITTED_INTENT_FIELDS):
        return False
    if not all(
        is_sha256(value.get(field))
        for field in (
            "ownerIdentityDigest",
            "scopeDigest",
            "sourceIntentDigest",
            "sourceEvidenceFingerprint",
        )
    ):
        return False
    outcomes = value.get("outcomes")
    return (
        value.get("statusCode") == 200
        and value.get("proposalIdentityPresent") is False
        and all(
            value.get(field) is False
            for field in (
                "proposalRecordCreated",
                "suitabilityAuthorityGranted",
                "orderCreated",
                "clientPublicationAuthorized",
            )
        )
        and value.get("ownerIdentityDigest") == accepted.get("ownerIdentityDigest")
        and value.get("reviewWorkStatus") == accepted.get("reviewWorkStatus")
        and value.get("scopeDigest") == accepted.get("scopeDigest")
        and value.get("scopeDigest") == submitted.get("scopeDigest")
        and value.get("sourceIntentDigest") == submitted.get("sourceIntentDigest")
        and value.get("sourceEvidenceFingerprint") == accepted.get("sourceEvidenceFingerprint")
        and value.get("currentStatus") == accepted.get("realizationStatus")
        and value.get("currentSourceEventVersion") == accepted.get("sourceEventVersion")
        and isinstance(outcomes, list)
        and len(outcomes) == 1
        and isinstance(outcomes[0], Mapping)
        and outcomes[0].get("sourceEventVersion") == value.get("currentSourceEventVersion")
        and outcomes[0].get("status") == value.get("currentStatus")
        and outcomes[0].get("ownerWorkBound") is True
        and outcomes[0].get("proposalIdentityPresent") is False
        and outcomes[0].get("terminal") is False
    )


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
    return intake_receipt_matches(
        value,
        receipt_fields=_RECEIPT_FIELDS,
        status_code=status_code,
        intake_status=intake_status,
        accepted=accepted,
        replay=replay,
        reason_codes=reason_codes,
        digest=source_safe_receipt_digest,
        retained_false_fields=_RETAINED_FALSE_RECEIPT_FIELDS,
    )


def _source_authority(
    repository_root: Path,
    advise_root: Path,
) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(
        (
            *tuple(
                SourceAuthoritySource(
                    ADVISE_ROUTE_PROFILE.owner_repository,
                    f"../{ADVISE_ROUTE_PROFILE.owner_repository}/{ref}",
                    advise_root / ref,
                )
                for ref in ADVISE_INTAKE_RUNTIME_SOURCE_REFS
            ),
            *tuple(
                SourceAuthoritySource("lotus-idea", ref, repository_root / ref)
                for ref in IDEA_ADVISE_RECONCILIATION_SOURCE_REFS
            ),
        )
    )


def _expected_source_authority() -> tuple[SourceAuthoritySource, ...]:
    return (
        *tuple(
            SourceAuthoritySource(
                ADVISE_ROUTE_PROFILE.owner_repository,
                f"../{ADVISE_ROUTE_PROFILE.owner_repository}/{ref}",
                Path(ref),
            )
            for ref in ADVISE_INTAKE_RUNTIME_SOURCE_REFS
        ),
        *tuple(
            SourceAuthoritySource("lotus-idea", ref, Path(ref))
            for ref in IDEA_ADVISE_RECONCILIATION_SOURCE_REFS
        ),
    )


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=_expected_source_authority(),
    )
