from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Mapping

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
OWNED_TABLE = re.compile(r"^idea_[a-z0-9_]+$")


class RestoreValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class DisasterRecoveryPolicy:
    rpo_minutes: int
    rto_minutes: int
    owned_tables: frozenset[str]
    allowed_unvalidated_constraints: frozenset[str]
    required_non_empty_tables: frozenset[str]

    def __post_init__(self) -> None:
        _require_positive(self.rpo_minutes, "rpo_minutes")
        _require_positive(self.rto_minutes, "rto_minutes")
        _require_owned_tables(self.owned_tables, "owned_tables")
        _require_owned_tables(self.required_non_empty_tables, "required_non_empty_tables")
        if not self.required_non_empty_tables.issubset(self.owned_tables):
            raise ValueError("required_non_empty_tables must be owned tables")
        for name in self.allowed_unvalidated_constraints:
            _require_safe_identifier(name, "allowed_unvalidated_constraint")


@dataclass(frozen=True)
class RestoreDrillRequest:
    backup_identifier: str
    backup_source: str
    operator_id: str
    correlation_id: str
    backup_format: str
    backup_artifact_sha256: str
    pitr_proof: bool
    migration_bundle_sha256: str
    latest_migration: str
    backup_created_at_utc: datetime
    incident_cutoff_utc: datetime
    recovery_point_utc: datetime
    restore_started_at_utc: datetime

    def __post_init__(self) -> None:
        for field_name in (
            "backup_identifier",
            "backup_source",
            "operator_id",
            "correlation_id",
            "backup_format",
            "latest_migration",
        ):
            _require_safe_identifier(getattr(self, field_name), field_name)
        if not re.fullmatch(r"[a-f0-9]{64}", self.migration_bundle_sha256):
            raise ValueError("migration_bundle_sha256 must be a lowercase SHA-256 digest")
        if not re.fullmatch(r"[a-f0-9]{64}", self.backup_artifact_sha256):
            raise ValueError("backup_artifact_sha256 must be a lowercase SHA-256 digest")
        for field_name in (
            "backup_created_at_utc",
            "incident_cutoff_utc",
            "recovery_point_utc",
            "restore_started_at_utc",
        ):
            _require_utc(getattr(self, field_name), field_name)
        if self.backup_created_at_utc > self.recovery_point_utc:
            raise ValueError("backup_created_at_utc must not be after recovery_point_utc")
        if self.recovery_point_utc > self.incident_cutoff_utc:
            raise ValueError("recovery_point_utc must not be after incident_cutoff_utc")
        if self.incident_cutoff_utc > self.restore_started_at_utc:
            raise ValueError("incident_cutoff_utc must not be after restore_started_at_utc")


@dataclass(frozen=True)
class RestoredDatabaseSnapshot:
    database_identity_sha256: str
    postgres_version: str
    table_row_counts: Mapping[str, int]
    table_content_sha256: Mapping[str, str]
    missing_primary_key_tables: tuple[str, ...]
    unvalidated_constraints: tuple[str, ...]
    invalid_indexes: tuple[str, ...]
    referential_violation_counts: Mapping[str, int]
    semantic_violation_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", self.database_identity_sha256):
            raise ValueError("database_identity_sha256 must be a lowercase SHA-256 digest")
        if not self.postgres_version.strip():
            raise ValueError("postgres_version is required")
        _require_count_mapping(self.table_row_counts, "table_row_counts", owned_keys=True)
        _require_hash_mapping(self.table_content_sha256)
        if set(self.table_content_sha256) != set(self.table_row_counts):
            raise ValueError("table hashes and row counts must cover the same tables")
        _require_count_mapping(self.referential_violation_counts, "referential_violation_counts")
        _require_count_mapping(self.semantic_violation_counts, "semantic_violation_counts")
        for name in (
            *self.missing_primary_key_tables,
            *self.unvalidated_constraints,
            *self.invalid_indexes,
        ):
            _require_safe_identifier(name, "schema finding")


@dataclass(frozen=True)
class RestoreDrillEvidence:
    evidence_version: str
    validation_mode: str
    status: RestoreValidationStatus
    generated_at_utc: str
    backup_identifier: str
    backup_source: str
    operator_id: str
    correlation_id: str
    backup_format: str
    backup_artifact_sha256: str
    pitr_proof: bool
    database_identity_sha256: str
    postgres_version: str
    migration_bundle_sha256: str
    latest_migration: str
    backup_created_at_utc: str
    incident_cutoff_utc: str
    recovery_point_utc: str
    restore_started_at_utc: str
    service_ready_at_utc: str
    actual_rpo_seconds: float
    target_rpo_seconds: int
    actual_rto_seconds: float
    target_rto_seconds: int
    restored_table_row_counts: Mapping[str, int]
    restored_table_content_sha256: Mapping[str, str]
    failed_checks: tuple[str, ...]
    source_safe: bool = True
    real_restored_backup: bool = True
    synthetic_smoke: bool = False
    supported_feature_promoted: bool = False
    certification_status: str = "not_certified"


