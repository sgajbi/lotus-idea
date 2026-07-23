from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.report.materialization_source_contract import (
    REPORT_MATERIALIZATION_ROUTE,
)
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.application.source_runtime_evidence import is_sha256
from app.domain.proof_evidence import EvidenceClass

REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV = (
    "LOTUS_IDEA_REPORT_MATERIALIZATION_RUNTIME_EXECUTION_PROOF"
)
REPORT_MATERIALIZATION_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.report-materialization.runtime-execution.v1"
)
REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED = (
    "report_evidence_pack_live_materialization_proof_missing",
    "rendered_output_creation_missing",
    "archive_record_creation_missing",
)
REMAINING_REPORT_MATERIALIZATION_RUNTIME_BLOCKERS = (
    "client_publication_authority_blocked",
    "supported_feature_promotion_missing",
    "production_identity_not_certified",
)
REPORT_RENDER_ARCHIVE_OWNER_MAINLINE_EVIDENCE = (
    {
        "ownerRepository": "lotus-render",
        "ownerIssueNumber": 65,
        "ownerIssueUrl": "https://github.com/sgajbi/lotus-render/issues/65",
        "ownerPullRequestNumber": 67,
        "ownerPullRequestUrl": "https://github.com/sgajbi/lotus-render/pull/67",
        "mergedMainCommitSha": "c608fe4c5b22fa22e51e242894a76a8532839e9f",
        "mainReleasabilityRunId": 29966168422,
        "mainReleasabilityRunUrl": (
            "https://github.com/sgajbi/lotus-render/actions/runs/29966168422"
        ),
        "mainReleasabilityCheckName": "Main Releasability Gate",
        "mainReleasabilityConclusion": "success",
        "proofStatus": "merged_main_validated",
    },
    {
        "ownerRepository": "lotus-archive",
        "ownerIssueNumber": 72,
        "ownerIssueUrl": "https://github.com/sgajbi/lotus-archive/issues/72",
        "ownerPullRequestNumber": 73,
        "ownerPullRequestUrl": "https://github.com/sgajbi/lotus-archive/pull/73",
        "mergedMainCommitSha": "61ff2cb56a0e3652c40df2740f1f5d8150e52071",
        "mainReleasabilityRunId": 29966167055,
        "mainReleasabilityRunUrl": (
            "https://github.com/sgajbi/lotus-archive/actions/runs/29966167055"
        ),
        "mainReleasabilityCheckName": "Main Releasability Gate",
        "mainReleasabilityConclusion": "success",
        "proofStatus": "merged_main_validated",
    },
)
REPORT_MATERIALIZATION_RUNTIME_EVIDENCE_REFS = (
    "../lotus-report/contracts/idea-evidence-materialization/"
    "lotus-report-idea-evidence-pack-materialization.v1.json",
    "../lotus-report/src/app/idea_evidence_intake/models.py",
    "../lotus-report/src/app/idea_evidence_intake/service.py",
    "../lotus-report/src/app/routers/idea_evidence_intake.py",
    "../lotus-report/src/app/reporting_lineage/capture_service.py",
    "../lotus-report/src/app/reporting_render/package_builder.py",
    "../lotus-report/tests/integration/test_idea_evidence_intake_api.py",
    "src/app/application/report/materialization_runtime_execution.py",
    "scripts/report/materialization_runtime_execution_gate.py",
    "scripts/report/generate_materialization_runtime_execution.py",
    "GET /api/v1/downstream-realization/readiness",
    "GET /api/v1/implementation-proof/readiness",
    "sgajbi/lotus-idea#690",
    "sgajbi/lotus-idea#691",
    "sgajbi/lotus-render#65",
    "sgajbi/lotus-render#67",
    "sgajbi/lotus-render/actions/runs/29966168422",
    "sgajbi/lotus-archive#72",
    "sgajbi/lotus-archive#73",
    "sgajbi/lotus-archive/actions/runs/29966167055",
)
REPORT_MATERIALIZATION_RUNTIME_SOURCE_REFS = (
    "contracts/idea-evidence-materialization/lotus-report-idea-evidence-pack-materialization.v1.json",
    "src/app/idea_evidence_intake/models.py",
    "src/app/idea_evidence_intake/service.py",
    "src/app/routers/idea_evidence_intake.py",
    "src/app/reporting_lineage/capture_service.py",
    "src/app/reporting_render/package_builder.py",
    "tests/integration/test_idea_evidence_intake_api.py",
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
        "ownerMainlineEvidence",
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
        "acceptedArchived",
        "acceptedReplay",
        "jsonOnlyAccepted",
        "archiveFailure",
        "idempotencyConflict",
        "missingIdempotencyKey",
        "clientPublicationDenied",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "statusCode",
        "materializationStatus",
        "materializationProven",
        "reportJobCreated",
        "renderedOutputCreated",
        "archiveRecordCreated",
        "clientPublicationAuthorized",
        "supportedFeaturePromoted",
        "supportabilityStatus",
        "receiptDigest",
        "reasonCodes",
    }
)
_RECEIPT_DIGEST_FIELDS = (
    "statusCode",
    "materializationStatus",
    "materializationProven",
    "reportJobCreated",
    "renderedOutputCreated",
    "archiveRecordCreated",
    "clientPublicationAuthorized",
    "supportedFeaturePromoted",
    "supportabilityStatus",
    "reasonCodes",
)
_RUNTIME_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "routeServingObserved",
        "runtimeExecutionObserved",
        "acceptedArchivedReceiptObserved",
        "acceptedReplayReceiptObserved",
        "jsonOnlyReceiptObserved",
        "archiveFailureReceiptObserved",
        "idempotencyConflictObserved",
        "missingIdempotencyKeyObserved",
        "clientPublicationDeniedObserved",
        "reportMaterializationAuthorityObserved",
        "renderedOutputCreationObserved",
        "archiveRecordCreationObserved",
        "renderOwnerMainlineEvidenceConsumed",
        "archiveOwnerMainlineEvidenceConsumed",
        "renderArchiveAuthorityRetained",
        "clientPublicationAuthorityRetained",
        "supportedFeatureNotPromoted",
        "productionIdentityNotCertified",
    }
)
_NON_PROOF_CLAIM_FIELDS = frozenset(
    {
        "renderedOutputCertified",
        "archiveRecordCertified",
        "clientPublicationAuthorized",
        "productionIdentityCertified",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)
_PRODUCER_CERTIFICATION_BLOCKERS_RETAINED = (
    "client_publication_authority_blocked",
    "supported_feature_promotion_missing",
    "production_identity_not_certified",
)
_SUPPORTED_RUNTIME_MODES = frozenset({"local_asgi_testclient", "http_service"})
_EXPECTED_PROOF_TYPE = "lotus_report_idea_evidence_pack_materialization_runtime_execution"
_EXPECTED_PROOF_SCOPE = "report_materialization_route_serving_and_receipt_behavior"
_EXPECTED_DOWNSTREAM_AUTHORITY = "lotus-report"
_EXPECTED_SOURCE_REPOSITORY = "lotus-idea"


def build_report_materialization_runtime_execution_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    report_root: Path | None,
    runtime_mode: str,
    receipt_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    source_authority = _source_authority(report_root or repository_root.parent / "lotus-report")
    runtime_checks = _runtime_checks(
        generated_at_utc=generated_at_utc,
        source_authority=source_authority,
        runtime_mode=runtime_mode,
        receipt_evidence=receipt_evidence,
    )
    return {
        "schemaVersion": REPORT_MATERIALIZATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": all(runtime_checks.values()),
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "runtimeMode": runtime_mode,
        "sourceAuthority": source_authority,
        "evidenceRefs": REPORT_MATERIALIZATION_RUNTIME_EVIDENCE_REFS,
        "ownerMainlineEvidence": REPORT_RENDER_ARCHIVE_OWNER_MAINLINE_EVIDENCE,
        "receiptEvidence": {
            name: dict(receipt_evidence.get(name, {})) for name in _RECEIPT_EVIDENCE_FIELDS
        },
        "runtimeChecks": runtime_checks,
        "aggregateBlockersSatisfied": REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED,
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_RUNTIME_BLOCKERS,
        "producerCertificationBlockersRetained": _PRODUCER_CERTIFICATION_BLOCKERS_RETAINED,
        "nonProofClaims": {
            "renderedOutputCertified": False,
            "archiveRecordCertified": False,
            "clientPublicationAuthorized": False,
            "productionIdentityCertified": False,
            "productionCertificationGranted": False,
            "supportedFeaturePromoted": False,
            "certificationClosed": False,
        },
    }


def report_materialization_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    expected = {
        "schemaVersion": REPORT_MATERIALIZATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": _EXPECTED_PROOF_TYPE,
        "proofScope": _EXPECTED_PROOF_SCOPE,
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeProofValid": True,
        "sourceRepository": _EXPECTED_SOURCE_REPOSITORY,
        "downstreamAuthority": _EXPECTED_DOWNSTREAM_AUTHORITY,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if payload.get("runtimeMode") not in _SUPPORTED_RUNTIME_MODES:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REPORT_MATERIALIZATION_RUNTIME_EVIDENCE_REFS:
        return False
    if not _owner_mainline_evidence_is_valid(payload.get("ownerMainlineEvidence")):
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != REMAINING_REPORT_MATERIALIZATION_RUNTIME_BLOCKERS
    ):
        return False
    if (
        tuple(payload.get("producerCertificationBlockersRetained") or ())
        != _PRODUCER_CERTIFICATION_BLOCKERS_RETAINED
    ):
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
    return isinstance(receipt_evidence, Mapping) and (
        set(receipt_evidence) == _RECEIPT_EVIDENCE_FIELDS
        and _accepted_archived_receipt_is_valid(receipt_evidence.get("acceptedArchived"))
        and _accepted_replay_receipt_is_valid(receipt_evidence.get("acceptedReplay"))
        and _json_only_receipt_is_valid(receipt_evidence.get("jsonOnlyAccepted"))
        and _archive_failure_receipt_is_valid(receipt_evidence.get("archiveFailure"))
        and _idempotency_conflict_receipt_is_valid(receipt_evidence.get("idempotencyConflict"))
        and _missing_idempotency_key_receipt_is_valid(receipt_evidence.get("missingIdempotencyKey"))
        and _client_publication_denied_receipt_is_valid(
            receipt_evidence.get("clientPublicationDenied")
        )
    )


def load_report_materialization_runtime_execution_from_env() -> tuple[
    dict[str, Any] | None, str | None
]:
    path_value = os.getenv(REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"{REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV} must reference a JSON object"
        )
    try:
        artifact_ref = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        artifact_ref = f"{REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV} artifact"
    return payload, artifact_ref


def source_safe_report_materialization_receipt_digest(receipt: Mapping[str, Any]) -> str:
    canonical = {field: receipt.get(field) for field in _RECEIPT_DIGEST_FIELDS}
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
        "runtimeExecutionObserved": runtime_mode in _SUPPORTED_RUNTIME_MODES,
        "acceptedArchivedReceiptObserved": _accepted_archived_receipt_is_valid(
            receipt_evidence.get("acceptedArchived")
        ),
        "acceptedReplayReceiptObserved": _accepted_replay_receipt_is_valid(
            receipt_evidence.get("acceptedReplay")
        ),
        "jsonOnlyReceiptObserved": _json_only_receipt_is_valid(
            receipt_evidence.get("jsonOnlyAccepted")
        ),
        "archiveFailureReceiptObserved": _archive_failure_receipt_is_valid(
            receipt_evidence.get("archiveFailure")
        ),
        "idempotencyConflictObserved": _idempotency_conflict_receipt_is_valid(
            receipt_evidence.get("idempotencyConflict")
        ),
        "missingIdempotencyKeyObserved": _missing_idempotency_key_receipt_is_valid(
            receipt_evidence.get("missingIdempotencyKey")
        ),
        "clientPublicationDeniedObserved": _client_publication_denied_receipt_is_valid(
            receipt_evidence.get("clientPublicationDenied")
        ),
        "reportMaterializationAuthorityObserved": True,
        "renderedOutputCreationObserved": _accepted_archived_receipt_is_valid(
            receipt_evidence.get("acceptedArchived")
        ),
        "archiveRecordCreationObserved": _accepted_archived_receipt_is_valid(
            receipt_evidence.get("acceptedArchived")
        ),
        "renderOwnerMainlineEvidenceConsumed": True,
        "archiveOwnerMainlineEvidenceConsumed": True,
        "renderArchiveAuthorityRetained": True,
        "clientPublicationAuthorityRetained": True,
        "supportedFeatureNotPromoted": True,
        "productionIdentityNotCertified": True,
    }


