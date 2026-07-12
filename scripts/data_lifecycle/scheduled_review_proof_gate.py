from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_PATH = ROOT / "output/data-lifecycle/scheduled-review-evidence.json"
ALLOWED_BLOCKERS = frozenset(
    {
        "active_delivery_work",
        "invalid_state",
        "legal_hold_active",
        "retention_not_expired",
    }
)


def validate_scheduled_lifecycle_review_proof(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"scheduled lifecycle review evidence is unreadable: {type(exc).__name__}"]
    if not isinstance(payload, dict):
        return ["scheduled lifecycle review evidence must be an object"]
    errors: list[str] = []
    expected = {
        "schema_version": "lotus-idea.scheduled-lifecycle-review-evidence.v1",
        "repository": "sgajbi/lotus-idea",
        "git_ref": "refs/heads/main",
        "execution_profile": "synthetic_disposable_postgres",
        "review_only": True,
        "privacy_review_required": True,
        "production_authority_verified": False,
        "source_safe": True,
        "certification_status": "not_certified",
        "supported_feature_promoted": False,
        "truncated": False,
    }
    for field_name, expected_value in expected.items():
        if payload.get(field_name) != expected_value:
            errors.append(f"scheduled lifecycle review {field_name} must be {expected_value!r}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(payload.get("git_commit", ""))):
        errors.append("scheduled lifecycle review git_commit must be a full commit SHA")
    if not str(payload.get("ci_run_id", "")).isdigit():
        errors.append("scheduled lifecycle review ci_run_id must be numeric")
    _validate_timestamp(payload.get("generated_at_utc"), errors)
    counts = _integer_counts(payload, errors)
    if counts is not None:
        scanned, ready, blocked, limit = counts
        if scanned != ready + blocked:
            errors.append("scheduled lifecycle review counts must reconcile")
        if scanned > limit:
            errors.append("scheduled lifecycle review scanned_count exceeds requested_limit")
        if ready < 1 or blocked < 1:
            errors.append("scheduled lifecycle proof must exercise ready and blocked decisions")
    _validate_blocker_counts(payload.get("blocker_counts"), errors)
    serialized = json.dumps(payload, sort_keys=True).lower()
    for forbidden in ("candidate_id", "tenant_id", "authority_ref", "approver_subject"):
        if forbidden in serialized:
            errors.append(f"scheduled lifecycle evidence must not expose {forbidden}")
    return errors


def _integer_counts(payload: dict[str, Any], errors: list[str]) -> tuple[int, int, int, int] | None:
    fields = (
        "scanned_count",
        "ready_for_authorized_purge_count",
        "blocked_count",
        "requested_limit",
    )
    values: list[int] = []
    for field_name in fields:
        value = payload.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"scheduled lifecycle review {field_name} must be non-negative integer")
            return None
        values.append(value)
    if values[-1] < 1 or values[-1] > 100:
        errors.append("scheduled lifecycle review requested_limit must be between 1 and 100")
    return values[0], values[1], values[2], values[3]


def _validate_timestamp(value: object, errors: list[str]) -> None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        errors.append("scheduled lifecycle review generated_at_utc must be ISO-8601")
        return
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        errors.append("scheduled lifecycle review generated_at_utc must be UTC")


def _validate_blocker_counts(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("scheduled lifecycle review blocker_counts must be a list")
        return
    observed: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            errors.append("scheduled lifecycle review blocker count must be an object")
            continue
        blocker = str(entry.get("blocker", ""))
        count = entry.get("count")
        if blocker not in ALLOWED_BLOCKERS or blocker in observed:
            errors.append("scheduled lifecycle review blocker inventory is invalid")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            errors.append("scheduled lifecycle review blocker count must be positive integer")
        observed.add(blocker)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate scheduled lifecycle review proof")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    errors = validate_scheduled_lifecycle_review_proof(parser.parse_args().evidence)
    if errors:
        print("\n".join(errors))
        return 1
    print("Scheduled data lifecycle review proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
