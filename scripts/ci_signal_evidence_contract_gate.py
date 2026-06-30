from __future__ import annotations

from ci_signal_evidence import build_ci_signal_evidence, validate_ci_signal_evidence


EXAMPLE_JOBS = {
    "jobs": [
        {
            "name": "PR Merge Gate / Lint Typecheck Security",
            "status": "completed",
            "conclusion": "success",
            "started_at": "2026-06-30T10:00:00Z",
            "completed_at": "2026-06-30T10:04:00Z",
            "runner_name": "GitHub Actions 1",
            "labels": ["ubuntu-latest"],
            "steps": [
                {
                    "name": "Install",
                    "number": 3,
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-06-30T10:00:20Z",
                    "completed_at": "2026-06-30T10:01:35Z",
                }
            ],
        },
        {
            "name": "PR Merge Gate / Validate Docker Build",
            "status": "completed",
            "conclusion": "failure",
            "started_at": "2026-06-30T10:04:00Z",
            "completed_at": "2026-06-30T10:05:10Z",
            "runner_name": "GitHub Actions 2",
            "labels": ["ubuntu-latest"],
            "steps": [
                {
                    "name": "Scan Docker image",
                    "number": 4,
                    "status": "completed",
                    "conclusion": "failure",
                    "started_at": "2026-06-30T10:04:40Z",
                    "completed_at": "2026-06-30T10:05:10Z",
                }
            ],
        },
    ]
}


def main() -> int:
    artifact = build_ci_signal_evidence(
        jobs_payload=EXAMPLE_JOBS,
        repository="sgajbi/lotus-idea",
        commit_sha="a" * 40,
        ref="refs/heads/main",
        workflow="Pull Request Merge Gate",
        run_id="123456",
        run_attempt="1",
        generated_at_utc="2026-06-30T10:05:30Z",
        source="contract-gate-example",
    )
    errors = validate_ci_signal_evidence(artifact)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("CI signal evidence contract gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
