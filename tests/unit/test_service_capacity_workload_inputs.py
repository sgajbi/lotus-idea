from pathlib import Path

import pytest

from app.application.cost_attribution_qualification import VerifiedPlatformCostAttestation
from app.infrastructure import service_capacity_workload_inputs


def test_database_url_is_required_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOTUS_IDEA_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="LOTUS_IDEA_DATABASE_URL"):
        service_capacity_workload_inputs.required_database_url()

    monkeypatch.setenv("LOTUS_IDEA_DATABASE_URL", "  postgresql://idea  ")
    assert service_capacity_workload_inputs.required_database_url() == "postgresql://idea"


def test_optional_attestation_is_not_verified_unless_requested() -> None:
    assert (
        service_capacity_workload_inputs.verify_optional_cost_attribution_attestation(
            verification_requested=False,
            artifact_path=None,
            artifact=None,
            environment_profile="test",
        )
        is None
    )


@pytest.mark.parametrize(
    ("artifact_path", "artifact", "environment_profile", "message"),
    [
        (None, None, "production-like", "requires a platform artifact"),
        (Path("cost.json"), {}, "production", "production-like profile"),
        (Path("cost.json"), {"provenance": None}, "production-like", "provenance"),
        (
            Path("cost.json"),
            {"provenance": {"sourceCommitSha": " "}},
            "production-like",
            "sourceCommitSha",
        ),
    ],
)
def test_cost_attestation_input_contract_fails_closed(
    artifact_path: Path | None,
    artifact: dict[str, object] | None,
    environment_profile: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        service_capacity_workload_inputs.verify_optional_cost_attribution_attestation(
            verification_requested=True,
            artifact_path=artifact_path,
            artifact=artifact,
            environment_profile=environment_profile,
        )


def test_cost_attestation_verification_uses_declared_source_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path = tmp_path / "cost.json"
    artifact_path.write_text("{}", encoding="utf-8")
    expected = VerifiedPlatformCostAttestation(
        subject_sha256="b" * 64,
        repository="sgajbi/lotus-platform",
        signer_workflow="workflow",
        source_ref="refs/heads/main",
        source_commit_sha="a" * 40,
    )
    observed: dict[str, object] = {}

    class Verifier:
        def verify(self, **kwargs: object) -> VerifiedPlatformCostAttestation:
            observed.update(kwargs)
            return expected

    monkeypatch.setattr(
        service_capacity_workload_inputs,
        "GitHubCostAttributionAttestationVerifier",
        Verifier,
    )

    result = service_capacity_workload_inputs.verify_optional_cost_attribution_attestation(
        verification_requested=True,
        artifact_path=artifact_path,
        artifact={"provenance": {"sourceCommitSha": "a" * 40}},
        environment_profile="production-like",
    )

    assert result is expected
    assert observed == {"artifact_path": artifact_path, "source_commit_sha": "a" * 40}
