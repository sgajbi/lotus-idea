from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECURITY_POLICY_PATH = "SECURITY.md"
DEPENDABOT_PATH = ".github/dependabot.yml"

SECURITY_POLICY_REQUIRED_FRAGMENTS = {
    "# Security Policy": "SECURITY.md must define a GitHub security policy",
    "Supported Versions": "SECURITY.md must define supported versions",
    "Reporting a Vulnerability": "SECURITY.md must define vulnerability reporting",
    "Do not open public GitHub issues": (
        "SECURITY.md must keep vulnerability reports out of public issues"
    ),
    "Do not include client-identifying data": (
        "SECURITY.md must prohibit client-identifying data in reports"
    ),
}
DEPENDABOT_REQUIRED_FRAGMENTS = {
    'package-ecosystem: "pip"': "dependabot.yml must monitor Python dependencies",
    'package-ecosystem: "github-actions"': "dependabot.yml must monitor GitHub Actions",
    'interval: "weekly"': "dependabot.yml must use a weekly cadence",
    'timezone: "Asia/Singapore"': "dependabot.yml must use the governed timezone",
    "groups:": "dependabot.yml must group updates to reduce alert noise",
    "open-pull-requests-limit: 5": (
        "dependabot.yml must cap open dependency PRs to preserve signal quality"
    ),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_security_tab_governance(security_policy: str, dependabot_config: str) -> list[str]:
    errors: list[str] = []
    for fragment, message in SECURITY_POLICY_REQUIRED_FRAGMENTS.items():
        if fragment not in security_policy:
            errors.append(message)
    for fragment, message in DEPENDABOT_REQUIRED_FRAGMENTS.items():
        if fragment not in dependabot_config:
            errors.append(message)
    return errors


def validate_security_tab_governance_files(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    security_policy_path = root / SECURITY_POLICY_PATH
    dependabot_path = root / DEPENDABOT_PATH
    if not security_policy_path.exists():
        errors.append("Missing SECURITY.md")
        security_policy = ""
    else:
        security_policy = _read(security_policy_path)
    if not dependabot_path.exists():
        errors.append("Missing .github/dependabot.yml")
        dependabot_config = ""
    else:
        dependabot_config = _read(dependabot_path)
    return [*errors, *validate_security_tab_governance(security_policy, dependabot_config)]


def main() -> int:
    errors = validate_security_tab_governance_files()
    if errors:
        print("\n".join(errors))
        return 1
    print("Security tab governance contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
