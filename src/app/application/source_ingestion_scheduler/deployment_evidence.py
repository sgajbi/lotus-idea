from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import re
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import format_utc, require_aware, sha256_json
from app.domain.proof_evidence import (
    EvidenceClass,
    evidence_class_can_clear,
    is_timezone_aware_datetime_text,
    parse_timezone_aware_datetime,
)


SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV = (
    "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE"
)
SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_SCHEMA_VERSION = (
    "lotus-idea.source-ingestion.scheduled-worker-deployment-evidence.v1"
)
SCHEDULED_WORKER_DEPLOYMENT_BLOCKER = "scheduled_worker_deploy_proof_missing"
SCHEDULED_WORKER_DEPLOYMENT_BLOCKERS_PRESERVED = (
    "live_core_source_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_BOUNDED_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "evidenceClass",
    "requiredEvidenceClass",
    "repository",
    "generatedAtUtc",
    "sourceCommitSha",
    "image",
    "target",
    "controller",
    "workload",
    "schedulerConfiguration",
    "deploymentReceiptDigest",
    "deploymentEvidenceValid",
    "blockerEffect",
    "nonProofClaims",
    "supportedFeaturePromoted",
    "proofClosed",
}


def build_scheduled_worker_deployment_evidence_payload(
    *,
    generated_at_utc: datetime,
    source_commit_sha: str,
    image_digest: str,
    target_environment: str,
    environment_class: str,
    controller_workflow: str,
    controller_run_id: str,
    controller_run_attempt: int,
    deployment_actor: str,
    workload_identity: str,
    rollout_completed_at_utc: datetime,
    scheduler_configuration_digest: str,
    source_contract_digest: str,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    require_aware(rollout_completed_at_utc, "rollout_completed_at_utc")
    deployment_material = {
        "sourceCommitSha": source_commit_sha,
        "image": {
            "reference": f"ghcr.io/sgajbi/lotus-idea@{image_digest}",
            "digest": image_digest,
            "gitCommitSha": source_commit_sha,
        },
        "target": {
            "environment": target_environment,
            "environmentClass": environment_class,
        },
        "controller": {
            "repository": "sgajbi/lotus-idea",
            "workflow": controller_workflow,
            "runId": controller_run_id,
            "runAttempt": controller_run_attempt,
            "actor": deployment_actor,
        },
        "workload": {
            "identity": workload_identity,
            "rolloutStatus": "completed",
            "rolloutCompletedAtUtc": format_utc(rollout_completed_at_utc),
            "observedImageDigest": image_digest,
            "observedGitCommitSha": source_commit_sha,
        },
        "schedulerConfiguration": {
            "identityDigest": scheduler_configuration_digest,
            "sourceContractDigest": source_contract_digest,
        },
    }
    return {
        "schemaVersion": SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_SCHEMA_VERSION,
        "evidenceClass": EvidenceClass.DEPLOYMENT.value,
        "requiredEvidenceClass": EvidenceClass.DEPLOYMENT.value,
        "repository": "lotus-idea",
        "generatedAtUtc": format_utc(generated_at_utc),
        **deployment_material,
        "deploymentReceiptDigest": sha256_json(deployment_material),
        "deploymentEvidenceValid": True,
        "blockerEffect": {
            "clears": [SCHEDULED_WORKER_DEPLOYMENT_BLOCKER],
            "preserves": list(SCHEDULED_WORKER_DEPLOYMENT_BLOCKERS_PRESERVED),
        },
        "nonProofClaims": {
            "scheduledExecutionObserved": False,
            "liveCoreSourceCertified": False,
            "productionCertified": False,
        },
        "supportedFeaturePromoted": False,
        "proofClosed": True,
    }


def scheduled_worker_deployment_evidence_is_valid(payload: Mapping[str, Any]) -> bool:
    if not _has_exact_keys(payload, _TOP_LEVEL_KEYS):
        return False
    if payload.get("schemaVersion") != SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_SCHEMA_VERSION:
        return False
    if payload.get("evidenceClass") != EvidenceClass.DEPLOYMENT.value:
        return False
    if payload.get("requiredEvidenceClass") != EvidenceClass.DEPLOYMENT.value:
        return False
    if not evidence_class_can_clear(
        actual=EvidenceClass.DEPLOYMENT,
        required=EvidenceClass.DEPLOYMENT,
    ):
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if payload.get("deploymentEvidenceValid") is not True:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not True:
        return False
    source_commit_sha = payload.get("sourceCommitSha")
    if not isinstance(source_commit_sha, str) or not _SHA.fullmatch(source_commit_sha):
        return False
    provenance = payload.get(AGGREGATE_PROOF_PROVENANCE_KEY)
    if isinstance(provenance, Mapping) and provenance.get("sourceRevision") != source_commit_sha:
        return False
    if not _image_is_valid(payload.get("image"), source_commit_sha=source_commit_sha):
        return False
    if not _target_is_valid(payload.get("target")):
        return False
    if not _controller_is_valid(payload.get("controller")):
        return False
    image = payload["image"]
    assert isinstance(image, Mapping)
    image_digest = image["digest"]
    if not _workload_is_valid(
        payload.get("workload"),
        source_commit_sha=source_commit_sha,
        image_digest=image_digest,
    ):
        return False
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    workload = payload["workload"]
    assert isinstance(workload, Mapping)
    rollout_completed_at_utc = parse_timezone_aware_datetime(workload.get("rolloutCompletedAtUtc"))
    if (
        generated_at_utc is None
        or rollout_completed_at_utc is None
        or rollout_completed_at_utc > generated_at_utc
    ):
        return False
    if not _scheduler_configuration_is_valid(payload.get("schedulerConfiguration")):
        return False
    if payload.get("blockerEffect") != {
        "clears": [SCHEDULED_WORKER_DEPLOYMENT_BLOCKER],
        "preserves": list(SCHEDULED_WORKER_DEPLOYMENT_BLOCKERS_PRESERVED),
    }:
        return False
    if payload.get("nonProofClaims") != {
        "scheduledExecutionObserved": False,
        "liveCoreSourceCertified": False,
        "productionCertified": False,
    }:
        return False
    deployment_material = {
        key: payload[key]
        for key in (
            "sourceCommitSha",
            "image",
            "target",
            "controller",
            "workload",
            "schedulerConfiguration",
        )
    }
    return payload.get("deploymentReceiptDigest") == sha256_json(deployment_material)


def scheduled_worker_deployment_matches_source_contract(
    deployment_evidence: Mapping[str, Any],
    source_contract: Mapping[str, Any],
) -> bool:
    if not scheduled_worker_deployment_evidence_is_valid(deployment_evidence):
        return False
    scheduler_configuration = deployment_evidence.get("schedulerConfiguration")
    if not isinstance(scheduler_configuration, Mapping):
        return False
    return scheduler_configuration.get("identityDigest") == source_contract.get(
        "schedulerConfigurationDigest"
    ) and scheduler_configuration.get("sourceContractDigest") == source_contract.get(
        "sourceContractDigest"
    )


def _image_is_valid(value: object, *, source_commit_sha: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "reference",
        "digest",
        "gitCommitSha",
    }:
        return False
    digest = value.get("digest")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        return False
    if value.get("reference") != f"ghcr.io/sgajbi/lotus-idea@{digest}":
        return False
    return value.get("gitCommitSha") == source_commit_sha


def _target_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "environment",
        "environmentClass",
    }:
        return False
    environment = value.get("environment")
    if not isinstance(environment, str) or not _BOUNDED_NAME.fullmatch(environment):
        return False
    return value.get("environmentClass") in {
        "development",
        "test",
        "staging",
        "production",
    }


