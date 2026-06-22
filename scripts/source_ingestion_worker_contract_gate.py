from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MANIFEST_PATH = (
    ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
)

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "mode",
    "sourceAuthority",
    "evaluatedAtUtc",
    "actorSubject",
    "maxItems",
    "workItemCount",
    "workItems",
}

REQUIRED_WORK_ITEM_KEYS = {
    "itemIndex",
    "asOfDate",
    "hasExplicitIdempotencyKey",
    "hasDuplicateOfCandidateId",
}

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "duplicateOfCandidateId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "/source/",
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
    "signal-ingestion:high-cash:lotus-core",
}


def validate_source_ingestion_worker_contract(
    *,
    manifest_path: Path = EXAMPLE_MANIFEST_PATH,
) -> list[str]:
    errors: list[str] = []
    try:
        manifest = _read_manifest(manifest_path)
        plan = source_ingestion_worker_plan_from_manifest(manifest)
        summary = plan.check_summary()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"{_display_path(manifest_path)}: cannot build check-only summary: {exc}"]

    if set(summary) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "check-only summary keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(summary)}"
        )
    if summary.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {MANIFEST_SCHEMA_VERSION}")
    if summary.get("mode") != "check_only":
        errors.append("mode must be check_only")
    if summary.get("sourceAuthority") != "lotus-core":
        errors.append("sourceAuthority must be lotus-core")

    work_items = summary.get("workItems")
    if not isinstance(work_items, list):
        errors.append("workItems must be a list")
    else:
        if summary.get("workItemCount") != len(work_items):
            errors.append("workItemCount must equal the number of workItems")
        for index, item in enumerate(work_items):
            if not isinstance(item, Mapping):
                errors.append(f"workItems[{index}] must be an object")
                continue
            if set(item) != REQUIRED_WORK_ITEM_KEYS:
                errors.append(
                    f"workItems[{index}] keys must be {sorted(REQUIRED_WORK_ITEM_KEYS)}; "
                    f"got {sorted(item)}"
                )
            if item.get("itemIndex") != index:
                errors.append(f"workItems[{index}].itemIndex must equal {index}")
            if not isinstance(item.get("hasExplicitIdempotencyKey"), bool):
                errors.append(f"workItems[{index}].hasExplicitIdempotencyKey must be boolean")
            if not isinstance(item.get("hasDuplicateOfCandidateId"), bool):
                errors.append(f"workItems[{index}].hasDuplicateOfCandidateId must be boolean")

    _validate_forbidden_content(summary, errors)
    return errors


def _validate_forbidden_content(value: object, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text in FORBIDDEN_KEYS:
                errors.append(f"{next_path}: forbidden source-sensitive key is present")
            _validate_forbidden_content(nested, errors, next_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    errors = validate_source_ingestion_worker_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Source ingestion worker contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