def evaluate_restored_database(
    request: RestoreDrillRequest,
    snapshot: RestoredDatabaseSnapshot,
    policy: DisasterRecoveryPolicy,
    *,
    generated_at_utc: datetime,
) -> RestoreDrillEvidence:
    _require_utc(generated_at_utc, "generated_at_utc")
    actual_rpo_seconds = (request.incident_cutoff_utc - request.recovery_point_utc).total_seconds()
    actual_rto_seconds = (generated_at_utc - request.restore_started_at_utc).total_seconds()
    if actual_rto_seconds < 0:
        raise ValueError("generated_at_utc must not be before restore_started_at_utc")
    failed_checks: list[str] = []
    observed_tables = set(snapshot.table_row_counts)
    if observed_tables != policy.owned_tables:
        failed_checks.append("owned_table_inventory")
    if any(
        snapshot.table_row_counts.get(table, 0) == 0 for table in policy.required_non_empty_tables
    ):
        failed_checks.append("representative_linked_state")
    if snapshot.missing_primary_key_tables:
        failed_checks.append("primary_keys")
    unexpected_constraints = set(snapshot.unvalidated_constraints).difference(
        policy.allowed_unvalidated_constraints
    )
    if unexpected_constraints:
        failed_checks.append("validated_constraints")
    if snapshot.invalid_indexes:
        failed_checks.append("valid_ready_indexes")
    if any(snapshot.referential_violation_counts.values()):
        failed_checks.append("referential_integrity")
    if any(snapshot.semantic_violation_counts.values()):
        failed_checks.append("workflow_state_integrity")
    if actual_rpo_seconds > policy.rpo_minutes * 60:
        failed_checks.append("rpo")
    if actual_rto_seconds > policy.rto_minutes * 60:
        failed_checks.append("rto")

    return RestoreDrillEvidence(
        evidence_version="1.0.0",
        validation_mode="real_restore_validation",
        status=(
            RestoreValidationStatus.FAILED if failed_checks else RestoreValidationStatus.PASSED
        ),
        generated_at_utc=generated_at_utc.isoformat(),
        backup_identifier=request.backup_identifier,
        backup_source=request.backup_source,
        operator_id=request.operator_id,
        correlation_id=request.correlation_id,
        backup_format=request.backup_format,
        backup_artifact_sha256=request.backup_artifact_sha256,
        pitr_proof=request.pitr_proof,
        database_identity_sha256=snapshot.database_identity_sha256,
        postgres_version=snapshot.postgres_version,
        migration_bundle_sha256=request.migration_bundle_sha256,
        latest_migration=request.latest_migration,
        backup_created_at_utc=request.backup_created_at_utc.isoformat(),
        incident_cutoff_utc=request.incident_cutoff_utc.isoformat(),
        recovery_point_utc=request.recovery_point_utc.isoformat(),
        restore_started_at_utc=request.restore_started_at_utc.isoformat(),
        service_ready_at_utc=generated_at_utc.isoformat(),
        actual_rpo_seconds=actual_rpo_seconds,
        target_rpo_seconds=policy.rpo_minutes * 60,
        actual_rto_seconds=actual_rto_seconds,
        target_rto_seconds=policy.rto_minutes * 60,
        restored_table_row_counts=dict(sorted(snapshot.table_row_counts.items())),
        restored_table_content_sha256=dict(sorted(snapshot.table_content_sha256.items())),
        failed_checks=tuple(failed_checks),
    )


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _require_safe_identifier(value: str, field_name: str) -> None:
    if not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} must be a source-safe identifier")


def _require_owned_tables(values: frozenset[str], field_name: str) -> None:
    if not values or any(not OWNED_TABLE.fullmatch(value) for value in values):
        raise ValueError(f"{field_name} must contain idea-owned table names")


def _require_count_mapping(
    values: Mapping[str, int], field_name: str, *, owned_keys: bool = False
) -> None:
    for key, value in values.items():
        if owned_keys:
            if not OWNED_TABLE.fullmatch(key):
                raise ValueError(f"{field_name} must use idea-owned table names")
        else:
            _require_safe_identifier(key, field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} values must be non-negative integers")


def _require_hash_mapping(values: Mapping[str, str]) -> None:
    for table, digest in values.items():
        if not OWNED_TABLE.fullmatch(table) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("table_content_sha256 must contain owned-table SHA-256 digests")
