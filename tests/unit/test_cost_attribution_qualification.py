from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.cost_attribution_qualification import (
    RESOURCE_SCHEMA_VERSION,
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
    VerifiedPlatformCostAttestation,
    qualify_platform_cost_attribution,
)


def _artifact() -> dict[str, Any]:
    return {
        "schemaVersion": "lotus-platform.service-cost-attribution.v1",
        "repository": "lotus-platform",
        "proofScope": "source_safe_service_cost_attribution",
        "claimPosture": "reconciled_not_attested",
        "service": {
            "repository": "lotus-idea",
            "serviceId": "lotus-idea-api",
            "environment": "production-like",
            "region": "ap-southeast-1",
        },
        "billingPeriod": {"start": "2026-07-01", "end": "2026-07-31"},
        "currency": "USD",
        "provenance": {
            "sourceCommitSha": "a" * 40,
            "sourceRef": TRUSTED_SOURCE_REF,
            "pipelineRunId": "run-1",
        },
        "resourceObservation": {
            "schemaVersion": RESOURCE_SCHEMA_VERSION,
            "sha256": "b" * 64,
            "runId": "resource-1",
        },
        "costAttributionReconciled": True,
        "costAttributionCertified": False,
        "certificationBlockers": ["artifact_attestation_missing"],
        "supportedFeaturePromoted": False,
    }


def _attestation(**overrides: str) -> VerifiedPlatformCostAttestation:
    values = {
        "subject_sha256": "c" * 64,
        "repository": TRUSTED_REPOSITORY,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "source_ref": TRUSTED_SOURCE_REF,
        "source_commit_sha": "a" * 40,
    }
    values.update(overrides)
    return VerifiedPlatformCostAttestation(**values)


def _resource_qualification(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "resourceProofSha256": "b" * 64,
        "resourceProofRunId": "resource-1",
        "attestationVerified": True,
    }
    values.update(overrides)
    return values


def test_qualification_binds_platform_attestation_to_idea_resource_proof() -> None:
    result = qualify_platform_cost_attribution(
        artifact=_artifact(),
        attestation=_attestation(),
        resource_qualification=_resource_qualification(),
        generated_at_utc=datetime(2026, 7, 11, 10, tzinfo=UTC),
        qualification_run_id="idea-cost-qualification-1",
    )

    assert result["costAttributionVerified"] is True
    assert result["platformArtifactSha256"] == "c" * 64
    assert result["resourceProofSha256"] == "b" * 64
    assert result["productionCapacityCertified"] is False
    assert result["supportedFeaturePromoted"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"costAttributionReconciled": False}, "costAttributionReconciled is invalid"),
        ({"costAttributionCertified": True}, "costAttributionCertified is invalid"),
        ({"certificationBlockers": []}, "blockers are inconsistent"),
        ({"currency": "usd"}, "currency is invalid"),
    ],
)
def test_qualification_rejects_inflated_or_malformed_platform_claims(
    mutation: dict[str, object], message: str
) -> None:
    artifact = _artifact()
    artifact.update(mutation)
    with pytest.raises(ValueError, match=message):
        qualify_platform_cost_attribution(
            artifact=artifact,
            attestation=_attestation(),
            resource_qualification=_resource_qualification(),
            generated_at_utc=datetime(2026, 7, 11, 10, tzinfo=UTC),
            qualification_run_id="qual-1",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"repository": "other/repo"}, "repository is not trusted"),
        ({"signer_workflow": "other/workflow"}, "workflow is not trusted"),
        ({"source_ref": "refs/heads/feature"}, "refs/heads/main"),
        ({"source_commit_sha": "d" * 40}, "commit does not match"),
        ({"subject_sha256": "bad"}, "subject digest"),
    ],
)
def test_qualification_rejects_platform_attestation_mismatch(
    overrides: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        qualify_platform_cost_attribution(
            artifact=_artifact(),
            attestation=_attestation(**overrides),
            resource_qualification=_resource_qualification(),
            generated_at_utc=datetime(2026, 7, 11, 10, tzinfo=UTC),
            qualification_run_id="qual-1",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"resourceProofSha256": "d" * 64}, "digest does not match"),
        ({"resourceProofRunId": "other"}, "run does not match"),
        ({"attestationVerified": False}, "must be attested"),
    ],
)
def test_qualification_rejects_unbound_idea_resource_evidence(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        qualify_platform_cost_attribution(
            artifact=_artifact(),
            attestation=_attestation(),
            resource_qualification=_resource_qualification(**overrides),
            generated_at_utc=datetime(2026, 7, 11, 10, tzinfo=UTC),
            qualification_run_id="qual-1",
        )
