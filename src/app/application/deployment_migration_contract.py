from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from app.domain.deployment_migrations import (
    DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
    MIGRATION_EVIDENCE_SCHEMA_VERSION,
    MIGRATION_HISTORY_SCHEMA_VERSION,
    SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR,
)


@dataclass(frozen=True)
class DeploymentMigrationContract:
    schema_version: str
    evidence_schema_version: str
    postgres_major_version: int
    migration_bundle_sha256: str
    schema_fingerprint_sha256: str
    migration_count: int
    current_migration_version: str
    remaining_certification_blockers: tuple[str, ...]


def load_deployment_migration_contract(path: Path) -> DeploymentMigrationContract:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("deployment migration contract must be an object")
    expected = {
        "schemaVersion": DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
        "repository": "sgajbi/lotus-idea",
        "migrationHistorySchemaVersion": MIGRATION_HISTORY_SCHEMA_VERSION,
        "evidenceSchemaVersion": MIGRATION_EVIDENCE_SCHEMA_VERSION,
        "postgresMajorVersion": SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"deployment migration contract {key} must be {value}")
    adoption = payload.get("legacyAdoption")
    if not isinstance(adoption, Mapping):
        raise ValueError("deployment migration contract legacyAdoption must be an object")
    certification = payload.get("certificationPosture")
    if not isinstance(certification, Mapping):
        raise ValueError("deployment migration contract certificationPosture must be an object")
    blockers = certification.get("remainingBlockers")
    if (
        not isinstance(blockers, list)
        or not blockers
        or not all(isinstance(blocker, str) and blocker for blocker in blockers)
    ):
        raise ValueError(
            "deployment migration contract remainingBlockers must be a non-empty text list"
        )
    return DeploymentMigrationContract(
        schema_version=_required_text(payload, "schemaVersion"),
        evidence_schema_version=_required_text(payload, "evidenceSchemaVersion"),
        postgres_major_version=_required_int(payload, "postgresMajorVersion"),
        migration_bundle_sha256=_required_text(payload, "migrationBundleSha256"),
        schema_fingerprint_sha256=_required_text(adoption, "schemaFingerprintSha256"),
        migration_count=_required_int(payload, "migrationCount"),
        current_migration_version=_required_text(payload, "currentMigrationVersion"),
        remaining_certification_blockers=tuple(blockers),
    )


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"deployment migration contract {key} must be non-empty text")
    return value


def _required_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"deployment migration contract {key} must be an integer")
    return value
