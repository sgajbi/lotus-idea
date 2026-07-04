from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.proof_provenance import (
    AGGREGATE_PROOF_PROVENANCE_KEY,
    bind_aggregate_proof_provenance,
    current_source_revision,
)

ROOT = Path(__file__).resolve().parents[2]


def bound_aggregate_proof(
    payload: Mapping[str, object],
    proof_ref: str,
    *,
    repository_root: Path = ROOT,
    source_tree_dirty: bool = False,
) -> dict[str, Any]:
    generated_at_utc = _parse_generated_at_utc(payload.get("generatedAtUtc"))
    bound_payload = dict(payload)
    bound_payload[AGGREGATE_PROOF_PROVENANCE_KEY] = {
        "repository": "lotus-idea",
        "proofRef": proof_ref,
        "proofGeneratedAtUtc": _format_utc(generated_at_utc),
        "artifactSha256": "0" * 64,
        "sourceRevision": current_source_revision(repository_root),
        "sourceTreeDirty": source_tree_dirty,
    }
    return bound_payload


def bind_clean_aggregate_proof_provenance(
    payload: Mapping[str, Any],
    *,
    artifact_path: Path,
    proof_ref: str,
    repository_root: Path,
) -> dict[str, Any]:
    bound_payload = bind_aggregate_proof_provenance(
        payload,
        artifact_path=artifact_path,
        proof_ref=proof_ref,
        repository_root=repository_root,
    )
    bound_payload[AGGREGATE_PROOF_PROVENANCE_KEY]["sourceTreeDirty"] = False
    return bound_payload


def _parse_generated_at_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("proof fixture must include generatedAtUtc")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("proof fixture generatedAtUtc must be timezone-aware")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
