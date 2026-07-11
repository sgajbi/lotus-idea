from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from app.application.cost_attribution_qualification import (
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
)
from app.infrastructure.github_cost_attribution_attestation import (
    GitHubCostAttributionAttestationVerifier,
)


def test_verifies_platform_artifact_with_exact_cross_repo_trust_policy(tmp_path: Path) -> None:
    artifact = tmp_path / "cost.json"
    artifact.write_text('{"sourceSafe":true}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout='[{"verified":true}]', stderr="")

    receipt = GitHubCostAttributionAttestationVerifier(command_runner=run).verify(
        artifact_path=artifact, source_commit_sha="a" * 40
    )

    assert calls[0] == [
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
    assert receipt.subject_sha256 == hashlib.sha256(artifact.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (subprocess.CompletedProcess([], 1, stdout="", stderr="sensitive"), "failed"),
        (subprocess.CompletedProcess([], 0, stdout="bad", stderr=""), "invalid JSON"),
        (subprocess.CompletedProcess([], 0, stdout="[]", stderr=""), "no attestations"),
    ],
)
def test_verifier_fails_closed_without_leaking_command_output(
    tmp_path: Path, result: subprocess.CompletedProcess[str], message: str
) -> None:
    artifact = tmp_path / "cost.json"
    artifact.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=message) as captured:
        GitHubCostAttributionAttestationVerifier(
            command_runner=lambda *args, **kwargs: result
        ).verify(artifact_path=artifact, source_commit_sha="a" * 40)
    assert "sensitive" not in str(captured.value)
