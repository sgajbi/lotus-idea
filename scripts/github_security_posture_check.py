from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_REPOSITORY = "sgajbi/lotus-idea"
REQUIRED_LANGUAGES = frozenset({"actions", "python"})
REQUIRED_SECURITY_FEATURES = {
    "dependabot_security_updates": "Dependabot security updates",
    "secret_scanning": "Secret scanning",
    "secret_scanning_push_protection": "Secret scanning push protection",
}
ADVANCED_SECRET_SCANNING_FEATURES = {
    "secret_scanning_non_provider_patterns": "Secret scanning non-provider patterns",
    "secret_scanning_validity_checks": "Secret scanning validity checks",
}


@dataclass(frozen=True)
class GitHubSecurityPostureSnapshot:
    repository: str
    security_and_analysis: dict[str, Any]
    codeql_default_setup: dict[str, Any]
    private_vulnerability_reporting: dict[str, Any]
    open_code_scanning_alerts: int
    open_secret_scanning_alerts: int
    open_dependabot_alerts: int


def _run_gh_json(path: str) -> Any:
    completed = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown gh api error"
        raise RuntimeError(f"`gh api {path}` failed: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`gh api {path}` returned non-JSON output") from exc


def _alert_count(repository: str, alert_family: str) -> int:
    response = _run_gh_json(f"repos/{repository}/{alert_family}/alerts?state=open&per_page=100")
    if not isinstance(response, list):
        raise RuntimeError(f"{alert_family} alert endpoint returned an unexpected payload")
    return len(response)


def collect_live_snapshot(repository: str = DEFAULT_REPOSITORY) -> GitHubSecurityPostureSnapshot:
    repository_response = _run_gh_json(f"repos/{repository}")
    if not isinstance(repository_response, dict):
        raise RuntimeError("Repository endpoint returned an unexpected payload")
    security_and_analysis = repository_response.get("security_and_analysis")
    if not isinstance(security_and_analysis, dict):
        raise RuntimeError("Repository payload did not include security_and_analysis")

    codeql_default_setup = _run_gh_json(f"repos/{repository}/code-scanning/default-setup")
    if not isinstance(codeql_default_setup, dict):
        raise RuntimeError("CodeQL default setup endpoint returned an unexpected payload")

    private_vulnerability_reporting = _run_gh_json(
        f"repos/{repository}/private-vulnerability-reporting"
    )
    if not isinstance(private_vulnerability_reporting, dict):
        raise RuntimeError(
            "Private vulnerability reporting endpoint returned an unexpected payload"
        )

    return GitHubSecurityPostureSnapshot(
        repository=repository,
        security_and_analysis=security_and_analysis,
        codeql_default_setup=codeql_default_setup,
        private_vulnerability_reporting=private_vulnerability_reporting,
        open_code_scanning_alerts=_alert_count(repository, "code-scanning"),
        open_secret_scanning_alerts=_alert_count(repository, "secret-scanning"),
        open_dependabot_alerts=_alert_count(repository, "dependabot"),
    )


def load_snapshot(path: Path) -> GitHubSecurityPostureSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return GitHubSecurityPostureSnapshot(
        repository=str(payload["repository"]),
        security_and_analysis=dict(payload["security_and_analysis"]),
        codeql_default_setup=dict(payload["codeql_default_setup"]),
        private_vulnerability_reporting=dict(payload["private_vulnerability_reporting"]),
        open_code_scanning_alerts=int(payload["open_code_scanning_alerts"]),
        open_secret_scanning_alerts=int(payload["open_secret_scanning_alerts"]),
        open_dependabot_alerts=int(payload["open_dependabot_alerts"]),
    )


def _feature_status(security_and_analysis: dict[str, Any], feature: str) -> str:
    feature_payload = security_and_analysis.get(feature)
    if not isinstance(feature_payload, dict):
        return "missing"
    status = feature_payload.get("status")
    return status if isinstance(status, str) else "missing"


def validate_snapshot(
    snapshot: GitHubSecurityPostureSnapshot,
    *,
    max_open_alerts: int = 0,
    require_advanced_secret_scanning: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for feature, label in REQUIRED_SECURITY_FEATURES.items():
        status = _feature_status(snapshot.security_and_analysis, feature)
        if status != "enabled":
            errors.append(f"{label} must be enabled; GitHub reports `{status}`")

    for feature, label in ADVANCED_SECRET_SCANNING_FEATURES.items():
        status = _feature_status(snapshot.security_and_analysis, feature)
        if status != "enabled":
            message = f"{label} is not enabled; GitHub reports `{status}`"
            if require_advanced_secret_scanning:
                errors.append(message)
            else:
                warnings.append(message)

    if snapshot.private_vulnerability_reporting.get("enabled") is not True:
        errors.append("Private vulnerability reporting must be enabled")

    codeql = snapshot.codeql_default_setup
    if codeql.get("state") != "configured":
        errors.append("CodeQL default setup must be configured")
    languages = codeql.get("languages")
    if not isinstance(languages, list) or not REQUIRED_LANGUAGES.issubset(set(languages)):
        errors.append("CodeQL default setup must cover Python and GitHub Actions")
    if codeql.get("schedule") != "weekly":
        errors.append("CodeQL default setup must run weekly")
    if codeql.get("query_suite") != "default":
        errors.append("CodeQL default setup must use the governed default query suite")
    if codeql.get("threat_model") != "remote":
        errors.append("CodeQL default setup must use the governed remote threat model")

    alert_counts = {
        "code scanning": snapshot.open_code_scanning_alerts,
        "secret scanning": snapshot.open_secret_scanning_alerts,
        "Dependabot": snapshot.open_dependabot_alerts,
    }
    for label, count in alert_counts.items():
        if count > max_open_alerts:
            errors.append(
                f"Open {label} alerts must be <= {max_open_alerts}; GitHub reports {count}"
            )

    return errors, warnings


def _format_summary(snapshot: GitHubSecurityPostureSnapshot, warnings: list[str]) -> str:
    lines = [
        f"GitHub security posture check passed for {snapshot.repository}",
        f"Open code scanning alerts: {snapshot.open_code_scanning_alerts}",
        f"Open secret scanning alerts: {snapshot.open_secret_scanning_alerts}",
        f"Open Dependabot alerts: {snapshot.open_dependabot_alerts}",
        "CodeQL default setup: "
        f"{snapshot.codeql_default_setup.get('state')} / "
        f"{snapshot.codeql_default_setup.get('query_suite')} / "
        f"{snapshot.codeql_default_setup.get('threat_model')}",
    ]
    if warnings:
        lines.append("Advisory controls not claimed as active release evidence:")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY)
    parser.add_argument("--snapshot", type=Path, help="Validate a captured posture JSON payload")
    parser.add_argument("--max-open-alerts", type=int, default=0)
    parser.add_argument("--require-advanced-secret-scanning", action="store_true")
    args = parser.parse_args(argv)

    try:
        snapshot = (
            load_snapshot(args.snapshot) if args.snapshot else collect_live_snapshot(args.repo)
        )
        errors, warnings = validate_snapshot(
            snapshot,
            max_open_alerts=args.max_open_alerts,
            require_advanced_secret_scanning=args.require_advanced_secret_scanning,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(_format_summary(snapshot, warnings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
