from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any


_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


@dataclass(frozen=True, slots=True)
class CIExecutionReceipt:
    repository: str
    workflow_path: str
    workflow_name: str
    job_name: str
    run_id: int
    run_attempt: int
    source_commit_sha: str
    source_ref: str
    conclusion: str
    completed_at_utc: str
    artifact_name: str
    artifact_sha256: str
    assertions: tuple[str, ...]


def ci_execution_receipt_from_mapping(payload: Mapping[str, object]) -> CIExecutionReceipt | None:
    if set(payload) != set(CIExecutionReceipt.__dataclass_fields__):
        return None
    try:
        receipt = CIExecutionReceipt(
            repository=_text(payload, "repository"),
            workflow_path=_text(payload, "workflow_path"),
            workflow_name=_text(payload, "workflow_name"),
            job_name=_text(payload, "job_name"),
            run_id=_positive_int(payload, "run_id"),
            run_attempt=_positive_int(payload, "run_attempt"),
            source_commit_sha=_text(payload, "source_commit_sha"),
            source_ref=_text(payload, "source_ref"),
            conclusion=_text(payload, "conclusion"),
            completed_at_utc=_text(payload, "completed_at_utc"),
            artifact_name=_text(payload, "artifact_name"),
            artifact_sha256=_text(payload, "artifact_sha256"),
            assertions=_text_tuple(payload, "assertions"),
        )
    except (TypeError, ValueError):
        return None
    return receipt if ci_execution_receipt_is_well_formed(receipt) else None


def ci_execution_receipt_is_well_formed(receipt: CIExecutionReceipt) -> bool:
    return (
        isinstance(receipt.repository, str)
        and _REPOSITORY.fullmatch(receipt.repository) is not None
        and isinstance(receipt.workflow_path, str)
        and receipt.workflow_path.startswith(".github/workflows/")
        and receipt.workflow_path.endswith((".yml", ".yaml"))
        and isinstance(receipt.workflow_name, str)
        and bool(receipt.workflow_name.strip())
        and isinstance(receipt.job_name, str)
        and bool(receipt.job_name.strip())
        and isinstance(receipt.run_id, int)
        and not isinstance(receipt.run_id, bool)
        and receipt.run_id > 0
        and isinstance(receipt.run_attempt, int)
        and not isinstance(receipt.run_attempt, bool)
        and receipt.run_attempt > 0
        and isinstance(receipt.source_commit_sha, str)
        and _COMMIT_SHA.fullmatch(receipt.source_commit_sha) is not None
        and isinstance(receipt.source_ref, str)
        and receipt.source_ref.startswith("refs/")
        and receipt.conclusion == "success"
        and _timezone_aware_datetime(receipt.completed_at_utc)
        and isinstance(receipt.artifact_name, str)
        and bool(receipt.artifact_name.strip())
        and isinstance(receipt.artifact_sha256, str)
        and _SHA256.fullmatch(receipt.artifact_sha256) is not None
        and isinstance(receipt.assertions, tuple)
        and bool(receipt.assertions)
        and len(set(receipt.assertions)) == len(receipt.assertions)
        and all(assertion.strip() == assertion and assertion for assertion in receipt.assertions)
    )


def ci_execution_receipt_digest(receipt: CIExecutionReceipt) -> str:
    encoded = json.dumps(
        asdict(receipt),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be non-empty text")
    return value


def _positive_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _text_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a text sequence")
    return tuple(value)


def _timezone_aware_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None
