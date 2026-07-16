from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


_SOURCE_AUTHORITY_FIELDS = frozenset({"repository", "ref", "sha256"})


@dataclass(frozen=True)
class SourceAuthoritySource:
    repository: str
    ref: str
    path: Path


def build_source_authority_records(
    sources: Sequence[SourceAuthoritySource],
) -> tuple[dict[str, str | None], ...]:
    return tuple(
        {
            "repository": source.repository,
            "ref": source.ref,
            "sha256": _sha256(source.path),
        }
        for source in sources
    )


def source_authority_records_are_valid(
    value: object,
    *,
    expected_sources: Sequence[SourceAuthoritySource],
) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != len(expected_sources):
        return False
    for item, expected in zip(value, expected_sources, strict=True):
        if not isinstance(item, Mapping) or set(item) != _SOURCE_AUTHORITY_FIELDS:
            return False
        if item.get("repository") != expected.repository or item.get("ref") != expected.ref:
            return False
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            return False
        if any(character not in "0123456789abcdef" for character in digest):
            return False
    return True


def source_authority_records_digest(value: object) -> str | None:
    if not isinstance(value, (list, tuple)):
        return None
    records: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _SOURCE_AUTHORITY_FIELDS:
            return None
        repository = item.get("repository")
        ref = item.get("ref")
        digest = item.get("sha256")
        if (
            not isinstance(repository, str)
            or not isinstance(ref, str)
            or not isinstance(digest, str)
        ):
            return None
        records.append(
            {
                "repository": repository,
                "ref": ref,
                "sha256": digest,
            }
        )
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_json_object(path: Path) -> Mapping[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()