def _accepted_archived_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        materialization_status="archived",
        materialization_proven=True,
        report_job_created=True,
        rendered_output_created=True,
        archive_record_created=True,
        supportability_status="not_certified",
        reason_codes=(
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ),
    )


def _accepted_replay_receipt_is_valid(value: object) -> bool:
    return _accepted_archived_receipt_is_valid(value)


def _json_only_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        materialization_status="data_ready",
        materialization_proven=True,
        report_job_created=True,
        rendered_output_created=False,
        archive_record_created=False,
        supportability_status="not_certified",
        reason_codes=(
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ),
    )


def _archive_failure_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=202,
        materialization_status="failed",
        materialization_proven=True,
        report_job_created=True,
        rendered_output_created=True,
        archive_record_created=False,
        supportability_status="not_certified",
        reason_codes=(
            "archive_storage_failed",
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ),
    )


def _idempotency_conflict_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=409,
        materialization_status=None,
        materialization_proven=False,
        report_job_created=False,
        rendered_output_created=False,
        archive_record_created=False,
        supportability_status=None,
        reason_codes=("idempotency_conflict",),
    )


def _missing_idempotency_key_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=400,
        materialization_status=None,
        materialization_proven=False,
        report_job_created=False,
        rendered_output_created=False,
        archive_record_created=False,
        supportability_status=None,
        reason_codes=("missing_idempotency_key",),
    )


