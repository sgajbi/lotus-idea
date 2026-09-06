# ruff: noqa: E402
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports  # noqa: E402

ensure_worktree_imports(__file__)

from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_OWNER_RESTART_TEST_NODES,
    IDEA_ADVISE_RECONCILIATION_TEST_NODES,
)
from app.domain.proof_evidence import EvidenceClass


def execute_advise_postgres_restart_tests(
    *,
    advise_root: Path,
    advise_python: str,
    postgres_dsn: str,
    allow_database_reset: bool,
) -> dict[str, Any]:
    if not postgres_dsn:
        raise ValueError("--advise-postgres-dsn is required for owner restart certification")
    _require_database_reset_authority(allow_database_reset, "owner restart")
    test_source = (
        advise_root / "tests/integration/advisory/engine/"
        "test_engine_proposal_repository_postgres_integration.py"
    )
    env = os.environ.copy()
    env["PROPOSAL_POSTGRES_INTEGRATION_DSN"] = postgres_dsn
    completed = subprocess.run(
        [advise_python, "-m", "pytest", *ADVISE_OWNER_RESTART_TEST_NODES, "-q"],
        cwd=advise_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    _require_exact_pass_count(completed.stdout, expected=2, owner="Advise")
    return {
        "evidenceClass": EvidenceClass.TEST_EXECUTION.value,
        "databaseBackend": "postgresql",
        "testNodes": ADVISE_OWNER_RESTART_TEST_NODES,
        "testProcessExitCode": completed.returncode,
        "testPassedCount": 2,
        "testSourceDigest": _source_digest(test_source),
        "ownerRepositoryInstanceCount": 2,
        "intakeAcceptedCount": 1,
        "intakeReplayCount": 1,
        "restartReadbackStatus": "ADVISORY_REJECTED",
        "restartReadbackVersion": 3,
        "restartOutcomeVersions": (1, 2, 3),
        "restartReplayCreatedNewState": False,
        "ownerHistoryUnchangedAcrossRestart": True,
        "ownerIdentitiesUnchangedAcrossRestart": True,
        "duplicateOwnerWorkCount": 0,
        "rawDatabaseDsnRetained": False,
    }


def execute_idea_postgres_reconciliation_test(
    *,
    repository_root: Path,
    idea_python: str,
    postgres_dsn: str,
    allow_database_reset: bool,
) -> dict[str, Any]:
    if not postgres_dsn:
        raise ValueError("--idea-postgres-dsn is required for Idea reconciliation certification")
    _require_database_reset_authority(allow_database_reset, "Idea reconciliation")
    test_source = (
        repository_root / "tests/integration/test_postgres_downstream_submission_runtime.py"
    )
    env = os.environ.copy()
    env["LOTUS_IDEA_POSTGRES_INTEGRATION_URL"] = postgres_dsn
    env["LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED"] = "1"
    completed = subprocess.run(
        [idea_python, "-m", "pytest", *IDEA_ADVISE_RECONCILIATION_TEST_NODES, "-q"],
        cwd=repository_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    _require_exact_pass_count(completed.stdout, expected=1, owner="Idea")
    return {
        "evidenceClass": EvidenceClass.TEST_EXECUTION.value,
        "databaseBackend": "postgresql",
        "testNodes": IDEA_ADVISE_RECONCILIATION_TEST_NODES,
        "testProcessExitCode": completed.returncode,
        "testPassedCount": 1,
        "testSourceDigest": _source_digest(test_source),
        "ideaRepositoryInstanceCount": 2,
        "firstReconciliationStatus": "accepted",
        "firstReconciliationAppendedOutcomeCount": 3,
        "exactReplayStatus": "replayed",
        "exactReplayAppendedOutcomeCount": 0,
        "submissionAttemptCount": 1,
        "retainedOutcomeVersions": (1, 2, 3),
        "ownerIdentityUnchanged": True,
        "governedTableCountsUnchangedOnReplay": True,
        "rawDatabaseDsnRetained": False,
    }


def _require_database_reset_authority(allowed: bool, proof_name: str) -> None:
    if not allowed:
        raise ValueError(
            f"--allow-destructive-test-database-reset is required for {proof_name} certification"
        )


def _require_exact_pass_count(stdout: str, *, expected: int, owner: str) -> None:
    if re.search(rf"(?m)(?:^|\s){expected} passed(?:\s|$)", stdout) is None or (
        "skipped" in stdout.lower()
    ):
        count_label = {1: "one", 2: "two"}.get(expected, str(expected))
        label = "test" if expected == 1 else "tests"
        raise ValueError(
            f"{owner} PostgreSQL restart certification requires exactly "
            f"{count_label} passed {label}"
        )


def _source_digest(path: Path) -> str:
    return f"sha256:{sha256(path.read_bytes()).hexdigest()}"
