from __future__ import annotations

import os
from pathlib import Path

from app.application.cost_attribution_qualification import VerifiedPlatformCostAttestation
from app.infrastructure.github_cost_attribution_attestation import (
    GitHubCostAttributionAttestationVerifier,
)


def required_database_url() -> str:
    database_url = os.getenv("LOTUS_IDEA_DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("LOTUS_IDEA_DATABASE_URL is required for the postgresql scenario")
    return database_url


def verify_optional_cost_attribution_attestation(
    *,
    verification_requested: bool,
    artifact_path: Path | None,
    artifact: dict[str, object] | None,
    environment_profile: str,
) -> VerifiedPlatformCostAttestation | None:
    if not verification_requested:
        return None
    if artifact_path is None or artifact is None:
        raise ValueError("cost-attribution verification requires a platform artifact")
    if environment_profile != "production-like":
        raise ValueError("attested cost attribution requires production-like profile")
    provenance = artifact.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("platform cost-attribution provenance must be an object")
    source_commit = provenance.get("sourceCommitSha")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise ValueError("platform cost-attribution sourceCommitSha must be a non-blank string")
    return GitHubCostAttributionAttestationVerifier().verify(
        artifact_path=artifact_path,
        source_commit_sha=source_commit,
    )
