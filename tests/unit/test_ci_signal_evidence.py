from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_ci_signal_evidence() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_signal_evidence.py"
    spec = importlib.util.spec_from_file_location("ci_signal_evidence", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_signal_evidence_summarizes_job_and_step_durations() -> None:
    module = _load_ci_signal_evidence()
    artifact = module.build_ci_signal_evidence(
        jobs_payload={
            "jobs": [
                {
                    "name": "Main Releasability / Coverage Gate (Combined)",
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-06-30T10:00:00Z",
                    "completed_at": "2026-06-30T10:02:00Z",
                    "runner_name": "runner-1",
                    "labels": ["ubuntu-latest"],
                    "steps": [
                        {
                            "name": "Install",
                            "number": 2,
                            "status": "completed",
                            "conclusion": "success",
                            "started_at": "2026-06-30T10:00:10Z",
                            "completed_at": "2026-06-30T10:00:55Z",
                        }
                    ],
                },
                {
                    "name": "Main Releasability / Validate Docker Build",
                    "status": "completed",
                    "conclusion": "failure",
                    "started_at": "2026-06-30T10:02:00Z",
                    "completed_at": "2026-06-30T10:03:10Z",
                    "steps": [],
                },
            ]
        },
        repository="sgajbi/lotus-idea",
        commit_sha="b" * 40,
        ref="refs/heads/main",
        workflow="Main Releasability Gate",
        run_id="987",
        run_attempt="1",
        generated_at_utc="2026-06-30T10:03:30Z",
    )

    assert artifact["thresholdEnforced"] is False
    assert artifact["summary"]["criticalPathJobName"] == (
        "Main Releasability / Coverage Gate (Combined)"
    )
    assert artifact["summary"]["criticalPathSeconds"] == 120
    assert artifact["summary"]["failureCategories"] == ["docker_build_or_scan"]
    assert artifact["jobs"][0]["steps"][0]["durationSeconds"] == 45


def test_ci_signal_evidence_rejects_source_sensitive_markers() -> None:
    module = _load_ci_signal_evidence()
    errors = module.validate_ci_signal_evidence(
        {
            "schemaVersion": module.SCHEMA_VERSION,
            "repository": "sgajbi/lotus-idea",
            "commitSha": "c" * 40,
            "ref": "refs/heads/main",
            "workflow": "Main Releasability Gate",
            "runId": "1",
            "runAttempt": "1",
            "generatedAtUtc": "2026-06-30T10:03:30Z",
            "source": "test",
            "thresholdEnforced": False,
            "jobs": [],
            "summary": {"cacheEvidence": "token cache should not be present"},
        }
    )

    assert any("forbidden source markers" in error for error in errors)


def test_ci_signal_evidence_cli_writes_artifact(tmp_path: Path) -> None:
    module = _load_ci_signal_evidence()
    jobs_json = tmp_path / "jobs.json"
    output = tmp_path / "ci-signal-evidence.json"
    jobs_json.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "name": "Feature Lane / Tests (unit)",
                        "status": "completed",
                        "conclusion": "success",
                        "started_at": "2026-06-30T10:00:00Z",
                        "completed_at": "2026-06-30T10:01:00Z",
                        "steps": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = module.main(
        [
            "--jobs-json",
            str(jobs_json),
            "--output",
            str(output),
            "--repository",
            "sgajbi/lotus-idea",
            "--commit-sha",
            "d" * 40,
            "--ref",
            "refs/heads/feature",
            "--workflow",
            "Remote Feature Lane",
            "--run-id",
            "654",
            "--run-attempt",
            "1",
            "--generated-at-utc",
            "2026-06-30T10:01:10Z",
        ]
    )

    assert result == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["schemaVersion"] == module.SCHEMA_VERSION
    assert artifact["summary"]["jobCount"] == 1
