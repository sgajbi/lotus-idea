from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.capacity_evidence_qualification import (
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
    VerifiedArtifactAttestation,
    qualify_postgres_capacity_threshold_evidence,
)
from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture


class ThresholdPort:
    def __init__(self) -> None:
        self._values = iter([0.2, 0.9, 0.2])

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(next(self._values))

    def acquire_load_connection(self) -> None:
        pass

    def release_load_connections(self) -> None:
        pass

    def close(self) -> None:
        pass


def _proof() -> dict[str, object]:
    return execute_postgres_capacity_threshold_proof(
        stress_port=ThresholdPort(),
        environment_profile="test",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="a" * 40,
        branch="main",
        run_id="threshold-1",
        maximum_load_connections=5,
    )


def _attestation(**overrides: str) -> VerifiedArtifactAttestation:
    values = {
        "subject_sha256": "b" * 64,
        "repository": TRUSTED_REPOSITORY,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "source_ref": TRUSTED_SOURCE_REF,
        "source_commit_sha": "a" * 40,
    }
    values.update(overrides)
    return VerifiedArtifactAttestation(**values)


def test_qualifies_only_attested_mainline_threshold_evidence() -> None:
    qualification = qualify_postgres_capacity_threshold_evidence(
        threshold_proof=_proof(),
        verified_attestation=_attestation(),
        generated_at_utc=datetime(2026, 7, 11, 7, 0, tzinfo=UTC),
        qualification_run_id="qualification-1",
    )

    assert qualification["claimPosture"] == "production_like_environment_qualified"
    assert qualification["attestationVerified"] is True
    assert qualification["thresholdProofSha256"] == "b" * 64
    assert qualification["productionCapacityCertified"] is False
    assert qualification["supportedFeaturePromoted"] is False


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"subject_sha256": "invalid"}, "lowercase SHA-256"),
        ({"repository": "other/repo"}, "repository is not trusted"),
        ({"signer_workflow": "other/workflow.yml"}, "workflow is not trusted"),
        ({"source_ref": "refs/heads/feature"}, "refs/heads/main"),
        ({"source_commit_sha": "c" * 40}, "commit does not match"),
    ],
)
def test_rejects_untrusted_or_mismatched_attestation(
    overrides: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(**overrides),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )


def test_rejects_non_main_proof_and_ambiguous_qualification_provenance() -> None:
    proof = _proof()
    proof["branch"] = "feature/capacity"
    with pytest.raises(ValueError, match="originate from main"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=proof,
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11),
            qualification_run_id="qualification-1",
        )

    with pytest.raises(ValueError, match="qualification_run_id"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id=" ",
        )

    invalid_proof = _proof()
    invalid_proof["claimPosture"] = "production_certified"
    with pytest.raises(ValueError, match="claimPosture"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=invalid_proof,
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )
