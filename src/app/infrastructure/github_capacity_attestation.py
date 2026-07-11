from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import subprocess

from app.application.capacity_evidence_qualification import (
    DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    LOAD_SOAK_SIGNER_WORKFLOW,
    POSTGRES_CAPACITY_SIGNER_WORKFLOW,
    TRUSTED_REPOSITORY,
    TRUSTED_SOURCE_REF,
    VerifiedArtifactAttestation,
)


class GitHubCapacityAttestationVerifier:
    def __init__(
        self,
        *,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        timeout_seconds: int = 60,
        signer_workflow: str = POSTGRES_CAPACITY_SIGNER_WORKFLOW,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if signer_workflow not in {
            POSTGRES_CAPACITY_SIGNER_WORKFLOW,
            DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
            LOAD_SOAK_SIGNER_WORKFLOW,
        }:
            raise ValueError("capacity evidence signer workflow is not trusted")
        self._command_runner = command_runner
        self._timeout_seconds = timeout_seconds
        self._signer_workflow = signer_workflow

    def verify(
        self,
        *,
        artifact_path: Path,
        source_commit_sha: str,
    ) -> VerifiedArtifactAttestation:
        if not artifact_path.is_file():
            raise ValueError("capacity evidence artifact path must be a file")
        if not source_commit_sha.strip():
            raise ValueError("source_commit_sha must not be blank")
        subject_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        command = [
            "gh",
            "attestation",
            "verify",
            str(artifact_path),
            "--repo",
            TRUSTED_REPOSITORY,
            "--signer-workflow",
            self._signer_workflow,
            "--source-ref",
            TRUSTED_SOURCE_REF,
            "--source-digest",
            source_commit_sha,
            "--format",
            "json",
        ]
        try:
            result = self._command_runner(
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("capacity evidence attestation verification unavailable") from exc
        if result.returncode != 0:
            raise ValueError("capacity evidence attestation verification failed")
        try:
            verified = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "capacity evidence attestation verification returned invalid JSON"
            ) from exc
        if not isinstance(verified, list) or not verified:
            raise ValueError("capacity evidence attestation verification returned no attestations")
        return VerifiedArtifactAttestation(
            subject_sha256=subject_sha256,
            repository=TRUSTED_REPOSITORY,
            signer_workflow=self._signer_workflow,
            source_ref=TRUSTED_SOURCE_REF,
            source_commit_sha=source_commit_sha,
        )
