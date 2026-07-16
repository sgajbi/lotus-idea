from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import format_utc, require_aware, sha256_json
from app.application.source_ingestion_scheduler.configuration import (
    RUN_ONCE_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_ENTRYPOINT,
    scheduled_worker_check_summary_is_valid,
)
from app.domain.proof_evidence import EvidenceClass, is_timezone_aware_datetime_text


SCHEDULED_WORKER_SOURCE_CONTRACT_ENV = (
    "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_SOURCE_CONTRACT"
)
SCHEDULED_WORKER_SOURCE_CONTRACT_SCHEMA_VERSION = (
    "lotus-idea.source-ingestion.scheduled-worker-source-contract.v2"
)
CANONICAL_WORKER_MANIFEST_PATH = (
    "docs/examples/source-ingestion/canonical-high-cash-worker.manifest.json"
)
REQUIRED_SOURCE_PATHS = (
    SCHEDULED_WORKER_ENTRYPOINT,
    RUN_ONCE_WORKER_ENTRYPOINT,
    "scripts/proof_generator_io.py",
    "docker-compose.yml",
    CANONICAL_WORKER_MANIFEST_PATH,
)
SCHEDULED_WORKER_BLOCKERS_PRESERVED = (
    "live_core_source_proof_missing",
    "scheduled_worker_deploy_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "evidenceClass",
    "repository",
    "sourceAuthority",
    "opportunityFamily",
    "generatedAtUtc",
    "proofType",
    "sourceContractValid",
    "sourceFiles",
    "checkSummary",
    "schedulerConfigurationDigest",
    "blockerEffect",
    "nonProofClaims",
    "supportedFeaturePromoted",
    "proofClosed",
    "sourceContractDigest",
}


def build_scheduled_worker_source_contract_payload(
    *,
    generated_at_utc: datetime,
    check_summary: Mapping[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    source_files = [
        {
            "path": path,
            "sha256": _file_sha256(repository_root / path),
        }
        for path in REQUIRED_SOURCE_PATHS
    ]
    material: dict[str, Any] = {
        "schemaVersion": SCHEDULED_WORKER_SOURCE_CONTRACT_SCHEMA_VERSION,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "repository": "lotus-idea",
        "sourceAuthority": "lotus-core",
        "opportunityFamily": "high_cash",
        "generatedAtUtc": format_utc(generated_at_utc),
        "proofType": "scheduled_source_ingestion_worker_source_contract",
        "sourceContractValid": True,
        "sourceFiles": source_files,
        "checkSummary": dict(check_summary),
        "schedulerConfigurationDigest": sha256_json(check_summary),
        "blockerEffect": {
            "clears": [],
            "preserves": list(SCHEDULED_WORKER_BLOCKERS_PRESERVED),
        },
        "nonProofClaims": {
            "deploymentObserved": False,
            "scheduledExecutionObserved": False,
            "productionCertified": False,
        },
        "supportedFeaturePromoted": False,
        "proofClosed": True,
    }
    return {**material, "sourceContractDigest": sha256_json(material)}


def scheduled_worker_source_contract_is_valid(
    payload: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
) -> bool:
    if not _has_exact_keys(payload, _TOP_LEVEL_KEYS):
        return False
    if payload.get("schemaVersion") != SCHEDULED_WORKER_SOURCE_CONTRACT_SCHEMA_VERSION:
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("sourceAuthority") != "lotus-core":
        return False
    if payload.get("opportunityFamily") != "high_cash":
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if payload.get("proofType") != "scheduled_source_ingestion_worker_source_contract":
        return False
    if payload.get("sourceContractValid") is not True:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not True:
        return False
    if not _source_files_are_valid(payload.get("sourceFiles")):
        return False
    if repository_root is not None and not _source_files_match_repository(
        payload["sourceFiles"],
        repository_root=repository_root,
    ):
        return False
    check_summary = payload.get("checkSummary")
    if not scheduled_worker_check_summary_is_valid(check_summary):
        return False
    if payload.get("schedulerConfigurationDigest") != sha256_json(check_summary):
        return False
    if payload.get("blockerEffect") != {
        "clears": [],
        "preserves": list(SCHEDULED_WORKER_BLOCKERS_PRESERVED),
    }:
        return False
    if payload.get("nonProofClaims") != {
        "deploymentObserved": False,
        "scheduledExecutionObserved": False,
        "productionCertified": False,
    }:
        return False
    material = {key: value for key, value in payload.items() if key != "sourceContractDigest"}
    material.pop(AGGREGATE_PROOF_PROVENANCE_KEY, None)
    return payload.get("sourceContractDigest") == sha256_json(material)


def _source_files_are_valid(value: object) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    records = list(value)
    if len(records) != len(REQUIRED_SOURCE_PATHS):
        return False
    for expected_path, record in zip(REQUIRED_SOURCE_PATHS, records, strict=True):
        if not isinstance(record, Mapping):
            return False
        if set(record) != {"path", "sha256"}:
            return False
        if record.get("path") != expected_path:
            return False
        digest = record.get("sha256")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            return False
    return True


def _source_files_match_repository(
    value: object,
    *,
    repository_root: Path,
) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    for record in value:
        if not isinstance(record, Mapping):
            return False
        path = record.get("path")
        digest = record.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            return False
        try:
            if _file_sha256(repository_root / path) != digest:
                return False
        except OSError:
            return False
    return True


def _has_exact_keys(payload: Mapping[str, Any], expected: set[str]) -> bool:
    return set(payload) in (expected, expected | {AGGREGATE_PROOF_PROVENANCE_KEY})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