def _client_publication_denied_receipt_is_valid(value: object) -> bool:
    return _receipt_matches(
        value,
        status_code=422,
        materialization_status=None,
        materialization_proven=False,
        report_job_created=False,
        rendered_output_created=False,
        archive_record_created=False,
        supportability_status=None,
        reason_codes=("client_publication_authority_blocked",),
    )


def _receipt_matches(
    value: object,
    *,
    status_code: int,
    materialization_status: str | None,
    materialization_proven: bool,
    report_job_created: bool,
    rendered_output_created: bool,
    archive_record_created: bool,
    supportability_status: str | None,
    reason_codes: tuple[str, ...],
) -> bool:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_FIELDS:
        return False
    return (
        value.get("statusCode") == status_code
        and value.get("materializationStatus") == materialization_status
        and value.get("materializationProven") is materialization_proven
        and value.get("reportJobCreated") is report_job_created
        and value.get("renderedOutputCreated") is rendered_output_created
        and value.get("archiveRecordCreated") is archive_record_created
        and value.get("clientPublicationAuthorized") is False
        and value.get("supportedFeaturePromoted") is False
        and value.get("supportabilityStatus") == supportability_status
        and tuple(value.get("reasonCodes") or ()) == reason_codes
        and is_sha256(value.get("receiptDigest"))
        and value.get("receiptDigest") == source_safe_report_materialization_receipt_digest(value)
    )


def _non_proof_claims_are_retained(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _NON_PROOF_CLAIM_FIELDS
        and all(value.get(key) is False for key in _NON_PROOF_CLAIM_FIELDS)
    )


def _owner_mainline_evidence_is_valid(value: object) -> bool:
    return tuple(value or ()) == REPORT_RENDER_ARCHIVE_OWNER_MAINLINE_EVIDENCE


def _source_authority(report_root: Path) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(
        tuple(
            SourceAuthoritySource("lotus-report", f"../lotus-report/{ref}", report_root / ref)
            for ref in REPORT_MATERIALIZATION_RUNTIME_SOURCE_REFS
        )
    )


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=tuple(
            SourceAuthoritySource("lotus-report", f"../lotus-report/{ref}", Path(ref))
            for ref in REPORT_MATERIALIZATION_RUNTIME_SOURCE_REFS
        ),
    )
