from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_security_tab_contract() -> ModuleType:
    script_path = ROOT / "scripts" / "security_tab_governance_contract.py"
    spec = importlib.util.spec_from_file_location("security_tab_governance_contract", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_security_tab_governance_contract_passes_current_repository() -> None:
    module = _load_security_tab_contract()

    assert module.validate_security_tab_governance_files(ROOT) == []


def test_security_tab_governance_contract_blocks_missing_reporting_policy() -> None:
    module = _load_security_tab_contract()
    security_policy = (
        (ROOT / "SECURITY.md")
        .read_text(encoding="utf-8")
        .replace("Do not open public GitHub issues", "Use GitHub issues")
    )
    dependabot_config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert "SECURITY.md must keep vulnerability reports out of public issues" in errors


def test_security_tab_governance_contract_blocks_client_data_reporting_boundary() -> None:
    module = _load_security_tab_contract()
    security_policy = (
        (ROOT / "SECURITY.md")
        .read_text(encoding="utf-8")
        .replace("Do not include client-identifying data", "Limit sensitive examples")
    )
    dependabot_config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert "SECURITY.md must prohibit client-identifying data in reports" in errors


def test_security_tab_governance_contract_blocks_missing_github_actions_coverage() -> None:
    module = _load_security_tab_contract()
    security_policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    dependabot_config = (
        (ROOT / ".github" / "dependabot.yml")
        .read_text(encoding="utf-8")
        .replace('package-ecosystem: "github-actions"', 'package-ecosystem: "docker"')
    )

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert "dependabot.yml must monitor GitHub Actions" in errors


def test_security_tab_governance_contract_blocks_missing_python_closure_group() -> None:
    module = _load_security_tab_contract()
    security_policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    dependabot_config = (
        (ROOT / ".github" / "dependabot.yml")
        .read_text(encoding="utf-8")
        .replace("python-dependency-closure-roots", "python-runtime-locks")
    )

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert "dependabot.yml must group Python root dependency updates for closure refresh" in errors


def test_security_tab_governance_contract_blocks_split_requirements_stream() -> None:
    module = _load_security_tab_contract()
    security_policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    dependabot_config = (ROOT / ".github" / "dependabot.yml").read_text(
        encoding="utf-8"
    ) + '\n  - package-ecosystem: "pip"\n    directory: "/requirements"\n'

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert (
        "dependabot.yml must not open lock-only Python PRs for /requirements; "
        "use `make dependency-refresh` to update runtime locks with root pins"
    ) in errors


def test_security_tab_governance_contract_blocks_unbounded_dependency_pr_noise() -> None:
    module = _load_security_tab_contract()
    security_policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    dependabot_config = (
        (ROOT / ".github" / "dependabot.yml")
        .read_text(encoding="utf-8")
        .replace("open-pull-requests-limit: 5", "open-pull-requests-limit: 20")
    )

    errors = module.validate_security_tab_governance(security_policy, dependabot_config)

    assert "dependabot.yml must cap open dependency PRs to preserve signal quality" in errors