def _controller_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "repository",
        "workflow",
        "runId",
        "runAttempt",
        "actor",
    }:
        return False
    if value.get("repository") != "sgajbi/lotus-idea":
        return False
    for key in ("workflow", "actor"):
        field = value.get(key)
        if not isinstance(field, str) or not _BOUNDED_NAME.fullmatch(field):
            return False
    run_id = value.get("runId")
    if not isinstance(run_id, str) or not run_id.isdigit():
        return False
    attempt = value.get("runAttempt")
    return isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 0


def _workload_is_valid(
    value: object,
    *,
    source_commit_sha: str,
    image_digest: object,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "identity",
        "rolloutStatus",
        "rolloutCompletedAtUtc",
        "observedImageDigest",
        "observedGitCommitSha",
    }:
        return False
    identity = value.get("identity")
    if not isinstance(identity, str) or not _BOUNDED_NAME.fullmatch(identity):
        return False
    if value.get("rolloutStatus") != "completed":
        return False
    if not is_timezone_aware_datetime_text(value.get("rolloutCompletedAtUtc")):
        return False
    if value.get("observedImageDigest") != image_digest:
        return False
    return value.get("observedGitCommitSha") == source_commit_sha


def _scheduler_configuration_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "identityDigest",
        "sourceContractDigest",
    }:
        return False
    return all(
        isinstance(value.get(key), str) and _DIGEST.fullmatch(value[key])
        for key in ("identityDigest", "sourceContractDigest")
    )


def _has_exact_keys(payload: Mapping[str, Any], expected: set[str]) -> bool:
    return set(payload) in (expected, expected | {AGGREGATE_PROOF_PROVENANCE_KEY})
