from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from app.application.capacity_evidence_qualification import (
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
)
from app.infrastructure.github_capacity_attestation import (
    GitHubCapacityAttestationVerifier,
)


def test_verifies_artifact_with_exact_trust_policy(tmp_path: Path) -> None:
    artifact = tmp_path / "threshold.json"
    artifact.write_text('{"sourceSafe":true}\n', encoding="utf-8")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout='[{"verified":true}]', stderr="")

    receipt = GitHubCapacityAttestationVerifier(command_runner=run).verify(
        artifact_path=artifact,
        source_commit_sha="a" * 40,
    )

    command, kwargs = calls[0]
    assert command == [
        "gh",
        "attestation",
        "verify",
        str(artifact),
        "--repo",
        TRUSTED_REPOSITORY,
        "--signer-workflow",
        TRUSTED_SIGNER_WORKFLOW,
        "--source-ref",
        TRUSTED_SOURCE_REF,
        "--source-digest",
        "a" * 40,
        "--format",
        "json",
    ]
    assert kwargs["check"] is False
    assert receipt.subject_sha256 == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert receipt.source_commit_sha == "a" * 40


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (subprocess.CompletedProcess([], 1, stdout="", stderr="sensitive"), "failed"),
        (subprocess.CompletedProcess([], 0, stdout="not-json", stderr=""), "invalid JSON"),
        (subprocess.CompletedProcess([], 0, stdout="[]", stderr=""), "no attestations"),
    ],
)
def test_fails_closed_without_leaking_verifier_output(
    tmp_path: Path,
    result: subprocess.CompletedProcess[str],
    message: str,
) -> None:
    artifact = tmp_path / "threshold.json"
    artifact.write_text("{}", encoding="utf-8")
    verifier = GitHubCapacityAttestationVerifier(command_runner=lambda *args, **kwargs: result)

    with pytest.raises(ValueError, match=message) as captured:
        verifier.verify(artifact_path=artifact, source_commit_sha="a" * 40)

    assert "sensitive" not in str(captured.value)


def test_rejects_missing_artifact_blank_commit_and_invalid_timeout(tmp_path: Path) -> None:
    verifier = GitHubCapacityAttestationVerifier()
    with pytest.raises(ValueError, match="must be a file"):
        verifier.verify(artifact_path=tmp_path / "missing.json", source_commit_sha="a" * 40)

    artifact = tmp_path / "threshold.json"
    artifact.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="must not be blank"):
        verifier.verify(artifact_path=artifact, source_commit_sha=" ")
    with pytest.raises(ValueError, match="positive"):
        GitHubCapacityAttestationVerifier(timeout_seconds=0)


def test_maps_command_unavailability_to_generic_failure(tmp_path: Path) -> None:
    artifact = tmp_path / "threshold.json"
    artifact.write_text("{}", encoding="utf-8")

    def unavailable(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("sensitive path")

    with pytest.raises(ValueError, match="verification unavailable") as captured:
        GitHubCapacityAttestationVerifier(command_runner=unavailable).verify(
            artifact_path=artifact,
            source_commit_sha="a" * 40,
        )
    assert "sensitive" not in str(captured.value)
