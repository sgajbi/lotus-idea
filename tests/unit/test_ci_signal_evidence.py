from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


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
    assert artifact["summary"]["criticalPathBasis"] == "workflow_wall_clock"
    assert artifact["summary"]["workflowStartedAtUtc"] == "2026-06-30T10:00:00Z"
    assert artifact["summary"]["workflowCompletedAtUtc"] == "2026-06-30T10:03:10Z"
    assert artifact["summary"]["workflowWallClockSeconds"] == 190
    assert artifact["summary"]["criticalPathJobName"] is None
    assert artifact["summary"]["criticalPathSeconds"] == 190
    assert artifact["summary"]["longestJobName"] == (
        "Main Releasability / Coverage Gate (Combined)"
    )
    assert artifact["summary"]["longestJobSeconds"] == 120
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


def test_jobs_payload_from_needs_preserves_results_and_discards_outputs() -> None:
    module = _load_ci_signal_evidence()

    payload = module.jobs_payload_from_needs(
        {
            "workflow-lint": {
                "result": "success",
                "outputs": {"token-shaped-output": "must-not-survive"},
            },
            "unit-tests": {"result": "failure", "outputs": {}},
            "optional-proof": {"result": "skipped", "outputs": {}},
        }
    )

    assert [job["name"] for job in payload["jobs"]] == [
        "optional-proof",
        "unit-tests",
        "workflow-lint",
    ]
    assert [job["conclusion"] for job in payload["jobs"]] == [
        "skipped",
        "failure",
        "success",
    ]
    assert all(job["steps"] == [] for job in payload["jobs"])
    assert "outputs" not in json.dumps(payload)


def test_jobs_payload_from_needs_rejects_unknown_result() -> None:
    module = _load_ci_signal_evidence()

    with pytest.raises(ValueError, match="unsupported result"):
        module.jobs_payload_from_needs({"unit-tests": {"result": "unknown"}})


def test_ci_signal_evidence_cli_consumes_needs_context_without_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_ci_signal_evidence()
    output = tmp_path / "ci-signal-evidence.json"
    monkeypatch.setenv(
        "CI_NEEDS_JSON",
        json.dumps(
            {
                "workflow-lint": {
                    "result": "failure",
                    "outputs": {"password": "must-not-survive"},
                }
            }
        ),
    )

    result = module.main(
        [
            "--needs-env",
            "CI_NEEDS_JSON",
            "--output",
            str(output),
            "--repository",
            "sgajbi/lotus-idea",
            "--commit-sha",
            "e" * 40,
            "--ref",
            "refs/heads/feature",
            "--workflow",
            "Remote Feature Lane",
            "--run-id",
            "655",
            "--run-attempt",
            "1",
            "--generated-at-utc",
            "2026-07-16T23:00:00Z",
        ]
    )

    assert result == 0
    artifact_text = output.read_text(encoding="utf-8")
    artifact = json.loads(artifact_text)
    assert artifact["source"] == "github-actions-needs-context"
    assert artifact["summary"]["failedJobCount"] == 1
    assert artifact["summary"]["failureCategories"] == ["workflow_lint"]
    assert "password" not in artifact_text


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
    assert artifact["summary"]["criticalPathSeconds"] == 60
    assert artifact["summary"]["longestJobSeconds"] == 60
