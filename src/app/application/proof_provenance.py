from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
import subprocess
from typing import Any

from app.domain.proof_evidence import parse_timezone_aware_datetime

AGGREGATE_PROOF_PROVENANCE_KEY = "aggregateProofProvenance"
MAX_AGGREGATE_PROOF_AGE = timedelta(hours=24)
SOURCE_REVISION_ENV = "LOTUS_IDEA_SOURCE_REVISION"
SOURCE_REVISION_UNAVAILABLE = "source-revision-unavailable"


def bind_aggregate_proof_provenance(
    payload: Mapping[str, Any],
    *,
    artifact_path: Path,
    proof_ref: str,
    repository_root: Path,
) -> dict[str, Any]:
    bound_payload = dict(payload)
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    bound_payload[AGGREGATE_PROOF_PROVENANCE_KEY] = {
        "repository": "lotus-idea",
        "proofRef": proof_ref,
        "proofGeneratedAtUtc": _format_utc(generated_at_utc) if generated_at_utc else None,
        "artifactSha256": _sha256_file(artifact_path),
        "sourceRevision": current_source_revision(repository_root),
        "sourceTreeDirty": source_tree_dirty(repository_root),
    }
    return bound_payload


def aggregate_proof_artifact_is_current(
    payload: Mapping[str, object],
    *,
    evaluated_at_utc: datetime,
    proof_ref: str | None,
    repository_root: Path | None = None,
) -> bool:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        return False
    if not proof_ref:
        return False
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    if generated_at_utc is None:
        return False
    evaluated_at_utc = evaluated_at_utc.astimezone(UTC)
    if generated_at_utc > evaluated_at_utc:
        return False
    if evaluated_at_utc - generated_at_utc > MAX_AGGREGATE_PROOF_AGE:
        return False

    provenance = payload.get(AGGREGATE_PROOF_PROVENANCE_KEY)
    if not isinstance(provenance, Mapping):
        return False
    if provenance.get("repository") != "lotus-idea":
        return False
    if provenance.get("proofRef") != proof_ref:
        return False
    if provenance.get("proofGeneratedAtUtc") != _format_utc(generated_at_utc):
        return False
    if not _is_sha256_hex(provenance.get("artifactSha256")):
        return False
    if provenance.get("sourceTreeDirty") is not False:
        return False

    root = repository_root or Path.cwd()
    source_revision = provenance.get("sourceRevision")
    if not isinstance(source_revision, str) or not source_revision.strip():
        return False
    if source_revision == SOURCE_REVISION_UNAVAILABLE:
        return False
    return source_revision == current_source_revision(root)


def current_source_revision(repository_root: Path) -> str:
    configured = os.getenv(SOURCE_REVISION_ENV, "").strip()
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return SOURCE_REVISION_UNAVAILABLE
    revision = result.stdout.strip()
    return revision or SOURCE_REVISION_UNAVAILABLE


def source_tree_dirty(repository_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return True
    return bool(result.stdout.strip())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _is_sha256_hex(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
