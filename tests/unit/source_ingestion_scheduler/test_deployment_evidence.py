from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from app.application.runtime_evidence import sha256_json
from app.application.source_ingestion_scheduler import (
    scheduled_worker_deployment_matches_source_contract,
    scheduled_worker_deployment_evidence_is_valid,
)
from tests.support.source_ingestion_scheduler_evidence import (
    deployment_evidence,
    source_contract,
)


ROOT = Path(__file__).resolve().parents[3]


def test_deployment_evidence_binds_image_environment_controller_and_rollout() -> None:
    payload = deployment_evidence(repository_root=ROOT)

    assert scheduled_worker_deployment_evidence_is_valid(payload)
    assert payload["evidenceClass"] == "deployment"
    assert payload["requiredEvidenceClass"] == "deployment"
    assert payload["blockerEffect"]["clears"] == [
        "scheduled_worker_deploy_proof_missing"
    ]
    assert payload["image"]["reference"] == (
        f"ghcr.io/sgajbi/lotus-idea@{payload['image']['digest']}"
    )
    assert payload["workload"]["observedImageDigest"] == payload["image"]["digest"]
    assert payload["workload"]["observedGitCommitSha"] == payload["sourceCommitSha"]
    assert payload["nonProofClaims"]["scheduledExecutionObserved"] is False
    assert payload["nonProofClaims"]["productionCertified"] is False
    assert scheduled_worker_deployment_matches_source_contract(
        payload,
        source_contract(repository_root=ROOT),
    )


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("evidenceClass",), "source_contract"),
        (("requiredEvidenceClass",), "runtime_execution"),
        (("image", "reference"), "ghcr.io/sgajbi/lotus-idea:latest"),
        (("image", "digest"), f"sha256:{'c' * 64}"),
        (("image", "gitCommitSha"), "c" * 40),
        (("target", "environment"), ""),
        (("target", "environmentClass"), "unknown"),
        (("controller", "repository"), "sgajbi/lotus-platform"),
        (("controller", "runId"), "run-1"),
        (("controller", "runAttempt"), 0),
        (("workload", "rolloutStatus"), "started"),
        (("workload", "rolloutCompletedAtUtc"), "2026-07-16T10:11:00Z"),
        (("workload", "observedImageDigest"), f"sha256:{'c' * 64}"),
        (("workload", "observedGitCommitSha"), "c" * 40),
        (("schedulerConfiguration", "identityDigest"), "not-a-digest"),
        (("schedulerConfiguration", "sourceContractDigest"), "not-a-digest"),
        (("deploymentEvidenceValid",), False),
        (("nonProofClaims", "scheduledExecutionObserved"), True),
        (("nonProofClaims", "liveCoreSourceCertified"), True),
        (("nonProofClaims", "productionCertified"), True),
        (("supportedFeaturePromoted",), True),
    ),
)
def test_deployment_evidence_rejects_identity_drift_and_claim_inflation(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(deployment_evidence(repository_root=ROOT))
    _set(payload, path, value)
    _refresh_receipt_digest(payload)

    assert not scheduled_worker_deployment_evidence_is_valid(payload)


def test_deployment_evidence_rejects_unknown_execution_boolean() -> None:
    payload = deployment_evidence(repository_root=ROOT)
    payload["scheduledWorkerExecuted"] = True

    assert not scheduled_worker_deployment_evidence_is_valid(payload)


def test_deployment_evidence_rejects_aggregate_source_revision_drift() -> None:
    payload = deployment_evidence(repository_root=ROOT)
    payload["aggregateProofProvenance"] = {
        "sourceRevision": "c" * 40,
    }

    assert not scheduled_worker_deployment_evidence_is_valid(payload)


def test_deployment_evidence_rejects_source_contract_digest_drift() -> None:
    payload = deployment_evidence(repository_root=ROOT)
    contract = source_contract(repository_root=ROOT)
    contract["sourceContractDigest"] = f"sha256:{'c' * 64}"

    assert not scheduled_worker_deployment_matches_source_contract(payload, contract)


def _set(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
    target = payload
    for part in path[:-1]:
        nested = target[part]
        assert isinstance(nested, dict)
        target = nested
    target[path[-1]] = value


def _refresh_receipt_digest(payload: dict[str, object]) -> None:
    payload["deploymentReceiptDigest"] = sha256_json(
        {
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
    )
