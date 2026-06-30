from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "lotus-idea.ci-signal-evidence.v1"
FORBIDDEN_SOURCE_MARKERS = (
    "secret",
    "token",
    "password",
    "client_identifying",
    "portfolio_id",
    "account_number",
)


def build_ci_signal_evidence(
    *,
    jobs_payload: dict[str, Any],
    repository: str,
    commit_sha: str,
    ref: str,
    workflow: str,
    run_id: str,
    run_attempt: str,
    generated_at_utc: str,
    source: str = "github-actions-jobs-api",
) -> dict[str, Any]:
    jobs = [_build_job(job) for job in jobs_payload.get("jobs", [])]
    completed_jobs = [job for job in jobs if job["completedAtUtc"]]
    critical_path = max(completed_jobs, key=lambda job: job["durationSeconds"], default=None)
    failed_jobs = [job for job in jobs if job["conclusion"] in {"failure", "timed_out"}]
    cancelled_jobs = [job for job in jobs if job["conclusion"] == "cancelled"]
    failure_categories = sorted(
        {job["failureCategory"] for job in failed_jobs + cancelled_jobs if job["failureCategory"]}
    )

    artifact = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": repository,
        "commitSha": commit_sha,
        "ref": ref,
        "workflow": workflow,
        "runId": run_id,
        "runAttempt": run_attempt,
        "generatedAtUtc": generated_at_utc,
        "source": source,
        "thresholdEnforced": False,
        "jobs": jobs,
        "summary": {
            "jobCount": len(jobs),
            "completedJobCount": len(completed_jobs),
            "failedJobCount": len(failed_jobs),
            "cancelledJobCount": len(cancelled_jobs),
            "criticalPathJobName": critical_path["name"] if critical_path else None,
            "criticalPathSeconds": critical_path["durationSeconds"] if critical_path else 0,
            "failureCategories": failure_categories,
            "cacheEvidence": "not_captured_by_github_jobs_api",
        },
    }
    errors = validate_ci_signal_evidence(artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return artifact


def validate_ci_signal_evidence(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schemaVersion",
        "repository",
        "commitSha",
        "ref",
        "workflow",
        "runId",
        "runAttempt",
        "generatedAtUtc",
        "source",
        "thresholdEnforced",
        "jobs",
        "summary",
    }
    missing = sorted(required_fields - artifact.keys())
    if missing:
        errors.append(f"artifact missing fields: {', '.join(missing)}")
    if artifact.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")
    if artifact.get("thresholdEnforced") is not False:
        errors.append("CI signal evidence must remain report-only; thresholdEnforced must be false")
    if not isinstance(artifact.get("jobs"), list):
        errors.append("jobs must be a list")
    if not isinstance(artifact.get("summary"), dict):
        errors.append("summary must be an object")
    forbidden_paths = _find_forbidden_source_markers(artifact)
    if forbidden_paths:
        errors.append(f"artifact contains forbidden source markers: {', '.join(forbidden_paths)}")
    return errors


def _build_job(job: dict[str, Any]) -> dict[str, Any]:
    started_at = _optional_text(job.get("started_at"))
    completed_at = _optional_text(job.get("completed_at"))
    duration = _duration_seconds(started_at, completed_at)
    conclusion = _optional_text(job.get("conclusion")) or "unknown"
    name = _optional_text(job.get("name")) or "unknown"
    return {
        "name": name,
        "status": _optional_text(job.get("status")) or "unknown",
        "conclusion": conclusion,
        "failureCategory": _failure_category(name, conclusion),
        "startedAtUtc": started_at,
        "completedAtUtc": completed_at,
        "durationSeconds": duration,
        "runnerName": _optional_text(job.get("runner_name")),
        "labels": sorted(str(label) for label in job.get("labels", []) if label is not None),
        "steps": [_build_step(step) for step in job.get("steps", [])],
    }


def _build_step(step: dict[str, Any]) -> dict[str, Any]:
    started_at = _optional_text(step.get("started_at"))
    completed_at = _optional_text(step.get("completed_at"))
    return {
        "name": _optional_text(step.get("name")) or "unknown",
        "number": step.get("number"),
        "status": _optional_text(step.get("status")) or "unknown",
        "conclusion": _optional_text(step.get("conclusion")) or "unknown",
        "startedAtUtc": started_at,
        "completedAtUtc": completed_at,
        "durationSeconds": _duration_seconds(started_at, completed_at),
    }


def _failure_category(name: str, conclusion: str) -> str | None:
    if conclusion in {"success", "skipped", "unknown", ""}:
        return None
    lowered = name.lower()
    if conclusion == "cancelled":
        return "cancelled"
    if conclusion == "timed_out":
        return "timeout"
    if "workflow lint" in lowered:
        return "workflow_lint"
    if "lint typecheck security" in lowered:
        return "lint_typecheck_security"
    if "coverage" in lowered:
        return "coverage"
    if "postgres" in lowered:
        return "postgres_runtime"
    if "docker" in lowered or "container" in lowered:
        return "docker_build_or_scan"
    if "test" in lowered:
        return "test"
    return "unclassified_failure"


def _duration_seconds(started_at: str | None, completed_at: str | None) -> int:
    if not started_at or not completed_at:
        return 0
    started = _parse_utc(started_at)
    completed = _parse_utc(completed_at)
    return max(0, round((completed - started).total_seconds()))


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _find_forbidden_source_markers(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if any(marker in key_text for marker in FORBIDDEN_SOURCE_MARKERS):
                findings.append(child_path)
            findings.extend(_find_forbidden_source_markers(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden_source_markers(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in FORBIDDEN_SOURCE_MARKERS):
            findings.append(path)
    return findings


def _default_generated_at() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate source-safe CI timing/signal evidence.")
    parser.add_argument("--jobs-json", required=True, help="GitHub Actions run jobs API payload.")
    parser.add_argument("--output", required=True, help="Path to write ci-signal-evidence.json.")
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", "unknown"))
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "unknown"))
    parser.add_argument("--ref", default=os.getenv("GITHUB_REF", "unknown"))
    parser.add_argument("--workflow", default=os.getenv("GITHUB_WORKFLOW", "unknown"))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", "unknown"))
    parser.add_argument("--run-attempt", default=os.getenv("GITHUB_RUN_ATTEMPT", "unknown"))
    parser.add_argument(
        "--generated-at-utc",
        default=os.getenv("CI_SIGNAL_EVIDENCE_GENERATED_AT_UTC", _default_generated_at()),
    )
    args = parser.parse_args(argv)

    jobs_payload = json.loads(Path(args.jobs_json).read_text(encoding="utf-8"))
    artifact = build_ci_signal_evidence(
        jobs_payload=jobs_payload,
        repository=args.repository,
        commit_sha=args.commit_sha,
        ref=args.ref,
        workflow=args.workflow,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        generated_at_utc=args.generated_at_utc,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote CI signal evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
