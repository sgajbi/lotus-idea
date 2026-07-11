from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

from app.domain.data_lifecycle import DataLifecycleState
from app.domain.data_lifecycle_schedule import ScheduledLifecycleControlSnapshot


ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 12, 3, 0, tzinfo=UTC)


class Connection:
    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class Repository:
    snapshots: tuple[ScheduledLifecycleControlSnapshot, ...] = ()

    def __init__(self, _connection: object) -> None:
        return None

    def scan_data_lifecycle_controls(
        self,
        *,
        evaluated_at_utc: datetime,
        limit: int,
    ) -> tuple[ScheduledLifecycleControlSnapshot, ...]:
        assert evaluated_at_utc == NOW
        return self.snapshots[:limit]


def test_scheduled_lifecycle_review_writes_source_safe_aggregate(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    module = load_script()
    Repository.snapshots = (
        snapshot("candidate-ready", state=DataLifecycleState.ERASED),
        snapshot("candidate-held", state=DataLifecycleState.HELD),
    )
    monkeypatch.setattr(module, "PostgresScheduledDataLifecycleRepository", Repository)
    monkeypatch.setenv("GITHUB_REPOSITORY", "sgajbi/lotus-idea")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    output_path = tmp_path / "evidence.json"

    evidence = module.run_scheduled_data_lifecycle_review(
        database_url="postgresql://runtime-only",
        limit=10,
        output_path=output_path,
        now=lambda: NOW,
        connect=lambda *_args, **_kwargs: Connection(),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert evidence.ready_for_authorized_purge_count == 1
    assert evidence.blocked_count == 1
    assert payload["blocker_counts"] == [{"blocker": "legal_hold_active", "count": 1}]
    assert payload["production_authority_verified"] is False
    assert payload["certification_status"] == "not_certified"
    assert "candidate-ready" not in output_path.read_text(encoding="utf-8")
    assert "candidate-held" not in output_path.read_text(encoding="utf-8")


def test_scheduled_lifecycle_review_entrypoint_loads() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_scheduled_data_lifecycle_review.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--limit" in completed.stdout


def snapshot(
    candidate_id: str,
    *,
    state: DataLifecycleState,
) -> ScheduledLifecycleControlSnapshot:
    return ScheduledLifecycleControlSnapshot(
        candidate_id=candidate_id,
        tenant_id="tenant-private-bank-sg",
        policy_ref="lotus-idea:regulated-advisory-evidence:seven-year:v1",
        state=state,
        held_from_state=(DataLifecycleState.ERASED if state is DataLifecycleState.HELD else None),
        retention_expires_at_utc=NOW,
        control_version=3,
        active_outbox_count=0,
        active_downstream_count=0,
    )


def load_script() -> ModuleType:
    path = ROOT / "scripts/run_scheduled_data_lifecycle_review.py"
    spec = importlib.util.spec_from_file_location("run_scheduled_data_lifecycle_review", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
