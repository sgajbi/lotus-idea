from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re


MIGRATION_EVIDENCE_SCHEMA_VERSION = "lotus-idea.deployment-migration-evidence.v1"
MIGRATION_HISTORY_SCHEMA_VERSION = "lotus-idea.schema-migration-history.v1"

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_REFERENCE_PATTERN = re.compile(r"^ghcr\.io/sgajbi/lotus-idea@sha256:[0-9a-f]{64}$")
_RUN_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")


class DeploymentMigrationOperation(StrEnum):
    APPLY = "apply"
    ROLLBACK = "rollback"
    ADOPT = "adopt"


class DeploymentEnvironmentClass(StrEnum):
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class MigrationReleaseIdentity:
    repository: str
    git_commit_sha: str
    git_ref: str
    ci_run_id: str
    image_digest_reference: str
    environment_class: DeploymentEnvironmentClass

    def __post_init__(self) -> None:
        if self.repository != "sgajbi/lotus-idea":
            raise ValueError("repository must identify sgajbi/lotus-idea")
        if not _COMMIT_SHA_PATTERN.fullmatch(self.git_commit_sha):
            raise ValueError("git_commit_sha must be a lowercase 40-character SHA")
        if self.git_ref != "refs/heads/main":
            raise ValueError("git_ref must be refs/heads/main")
        if not _RUN_ID_PATTERN.fullmatch(self.ci_run_id):
            raise ValueError("ci_run_id must be a positive numeric GitHub run id")
        if not _DIGEST_REFERENCE_PATTERN.fullmatch(self.image_digest_reference):
            raise ValueError("image_digest_reference must be the immutable Lotus Idea GHCR digest")


@dataclass(frozen=True)
class DeploymentMigrationCommand:
    operation: DeploymentMigrationOperation
    release: MigrationReleaseIdentity
    rollback_count: int = 0
    expected_schema_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.operation is DeploymentMigrationOperation.ROLLBACK:
            if self.rollback_count < 1 or self.rollback_count > 15:
                raise ValueError("rollback_count must be between 1 and 15")
        elif self.rollback_count != 0:
            raise ValueError("rollback_count is valid only for rollback")
        if self.operation is DeploymentMigrationOperation.ADOPT:
            if not self.expected_schema_fingerprint:
                raise ValueError("expected_schema_fingerprint is required for adoption")
        elif self.expected_schema_fingerprint is not None:
            raise ValueError("expected_schema_fingerprint is valid only for adoption")


@dataclass(frozen=True)
class DeploymentMigrationResult:
    operation: DeploymentMigrationOperation
    release: MigrationReleaseIdentity
    migration_bundle_sha256: str
    previous_version: str | None
    current_version: str | None
    applied_versions: tuple[str, ...]
    rolled_back_versions: tuple[str, ...]
    adopted_versions: tuple[str, ...]
    executed_at_utc: datetime
    advisory_lock_held: bool = True


class DeploymentMigrationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
