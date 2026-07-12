from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def test_scheduled_lifecycle_review_proof_accepts_source_safe_main_evidence(
    tmp_path: Path,
) -> None:
    module = load_gate()
    path = write_evidence(tmp_path, valid_evidence())

    assert module.validate_scheduled_lifecycle_review_proof(path) == []


def test_scheduled_lifecycle_review_proof_rejects_overclaim_and_sensitive_fields(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = valid_evidence()
    payload.update(
        {
            "production_authority_verified": True,
            "certification_status": "certified",
            "supported_feature_promoted": True,
            "candidate_id": "candidate-sensitive",
        }
    )
    path = write_evidence(tmp_path, payload)

    errors = module.validate_scheduled_lifecycle_review_proof(path)

    assert "scheduled lifecycle review production_authority_verified must be False" in errors
    assert "scheduled lifecycle review certification_status must be 'not_certified'" in errors
    assert "scheduled lifecycle review supported_feature_promoted must be False" in errors
    assert "scheduled lifecycle evidence must not expose candidate_id" in errors


def test_scheduled_lifecycle_review_proof_rejects_count_and_blocker_tampering(
    tmp_path: Path,
) -> None:
    module = load_gate()
    payload = deepcopy(valid_evidence())
    payload["blocked_count"] = 0
    payload["blocker_counts"] = [
        {"blocker": "unknown", "count": 0},
        {"blocker": "unknown", "count": 1},
    ]
    path = write_evidence(tmp_path, payload)

    errors = module.validate_scheduled_lifecycle_review_proof(path)

    assert "scheduled lifecycle review counts must reconcile" in errors
    assert "scheduled lifecycle proof must exercise ready and blocked decisions" in errors
    assert "scheduled lifecycle review blocker inventory is invalid" in errors
    assert "scheduled lifecycle review blocker count must be positive integer" in errors


def valid_evidence() -> dict[str, Any]:
    return {
        "schema_version": "lotus-idea.scheduled-lifecycle-review-evidence.v1",
        "generated_at_utc": datetime(2026, 7, 12, 3, 0, tzinfo=UTC).isoformat(),
        "repository": "sgajbi/lotus-idea",
        "git_commit": "a" * 40,
        "git_ref": "refs/heads/main",
        "ci_run_id": "12345",
        "execution_profile": "synthetic_disposable_postgres",
        "requested_limit": 100,
        "scanned_count": 2,
        "ready_for_authorized_purge_count": 1,
        "blocked_count": 1,
        "blocker_counts": [{"blocker": "legal_hold_active", "count": 1}],
        "truncated": False,
        "review_only": True,
        "privacy_review_required": True,
        "production_authority_verified": False,
        "source_safe": True,
        "certification_status": "not_certified",
        "supported_feature_promoted": False,
    }


def write_evidence(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def load_gate() -> ModuleType:
    path = ROOT / "scripts/scheduled_data_lifecycle_review_proof_gate.py"
    spec = importlib.util.spec_from_file_location(
        "scheduled_data_lifecycle_review_proof_gate", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
